"""D-07 screening: full factorial structure/loading/mechanism/transfer/defect.

512 common random stress draws in EVERY cell, repeated with a second seed.
This is sensitivity, not a posterior or a hypothesis acceptance ensemble.
"""
from itertools import combinations
import numpy as np
from scipy.stats import rankdata
from pet2mof.model.batch import endpoint_grid, periodic_endpoints, iast_batch
from pet2mof.model.gas import p_sat
from .screening import BRANCHES


def draws(scenario, count, seed, branch, product, settings=None):
    rng = np.random.default_rng(seed)
    p = {k:rng.uniform(*v, count) for k,v in scenario['screen_bounds'].items()}
    p['tau_over_t'] = rng.choice(scenario['tau_grid'], count)
    p['f1'], p['f2'], p['f3'] = rng.dirichlet([1.,1.,1.], count).T
    p['n_N'] = rng.uniform(max(scenario['screen_bounds']['n_N'][0], product), scenario['screen_bounds']['n_N'][1], count)
    p['kappa_fraction'] = rng.uniform(0., 1., count)
    p['alpha_fraction'] = rng.uniform(0., 1., count)
    settings = settings or {}
    p['water_volume_transfer'] = rng.uniform(*settings.get('water_volume_transfer_bounds', [.25,4.]), count)
    power_bounds = settings.get('branches',{}).get('v1.1-connectivity',{}).get('power_bounds',[1.,12.])
    p['power'] = rng.uniform(*power_bounds, count)
    if branch == 'neutral': p.update(gamma=np.zeros(count), h_max=np.zeros(count), xi=np.zeros(count))
    if branch == 'availability': p.update(gamma=abs(p['gamma']), h_max=np.zeros(count), xi=np.zeros(count))
    if branch == 'bicarbonate': p.update(gamma=np.zeros(count), xi=np.zeros(count))
    if branch == 'suppression': p.update(gamma=-np.minimum(abs(p['gamma']),1.), h_max=np.zeros(count), xi=np.zeros(count))
    if branch == 'affinity': p.update(gamma=np.zeros(count), h_max=np.zeros(count))
    return p


def feasible_parameters(raw, water, version, max_w=.3):
    p = {k:v.copy() for k,v in raw.items()}
    p['V_p0'] = water['equivalent_volume_cm3_g']*p['water_volume_transfer']
    if version == 'v1.1-connectivity':
        p['kappa'] = p['kappa_fraction']*10.
        dry_min = (1-max_w)*p['V_p0']*np.exp(-(p['kappa']*max_w/(1-max_w))**p['power'])
    else:
        cap = np.minimum(2.3, 1/(p['rho_pei']*p['V_p0']))
        p['kappa'] = p['kappa_fraction']*cap
        dry_min = (1-max_w-p['kappa']*max_w)*p['V_p0']
    # Bound for ALL 0<=a<=1, not only the humidity at the evaluated endpoint.
    max_water = max_w*p['W_max']/(p['K_WP']+1)
    p['alpha_in'] = p['alpha_fraction']*np.minimum(1., dry_min/(.01801528/p['rho_water']*max_water))
    return p


def gas_arrays(p, kind, RH=None):
    if kind == 'ads':
        T = np.full(len(p['Q_d']), 308.15); P = np.ones_like(T)
        a = np.full_like(T, RH/100)
        pw = a*p_sat(308.15)
        pc, pn = .05*(P-pw), .95*(P-pw)
    else:
        T = p['T_'+kind]; P = np.ones_like(T) if kind == 'R1' else p['P_R2']
        pc = P*p['y_'+kind+'_C']; pw = P*p['y_'+kind+'_W']; pn = P-pc-pw
        a = pw/np.array([p_sat(float(t)) for t in T])
    return dict(T=T, P=P, p_C=pc, p_N=pn, a=a)


def diagnostics_batch(q, grid):
    ties = np.isclose(q, q.max(axis=1)[:,None], rtol=0, atol=1e-9)
    lo = np.min(np.where(ties, grid, np.inf), axis=1)
    hi = np.max(np.where(ties, grid, -np.inf), axis=1)
    delta = q.max(axis=1)-np.maximum(q[:,0], q[:,-1])
    return lo, hi, delta


def correlations(params, targets):
    # Rank once per coordinate. Diagnostic associations; inactive inputs excluded
    # downstream when selecting source priorities, but retained in machine output.
    xs = {k:rankdata(v) for k,v in params.items() if np.std(v)>1e-12}
    out = {}
    for name, y in targets.items():
        if np.std(y) < 1e-12:
            continue
        ry = rankdata(y)
        out[name] = {k:float(np.corrcoef(x, ry)[0,1]) for k,x in xs.items()}
    return out


def screen_cell(fit, carrier, water, p, version, transfer, branch, grid):
    idx = np.array([np.argmin(abs(grid-w)) for w in (0., .1, .2, .3)])
    ads = {RH:endpoint_grid(fit, carrier, water, p, grid, gas_arrays(p,'ads',RH), version=version, transfer=transfer)
           for RH in (0.,40.,70.)}
    dry = ads[0.][..., [0,2,3]].sum(axis=-1)[:,idx]
    summary = {}; raw = {'dry':dry}; targets = {}
    wg=grid[None,:]
    dry_volume=((1-wg)*p['V_p0'][:,None]*np.exp(-(p['kappa'][:,None]*wg/(1-wg))**p['power'][:,None])
                if version=='v1.1-connectivity' else (1-wg-p['kappa'][:,None]*wg)*p['V_p0'][:,None])
    def baseline_endpoint(gas):
        host=fit['host'] if transfer=='S100-own-temperature-ratio-S105' else carrier['CO2']
        cc,_=iast_batch(gas['p_C'],gas['p_N'],gas['T'],host['q_sat'],host['b'],p['Q_phys'],
                       carrier['N2']['q_sat'],carrier['N2']['b'],p['Q_n2'])
        b=fit['models']['B1']['parameters']
        kd=b['K_d']*np.exp(p['Q_d']/8.31446261815324*(1/gas['T']-1/fit['T_fit']))
        # n_N*eta is preserved under N stress, as in T013. No water pool in B1.
        chem=fit['n_N']*b['eta0']*kd*gas['p_C']/(1+kd*gas['p_C'])
        return (1-grid[None,:])*cc[:,None],grid[None,:]*chem[:,None]
    baseads={RH:baseline_endpoint(gas_arrays(p,'ads',RH)) for RH in (0.,40.,70.)}
    for kind in ('R1', 'R2'):
        des = endpoint_grid(fit, carrier, water, p, grid, gas_arrays(p,kind), version=version, transfer=transfer)
        base_des=baseline_endpoint(gas_arrays(p,kind))
        ds = {}
        for RH in (0.,40.,70.):
            a, d = periodic_endpoints(ads[RH], des, p['tau_over_t']*1800., p['t_ads'], p['t_des'], coupled=branch=='bicarbonate')
            if np.any(a[...,3]-a[...,5]>1e-10) or np.any(d[...,3]-d[...,5]>1e-10):
                raise ValueError('retained bicarbonate without stoichiometric water')
            # Check both endpoints and pore geometry; convexity also protects the path.
            nu = np.minimum(.5, p['f1']+p['f2'])[:,None]
            for state in (a,d):
                used = state[...,2]/nu+state[...,3]
                if np.any(used-grid[None,:]*p['n_N'][:,None]>1e-9):
                    raise ValueError('retained nitrogen budget exceeded')
                water_volume=.01801528/p['rho_water'][:,None]*(state[...,4]+p['alpha_in'][:,None]*state[...,5])
                if np.any(water_volume-dry_volume>1e-10):
                    raise ValueError('retained water exceeds dry pore volume')
            q = (a-d)[..., [0,2,3]].sum(axis=-1)
            ba=np.zeros_like(a);bd=np.zeros_like(d)
            ba[...,0],ba[...,2]=baseads[RH];bd[...,0],bd[...,2]=base_des
            bca,bcd=periodic_endpoints(ba,bd,p['tau_over_t']*1800.,p['t_ads'],p['t_des'],coupled=False)
            baseq=(bca-bcd)[...,[0,2]].sum(axis=-1)[:,idx]
            lo, hi, delta = diagnostics_batch(q, grid)
            candidate = q[:,idx]
            unique = np.sum(np.isclose(candidate,candidate.max(axis=1)[:,None],atol=1e-9,rtol=0),axis=1)==1
            best = np.argmax(candidate, axis=1)
            probabilities = [float(np.mean((best==i)&unique)) for i in range(4)]
            winner = int(np.argmax(probabilities))
            contrasts = candidate[:,winner,None]-np.delete(candidate,winner,axis=1)
            # Conservative familywise 95% bounds, all three potential competitors.
            lower = np.quantile(contrasts,.025/3,axis=0)
            wci = [float(np.quantile(lo,.05)), float(np.quantile(hi,.95))]
            delta_ci = np.quantile(delta,[.025,.975]).tolist()
            interior = delta_ci[0]>0 and wci[0]>0 and wci[1]<.3
            winner_resolved = probabilities[winner]>=.8 and min(lower)>0
            key = f'{kind}_RH{RH:g}'
            pairs=[]
            for i,j in combinations(range(4),2):
                dd = dry[:,i]-dry[:,j]; wd = candidate[:,i]-candidate[:,j]
                pairs.append(dict(pair=[i,j], inversion_probability=float(np.mean(dd*wd<0)),
                                  dry_interval=np.quantile(dd,[.025/24,1-.025/24]).tolist(),
                                  wet_interval=np.quantile(wd,[.025/24,1-.025/24]).tolist()))
            summary[key] = dict(w_star_90=wci,delta_95=delta_ci,
                unique_winner_probabilities=probabilities, preferred_candidate=[0.,.1,.2,.3][winner],
                simultaneous_winner_lower=lower.tolist(), interior=bool(interior), winner_resolved=bool(winner_resolved),
                monotone_up_probability=float(np.mean(np.all(np.diff(q,axis=1)>=-1e-9,axis=1))),
                monotone_down_probability=float(np.mean(np.all(np.diff(q,axis=1)<=1e-9,axis=1))), H1a_pairs=pairs)
            summary[key]['baseline_unique_winner_probabilities']=[float(np.mean((np.argmax(baseq,axis=1)==i)&
                (np.sum(np.isclose(baseq,baseq.max(axis=1)[:,None],atol=1e-9,rtol=0),axis=1)==1))) for i in range(4)]
            ds[RH]=(lo,hi,delta)
            targets[key+'/endpoint_contrast']=candidate[:,-1]-candidate[:,0]
            targets[key+'/interior']=(lo>0)&(hi<.3)
            targets[key+'/rank_0.2']=np.sum(candidate>candidate[:,2,None]+1e-9,axis=1)+1
            targets[key+'/delta']=delta
            # Raw compact evidence: all four q_work, dense-grid maximizers and Delta.
            raw[key]=np.column_stack([candidate,lo,hi,delta])
            raw[key+'/B1']=baseq
        shift = summary[f'{kind}_RH0']['w_star_90'][1] < summary[f'{kind}_RH70']['w_star_90'][0] or summary[f'{kind}_RH70']['w_star_90'][1] < summary[f'{kind}_RH0']['w_star_90'][0]
        for RH in (40.,70.):
            contrast = ds[RH][2]-ds[0.][2]
            summary[f'{kind}_RH{RH:g}']['delta_vs_dry_95']=np.quantile(contrast,[.025,.975]).tolist()
            summary[f'{kind}_RH{RH:g}']['w_star_shift_resolved']=bool(shift) if RH==70 else None
            targets[f'{kind}_RH{RH:g}/delta_vs_dry']=contrast
        summary[f'{kind}_conditional_H1'] = bool(summary[f'{kind}_RH70']['interior'] and summary[f'{kind}_RH70']['winner_resolved'] and shift and
             np.prod(summary[f'{kind}_RH70']['delta_vs_dry_95'])>0)
    return summary, correlations(p,targets), raw


def screen_revision(root, demo, scenario, settings, *, count=None, seeds=None):
    from pathlib import Path
    root = Path(root)
    count = settings['samples'] if count is None else count
    seeds = settings['seeds'] if seeds is None else seeds
    if count < 512:
        raise ValueError('T015 requires >=512 sets in every cell')
    grid = np.round(np.arange(0.,.30001,scenario['dense_step']),8)
    carrier = {r['gas']:r for r in demo['c_fits']['carriers']}
    out = dict(status='debug', scientific_status='проверяемый прогноз; данных недостаточно',
               samples_per_cell=count, seeds=seeds, rng='numpy.PCG64', numpy_version=np.__version__,
               sampling_measure='uniform stress intervals; joint N,kappa,alpha geometry constraints; common random numbers across transfer/defect branches',
               correlations_selection_threshold=settings['correlation_selection_threshold'], branches={})
    out['raw_evidence'] = []
    for seed in seeds:
        evidence = {}
        for fi,fit in enumerate(demo['fits']):
            version=fit['model_version']; interpretation=fit['interpretation']
            for bi,branch in enumerate(BRANCHES):
                ss=np.random.SeedSequence([seed,fi,bi])
                raw=draws(scenario,count,ss,branch,fit['n_N']*fit['models']['M1']['parameters']['A0'],settings)
                stem=f'{seed}/{version}/{interpretation}/{branch}'
                evidence[stem+'/parameter_names']=np.array(sorted(raw))
                evidence[stem+'/draws']=np.column_stack([raw[k] for k in sorted(raw)])
                for transfer in settings['transfer_branches']:
                    for water in demo['c_fits']['water']:
                        key=stem+'/'+transfer+'/'+water['material']
                        p=feasible_parameters(raw,water,version)
                        summary,cor,values=screen_cell(fit,carrier,water,p,version,transfer,branch,grid)
                        out['branches'][key]=dict(attempted=count,accepted=count,rejected=0,rejected_fraction=0.,
                             status='debug_only', summary=summary,rank_correlations=cor,verdict='данных недостаточно')
                        for name,value in values.items(): evidence[key+'/'+name]=value
                        evidence[key+'/derived_names']=np.array(['V_p0','kappa','alpha_in'])
                        evidence[key+'/derived']=np.column_stack([p[k] for k in ('V_p0','kappa','alpha_in')])
        print(f'screen seed {seed}: {len(out["branches"])} cells complete',flush=True)
        path=root/f'reports/T015/screen_samples_{seed}.npz'
        np.savez_compressed(path,**evidence)
        out['raw_evidence'].append(path.relative_to(root).as_posix())
    out['raw_columns']='dry: w=0,.1,.2,.3; each condition: q_work[4], min(w*), max(w*), Delta; all q per g dry composite'
    return out
