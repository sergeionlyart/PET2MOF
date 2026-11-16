"""C-only structural comparisons on the T011 contract; no holdout discovery."""
import numpy as np
from scipy.linalg import cholesky, solve_triangular
from scipy.optimize import least_squares
from pet2mof.data.c_series import load_series, standard_errors
from pet2mof.model.revision import dry_prediction, VERSIONS
from pet2mof.model.isotherms import affinity, hill
from pet2mof.model.gas import p_sat
from .fit import loading, _solve
from .metrics import metrics, aicc
from pet2mof.model.config import load_config


def covariance_csv(f, shared_fraction=.5):
    """Frozen model-independent slopes. Half of each CSV variance shared per series.

    The split is a debug correlation assumption, not a new error magnitude. Total
    marginal variance is exactly (q_err**2 + slope**2*p_err**2)/3.
    """
    if not 0 <= shared_fraction < 1:
        raise ValueError('shared covariance fraction must lie in [0,1)')
    slope = np.zeros(len(f))
    for sid in f.series_id.unique():
        idx = np.flatnonzero((f.series_id == sid).to_numpy())
        order = idx[np.argsort(f.p_bar.to_numpy()[idx])]
        slope[order] = np.gradient(f.q_mmol_g.to_numpy()[order], f.p_bar.to_numpy()[order])
    sigma = standard_errors(f, slope)
    C = np.diag(sigma*sigma*(1-shared_fraction))
    for sid in f.series_id.unique():
        mask = (f.series_id == sid).to_numpy()
        for vec in (f.q_err_mmol_g.to_numpy()*np.sqrt(shared_fraction/3), slope*f.p_err_bar.to_numpy()*np.sqrt(shared_fraction/3)):
            v = mask*vec
            C += np.outer(v, v)
    return C


def complete_metrics(f, pred, C, *, inputs_note='nominal loading and capacity basis unresolved; experimental uncertainty unknown'):
    out = metrics(f.q_mmol_g, pred, np.sqrt(np.diag(C)))
    out['criteria'] = dict(MAE=out['MAE'] <= out['mean_U'], coverage=out['fraction_within_U'] >= .9,
                           Bias=abs(out['Bias']) <= out['mean_U']/2,
                           physical_inputs_known=False)
    out['physical_inputs_note'] = inputs_note
    out['all_protocol_criteria'] = False
    out['series'] = {}
    for sid in f.series_id.unique():
        mask = (f.series_id == sid).to_numpy()
        m = metrics(f.q_mmol_g.to_numpy()[mask], np.asarray(pred)[mask], np.sqrt(np.diag(C))[mask])
        m['criteria'] = dict(MAE=m['MAE'] <= m['mean_U'], coverage=m['fraction_within_U'] >= .9,
                             Bias=abs(m['Bias']) <= m['mean_U']/2)
        # Pressure bins fixed before fitting, expressed in measured absolute bar.
        m['pressure_bins'] = {}
        for label, lower, upper in [('low', 0., .2), ('mid', .2, .6), ('high', .6, 2.)]:
            sel = mask & (f.p_bar.to_numpy() >= lower) & (f.p_bar.to_numpy() < upper)
            if sel.any():
                m['pressure_bins'][label] = metrics(f.q_mmol_g.to_numpy()[sel], np.asarray(pred)[sel], np.sqrt(np.diag(C))[sel])
        out['series'][sid] = m
    out['all_series_numerical_criteria'] = all(m['within_conditional_tolerances'] for m in out['series'].values())
    return out


def fit_revision(root, settings, interpretation, version, *, profiles=True):
    from pathlib import Path
    root = Path(root)
    revision_settings = load_config(root/'configs/revision.yaml')
    branch_settings = revision_settings['branches'][version]
    f = load_series(root, sources=('S100',), roles=('C',), debug=True)
    omitted = f[f.status != 'verified'][['series_id', 'extraction_id', 'status']].to_dict('records')
    f = f[f.status == 'verified'].reset_index(drop=True)
    f['w'] = [loading(v, interpretation) for v in f.material]
    host = f[f.w == 0].reset_index(drop=True)
    C0 = covariance_csv(host, revision_settings['covariance_shared_fraction']); L0 = cholesky(C0, lower=True)
    def hp(x, p):
        return x[0]*x[1]*p/(1+x[1]*p)
    h = _solve(lambda x: solve_triangular(L0, hp(x, host.p_bar.to_numpy())-host.q_mmol_g, lower=True),
               settings['host_starts'], tuple(np.array(settings['host_bounds']).T))
    pei = f[f.w > 0].reset_index(drop=True)
    p, w, q = (pei[c].to_numpy() for c in ('p_bar', 'w', 'q_mmol_g'))
    hostq = hp(h.x, p)
    C = covariance_csv(pei, revision_settings['covariance_shared_fraction']); L = cholesky(C, lower=True)
    outputs = {}
    for name in ('M1', 'B1'):
        baseline = name == 'B1'
        columns = ['eta0', 'K_d'] if baseline else ['A0', 'lam', 'K_d', 'kappa']
        bounds = np.array(settings[name+'_bounds']).T.copy()
        starts = np.array(settings[name+'_starts']).copy()
        if not baseline:
            if version == 'v1.1-connectivity':
                bounds[:, 3] = branch_settings['kappa_bounds']
                bounds = np.column_stack([bounds, branch_settings['power_bounds']])
                starts[:, 3] = [2., 3., 4.]
                starts = np.column_stack([starts, [2., 4., 8.]])
                columns += ['power']
            else:
                bounds[1, 3] = min(bounds[1, 3], float(np.min((1-w)/w)))
        predict = lambda x: dry_prediction(p, w, hostq, settings['n_N'], x, version, baseline)
        fun = lambda x: solve_triangular(L, predict(x)-q, lower=True)
        fit = _solve(fun, starts, tuple(bounds))
        chi2 = float(fit.fun @ fit.fun)
        profile = {}
        if profiles and 'power' in columns:
            rows = []
            grid = np.unique(np.r_[np.linspace(*branch_settings['power_bounds'], branch_settings['profile_points']), fit.x[-1]])
            for power in grid:
                candidates = [least_squares(lambda y: fun(np.r_[y, power]), start,
                                            bounds=(bounds[0, :-1], bounds[1, :-1]), max_nfev=1500)
                              for start in (fit.x[:-1], starts[0, :-1], starts[2, :-1])]
                pr = min(candidates, key=lambda x: x.fun @ x.fun)
                rows.append(dict(fixed=float(power), chi2=float(pr.fun @ pr.fun),
                                 delta_chi2=float(pr.fun @ pr.fun)-chi2, success=bool(pr.success),
                                 parameters=dict(zip(columns, np.r_[pr.x, power].tolist()))))
            profile['power'] = rows
        pred = predict(fit.x)
        outputs[name] = dict(parameters=dict(zip(columns, fit.x.tolist())), chi2=chi2,
            k=len(columns), n_independent=4, AICc=aicc(chi2, len(columns), 4),
            AICc_reason='four whole PEI isotherms; undefined if n <= k+1; no point-count substitute',
            optimizer_success=bool(fit.success), profiles=profile,
            jacobian_singular_values=np.linalg.svd(fit.jac, compute_uv=False).tolist(),
            metrics=complete_metrics(pei, pred, C),
            predictions=[dict(series_id=str(s), p_bar=float(pp), w=float(ww), q_observed=float(qq),
                              q_predicted=float(v), error=float(v-qq), extraction_id=str(e))
                         for s, pp, ww, qq, v, e in zip(pei.series_id, p, w, q, pred, pei.extraction_id)])
    inputs = f[['input_path', 'input_sha256', 'extraction_id']].drop_duplicates().to_dict('records')
    return dict(model_version=version, interpretation=interpretation, status='debug_C_fit', T_fit=settings['T_fit'],
                n_N=settings['n_N'], inputs=inputs, provisional_rows_not_fitted=omitted,
                observation_basis='dry_composite' if version == 'v1' else 'dry_MOF',
                covariance=C.tolist(), host=dict(q_sat=float(h.x[0]), b=float(h.x[1]),
                    metrics=complete_metrics(host, hp(h.x, host.p_bar.to_numpy()), C0)), models=outputs)


def carrier_water_fits(root):
    """Actual S105/S106 adapter, debug until T011v; no pooling of defect samples."""
    f = load_series(root, sources=('S105', 'S106'), debug=True)
    shared = load_config(root/'configs/revision.yaml')['covariance_shared_fraction']
    results = {'carriers': [], 'water': [], 'status': 'debug_candidate_only'}
    for (source, material, gas), g in f.groupby(['source_id', 'material', 'gas']):
        if material != 'UiO-66' and not (source == 'S106' and material.startswith('UiO-66_')):
            continue
        p, T, q = (g[c].to_numpy(float) for c in ('p_bar', 'T_K', 'q_mmol_g'))
        C = covariance_csv(g.reset_index(drop=True),shared); L = cholesky(C, lower=True)
        if source == 'S105':
            multi = len(np.unique(T)) > 1
            def predict(x):
                b = x[1]*np.exp((x[2] if multi else 0.)/8.31446261815324*(1/T-1/298.))
                return x[0]*b*p/(1+b*p)
            bounds = ([.001, .00001, 0.], [100., 1000., 100000.]) if multi else ([.001, .00001], [100., 1000.])
            starts = [[5., .5, 20000.], [20., .05, 10000.]] if multi else [[1., .1], [5., .01]]
            fit = _solve(lambda x: solve_triangular(L, predict(x)-q, lower=True), starts, bounds)
            result = dict(q_sat=float(fit.x[0]), b=float(fit.x[1]), Q=float(fit.x[2]) if multi else None,
                          T_ref=298., Q_note='fit_on_C_candidate' if multi else 'unknown: one temperature')
            section = 'carriers'
        else:
            a = p / p_sat(float(T[0]))
            def predict(x):
                return x[0]*a**x[2]/(x[1]**x[2]+a**x[2])
            fit = _solve(lambda x: solve_triangular(L, predict(x)-q, lower=True), [[20., .3, 4.], [25., .5, 8.]],
                         ([.001, .001, 1.], [100., 2., 30.]))
            result = dict(q_max=float(fit.x[0]), a_s=float(fit.x[1]), m=float(fit.x[2]), T_ref=float(T[0]), Q=None,
                          Q_note='unknown: one temperature; temperature extrapolation requires explicit stress Q_W',
                          equivalent_volume_cm3_g=float(fit.x[0])*.01801528)
            section = 'water'
        result.update(source_id=source, material=material, gas=gas, status='provisional_debug',
                      metrics=complete_metrics(g.reset_index(drop=True), predict(fit.x), C,
                          inputs_note='candidate coordinates and experimental uncertainty unverified; inter-article transfer conditional'),
                      inputs=g[['input_path', 'input_sha256', 'extraction_id']].drop_duplicates().to_dict('records'))
        results[section].append(result)
    return results


def make_revision_model(fit, c_fits, scenario, *, transfer='S100-own-temperature-ratio-S105', defect='UiO-66_100'):
    """Nominal neutral scenario; all states per dry composite, never MOF-normalized.

    Vp from S106 equivalent water volume, CO2 Q and N2 from S105 are explicit
    inter-article transfers. N2 Q=lower stress endpoint, NOT a measured zero.
    """
    from pet2mof.model.isotherms import Isotherm, Site
    from pet2mof.model.amines import Amines
    from pet2mof.model.pores import Pores
    from pet2mof.model.cycle import Model
    carrier = {r['gas']:r for r in c_fits['carriers']}
    water = next(r for r in c_fits['water'] if r['material']==defect)
    if transfer not in ('S100-own-temperature-ratio-S105','S105-full-carrier'):
        raise ValueError('unknown carrier transfer branch')
    host = fit['host'] if transfer=='S100-own-temperature-ratio-S105' else carrier['CO2']
    co2=Isotherm((Site(host['q_sat'],host['b'],carrier['CO2']['Q']),),fit['T_fit'])
    n2=Isotherm((Site(carrier['N2']['q_sat'],carrier['N2']['b'],scenario['screen_bounds']['Q_n2'][0]),),298.)
    m=fit['models']['M1']['parameters'];vp=water['equivalent_volume_cm3_g']
    pores=dict(scenario['pores']);pores['V_p0']=vp
    if fit['model_version']=='v1.1-connectivity':
        pores.update(f_in=0.,connectivity_kappa=m['kappa'],connectivity_power=m['power'])
    else:
        pores['f_in']=m['kappa']*pores['rho_pei']*vp
    am=Amines(fit['n_N'],m['A0'],m['lam'],m['K_d'],Q_d=scenario['chemical_heat'],T_ref=fit['T_fit'],water_limited=True)
    return Model(co2,n2,Pores(**pores),am,dict(p_s_ref=water['a_s']*p_sat(water['T_ref']),m=water['m'],
              Q=scenario['water_step']['Q'],T_ref=water['T_ref']))
