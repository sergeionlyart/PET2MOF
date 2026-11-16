"""Weighted C fits and conditional profiles; no pseudo-independent digitized points.

S100: marker errors independent; axis/experimental offsets and scales are shared
within each isotherm. Missing experimental errors use protocol's 3% scale debug
scenario. Correlated systematic uncertainty is never divided by sqrt(n).
"""
import hashlib
import json
import re
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.linalg import cholesky, solve_triangular
from scipy.optimize import least_squares
from pet2mof.model.isotherms import Isotherm, Site, affinity
from .metrics import aicc, metrics

S100 = 'data/extraction/digitization/T006-S100-FigS5.csv'
ALLOWED_DOIS = {'10.1021/acs.inorgchem.5b00435', '10.1039/C2cp23839j'}


def loading(label, interpretation):
    r = 0. if label == 'UiO-66' else float(re.fullmatch(r'(\d+)PEI@UiO-66', label)[1])/100
    if interpretation not in ('composite', 'ratio'):
        raise ValueError('loading interpretation must be composite or ratio')
    return r if interpretation == 'composite' else r/(1+r)


def load_s100(root, interpretation):
    f = pd.read_csv(Path(root)/S100)
    if set(f.source_id) != {'S100'} or set(f.extraction_id) != {'T006-S100-FigS5'} or set(f.data_kind) != {'digitized_markers'}:
        raise ValueError('unexpected S100 provenance')
    f['p'] = f.x_display_kPa/100  # D-15: absolute kPa, NOT P/P0
    f['q'] = f.uptake_mmol_g
    f['w'] = [loading(v, interpretation) for v in f.series]
    return f


def covariance(f, derivative, settings):
    n = len(f)
    q_bound = np.maximum(f.uptake_bound_mmol_g.to_numpy(), settings['interexecutor_q'])
    p_bound = np.maximum(f.x_bound_kPa.to_numpy()/100, settings['interexecutor_p'])
    C = np.diag((q_bound**2 + (derivative*p_bound)**2)/3)
    # Shared extraction axis offset and experimental scale/offset by whole isotherm.
    for label in f.series.unique():
        mask = (f.series == label).to_numpy().astype(float)
        q_offset = mask * settings['digit_fraction'] * settings['q_scale'] / np.sqrt(3)
        p_offset = mask * derivative * settings['digit_fraction'] * settings['p_scale'] / np.sqrt(3)
        exp_offset = mask * settings['exp_fraction'] * settings['q_scale'] / np.sqrt(3)
        exp_scale = mask * f.q.to_numpy() * settings['exp_fraction'] / np.sqrt(3)
        for vector in (q_offset, p_offset, exp_offset, exp_scale):
            C += np.outer(vector, vector)
    return C


def _solve(fun, starts, bounds):
    fits = [least_squares(fun, start, bounds=bounds, max_nfev=1500, xtol=1e-10, ftol=1e-10, gtol=1e-10) for start in starts]
    good = [f for f in fits if f.success and np.all(np.isfinite(f.fun))]
    if not good:
        raise RuntimeError('C optimizer failed')
    return min(good, key=lambda f: np.dot(f.fun, f.fun))


def fit_s100(root, settings, interpretation='composite', *, profiles=True):
    f = load_s100(root, interpretation)
    host = f[f.w == 0].reset_index(drop=True)
    hder = np.full(len(host), 2.)
    for _ in range(3):
        C = covariance(host, hder, settings['errors'])
        L = cholesky(C, lower=True)
        def host_pred(x, p):
            return x[0]*x[1]*p/(1+x[1]*p)
        result = _solve(lambda x: solve_triangular(L, host_pred(x,host.p.to_numpy())-host.q, lower=True),
                        settings['host_starts'], tuple(np.array(settings['host_bounds']).T))
        hder = result.x[0]*result.x[1]/(1+result.x[1]*host.p.to_numpy())**2
    host_iso = Isotherm((Site(*result.x),), settings['T_fit'])
    host_metrics = metrics(host.q,host_pred(result.x,host.p.to_numpy()),np.sqrt(np.diag(C)),scale=settings['errors']['q_scale'])
    pei = f[f.w > 0].reset_index(drop=True)
    p,w,q = pei.p.to_numpy(),pei.w.to_numpy(),pei.q.to_numpy()
    hostq = host_pred(result.x,p)
    nN = settings['n_N']
    # Identical frozen weights for M1/B1, based on C marker slopes, not the
    # candidate model. Slope estimation affects uncertainty, never observations.
    deriv = np.zeros(len(p))
    for label in pei.series.unique():
        indices = np.flatnonzero((pei.series == label).to_numpy())
        deriv[indices] = np.gradient(q[indices], p[indices])
    cov = covariance(pei, deriv, settings['errors'])
    L = cholesky(cov, lower=True)
    outputs = {}
    for name in ('M1','B1'):
        def predict(x, pressure=p):
            hq=host_pred(result.x,pressure)
            if name == 'M1':
                A0, lam, kd, kappa = x
                return (1-w-kappa*w)*hq + w*nN*.5*A0*np.exp(-lam*w/(1-w))*kd*pressure/(1+kd*pressure)
            eta,kd=x
            return (1-w)*hq + w*nN*eta*kd*pressure/(1+kd*pressure)
        bounds=np.array(settings[name+'_bounds']).T
        # Every possible composition must have nonnegative dry pore volume.
        if name=='M1':
            bounds[1,3]=min(bounds[1,3],float(np.min((1-w)/w)))
        fun=lambda x: solve_triangular(L,predict(x)-q,lower=True)
        fitted=_solve(fun,settings[name+'_starts'],tuple(bounds))
        pred=predict(fitted.x)
        chi2=float(np.dot(fun(fitted.x),fun(fitted.x)))
        columns=['A0','lam','K_d','kappa'] if name=='M1' else ['eta0','K_d']
        profile={}
        if profiles:
            for j,col in enumerate(columns):
                grid=np.linspace(bounds[0,j],bounds[1,j],settings['profile_points'])
                if col=='K_d':
                    grid=np.geomspace(max(bounds[0,j],.001),bounds[1,j],settings['profile_points'])
                free=[i for i in range(len(columns)) if i!=j]
                rows=[]
                for v in grid:
                    def packed(y):
                        x=fitted.x.copy();x[j]=v;x[free]=y
                        return x
                    pr=least_squares(lambda y: fun(packed(y)), fitted.x[free],bounds=(bounds[0,free],bounds[1,free]),max_nfev=1000)
                    rows.append(dict(fixed=float(v),chi2=float(np.dot(pr.fun,pr.fun)),parameters=dict(zip(columns,packed(pr.x).tolist())),success=bool(pr.success)))
                profile[col]=rows
        outputs[name]=dict(parameters=dict(zip(columns,fitted.x.tolist())), metrics=metrics(q,pred,np.sqrt(np.diag(cov)),scale=settings['errors']['q_scale']),
                           chi2=chi2,AICc=aicc(chi2,len(columns),len(pei.series.unique())),
                           AICc_reason='independent isotherms, not adjacent digitized points; four PEI series',
                           profiles=profile,optimizer_success=bool(fitted.success), jacobian_singular_values=np.linalg.svd(fitted.jac,compute_uv=False).tolist(),
                           covariance=cov.tolist(),
                           predictions=[dict(series=str(s),p_bar=float(pp),w=float(ww),q_observed=float(qq),q_predicted=float(pr),error=float(pr-qq),extraction_id='T006-S100-FigS5') for s,pp,ww,qq,pr in zip(pei.series,p,w,q,pred)])
        if name == 'M1':
            # Exact likelihood ridge, conditional on the same nu_d: only n_N*A0
            # enters dry data. This is not a confidence interval on elemental N.
            product=nN*fitted.x[0]
            outputs[name]['nitrogen_ridge']=[dict(n_N=float(v),A0=float(product/v),chi2=chi2)
                for v in np.linspace(max(product,1e-6),settings['n_N_ridge_upper'],settings['profile_points'])]
    return dict(status='debug',interpretation=interpretation,T_fit=settings['T_fit'],n_N=nN,
                inputs=[dict(path=S100,sha256=hashlib.sha256((Path(root)/S100).read_bytes()).hexdigest(),
                             source_id='S100',extraction_id='T006-S100-FigS5',status='verified_by_D15; original_CSV_status_preserved')],
                host=dict(q_sat=float(result.x[0]),b=float(result.x[1]),metrics=host_metrics),models=outputs,
                limitations=['one-temperature fit: Q, humidity, kinetics unknown', 'porosity decomposition conditional: kappa=f_in/(rho_PEI*V_p0), c_conn=1',
                             'n_N*A0 identifiable at best, not n_N and A0 separately', 'experimental uncertainty unknown: no formal pass',
                             'C fit is control reproduction, not independent validation'])


def fit_carrier(frame, *, T_ref=298., bounds=((.001,100.),(1e-5,1000.),(0.,100000.))):
    """One gas/material/article, several T; no cross-batch pooling."""
    p,T,q = (frame[k].to_numpy(float) for k in ('p_bar','T_K','q_mmol_g'))
    if len(np.unique(T)) < 2:
        raise ValueError('Q fit requires multiple C temperatures')
    if np.any(~np.isfinite([p,T,q])) or min(p)<0 or min(q)<0:
        raise ValueError('invalid C rows')
    sigma=frame['u_q'].to_numpy(float)
    if np.any(sigma<=0):
        raise ValueError('positive C uncertainty required')
    def predict(x):
        b=x[1]*np.exp(x[2]/8.31446261815324*(1/T-1/T_ref))
        return x[0]*b*p/(1+b*p)
    fit=_solve(lambda x:(predict(x)-q)/sigma,[(5.,.5,20000.),(20.,.05,10000.)],tuple(np.array(bounds).T))
    return dict(q_sat=float(fit.x[0]),b=float(fit.x[1]),Q=float(fit.x[2]),T_ref=T_ref,
                metrics=metrics(q,predict(fit.x),sigma),optimizer_success=bool(fit.success))


def provisional_carriers(root):
    """Only two explicit D-12 DOI prefixes are ever enumerated/opened."""
    from pet2mof.data.nist_isodb import load_isotherm
    groups={}
    for prefix in ('10.1021acs.inorgchem.5b00435.', '10.1039C2cp23839j.'):
        for path in sorted((Path(root)/'data/raw/nist_isodb/isotherms').glob(prefix+'*.json')):
            raw=json.loads(path.read_text())
            material=raw.get('adsorbent',{}).get('name')
            gas=[v['name'] for v in raw.get('adsorbates',[])]
            if raw.get('DOI') not in ALLOWED_DOIS or material not in ('UiO-66','UiO-66-NH2') or gas not in (['Carbon Dioxide'],['Nitrogen']):
                continue
            if raw.get('category') not in ('exp', ''):
                continue
            f=load_isotherm(path)
            rows=pd.DataFrame(dict(p_bar=f.pressure_bar,T_K=raw['temperature'],q_mmol_g=f.adsorption_mmol_g,
                                   u_q=max(.03*float(f.adsorption_mmol_g.max()-f.adsorption_mmol_g.min())/np.sqrt(3),1e-5)))
            key=(raw['DOI'],material,gas[0])
            groups.setdefault(key,[]).append((rows,path,raw))
    results=[]
    for key,items in groups.items():
        fitted=fit_carrier(pd.concat([v[0] for v in items]))
        fitted.update(DOI=key[0],material=key[1],gas=key[2],status='provisional_debug',
                      limitation='unverified NIST coordinates; blank category/unknown branch records are only a pooled debug alternative, not established experiment',
                      uncertainty='3% observed range lower-bound proxy; full source scale/error unknown',
                      inputs=[dict(path=str(v[1].relative_to(root)),sha256=hashlib.sha256(v[1].read_bytes()).hexdigest(),
                                   source_id=key[0],extraction_id='T002-'+v[2]['filename'],category=v[2]['category']) for v in items])
        results.append(fitted)
    return results


def verified_carriers(root, manifest='data/processed/c_series/manifest.yaml'):
    """T011v contract: explicit whole-series allowlist and immutable file hashes.

    Manifest format: series: [{path, sha256, source_id, extraction_id,
    material, gas, status: verified}]. CSV: p_bar,T_K,q_mmol_g,u_q.
    T011 adapter may be needed when its actual accepted schema becomes available.
    """
    import yaml
    root=Path(root).resolve()
    path=root/manifest
    if not path.is_file():
        raise FileNotFoundError('verified C-series manifest missing; use explicit debug NIST mode only')
    groups={}
    for item in yaml.safe_load(path.read_text())['series']:
        candidate=(root/item['path']).resolve()
        candidate.relative_to(root/'data/processed/c_series')
        if item['status']!='verified' or not item['source_id'] or not item['extraction_id']:
            raise ValueError('C input lacks verified provenance')
        if hashlib.sha256(candidate.read_bytes()).hexdigest()!=item['sha256']:
            raise ValueError('C input hash mismatch')
        key=(item['source_id'],item['material'],item['gas'])
        groups.setdefault(key,[]).append(pd.read_csv(candidate))
    return [dict(source_id=k[0],material=k[1],gas=k[2],status='verified_C_fit',**fit_carrier(pd.concat(v))) for k,v in groups.items()]
