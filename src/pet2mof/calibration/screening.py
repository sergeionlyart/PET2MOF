"""Small D-07 stress ensemble. Every branch remains separate; never a prior claim."""
from dataclasses import replace
from itertools import combinations
import numpy as np
from scipy.stats import spearmanr
from pet2mof.model import Inadmissible
from pet2mof.model.gas import wet_gas, regeneration, p_sat
from pet2mof.model.cycle import periodic_cycle, co2_total, heat
from .demo import make_models

BRANCHES=('neutral','availability','bicarbonate','suppression','affinity')


def draw(rng, scenario, branch):
    p={k:float(rng.uniform(*v)) for k,v in scenario['screen_bounds'].items()}
    p['tau_over_t']=float(rng.choice(scenario['tau_grid']))
    p['f1'],p['f2'],p['f3']=rng.dirichlet(np.ones(3)).tolist()
    # Explicit joint sampling measure: keep all compositions feasible for dry
    # placement and PEI water before evaluating any outcome. This changes the
    # ignorance measure, not an invalid calculated state. Values are saved.
    kappa_limit=min(scenario['screen_bounds']['kappa'][1],1/(p['rho_pei']*p['V_p0']))
    p['kappa']=float(rng.uniform(0,kappa_limit))
    w_max=max(scenario['w_grid'])
    dry_min=((1-w_max)-p['kappa']*w_max)*p['V_p0']
    max_water=w_max*p['W_max']*.7/(p['K_WP']+.7)
    alpha_limit=min(1.,dry_min/(.001*18.01528/p['rho_water']*max_water))
    p['alpha_in']=float(rng.uniform(0,alpha_limit))
    # Mechanisms are alternatives. No mixing hidden in a shared ensemble.
    if branch=='neutral':p.update(gamma=0.,h_max=0.,xi=0.)
    if branch=='availability':p.update(gamma=abs(p['gamma']),h_max=0.,xi=0.)
    if branch=='bicarbonate':p.update(gamma=0.,xi=0.)
    if branch=='suppression':p.update(gamma=-min(abs(p['gamma']),1.),h_max=0.,xi=0.)
    if branch=='affinity':p.update(gamma=0.,h_max=0.)
    return p


def diagnostics(values, grid):
    """Preserve tied maxima; Delta >= 0 by definition, also save neighbour slopes."""
    q=np.asarray(values)
    best=np.flatnonzero(np.isclose(q,q.max(),atol=1e-9,rtol=0))
    ranks=[int(1+np.sum(q>v+1e-9)) for v in q]
    return dict(w_star=[float(grid[i]) for i in best],delta=float(q.max()-max(q[0],q[-1])),
                endpoint_contrast=float(q[-1]-q[0]),slopes=np.sign(np.diff(q)).astype(int).tolist(),ranks=ranks)


def screen(fits, carriers, scenario, *, count=None, seed=None):
    count=scenario['n_screen'] if count is None else count
    seed=scenario['seed'] if seed is None else seed
    if count<2:raise ValueError('screen needs >=2 attempted samples per branch')
    result={'status':'debug','seed':seed,'rng':'numpy.PCG64','numpy_version':np.__version__,
            'sampling_measure':'uniform stress intervals; joint feasible kappa and alpha_in conditional on V_p0,rho,W_max,K_WP, max w and RH; N simplex Dirichlet(1,1,1)',
            'scientific_status':'проверяемый прогноз; данных недостаточно','branches':{}}
    grid=np.round(np.arange(0,.3+scenario['dense_step']/2,scenario['dense_step']),8)
    candidates=np.array(scenario['w_grid'])
    candidate_indices=[int(np.argmin(abs(grid-w))) for w in candidates]
    for interpretation_index,fit in enumerate(fits):
        original,baseline=make_models(fit,carriers,scenario)
        for branch_index,branch in enumerate(BRANCHES):
            rng=np.random.Generator(np.random.PCG64(np.random.SeedSequence([seed,interpretation_index,branch_index])))
            accepted=[];rejected=[]
            for sample in range(count):
                p=draw(rng,scenario,branch)
                # f_in,alpha,volume constrained jointly rather than silently truncating volumes.
                f_in=p['kappa']*p['rho_pei']*p['V_p0']
                try:
                    pores=replace(original.pores,V_p0=p['V_p0'],rho_pei=p['rho_pei'],f_in=f_in,
                                  rho_water=p['rho_water'],alpha_in=p['alpha_in'],W_max=p['W_max'],K_WP=p['K_WP'])
                    am=replace(original.amines,n_N=p['n_N'],A0=original.amines.n_N*original.amines.A0/p['n_N'],
                               **{k:p[k] for k in ('gamma','h_max','K_h','K_b','Q_d','Q_b','f1','f2','f3')})
                    # Physical Q and water Q are the same scenario in equilibrium and heat.
                    co2=replace(original.co2,sites=tuple(replace(s,Q=p['Q_phys']) for s in original.co2.sites))
                    n2=replace(original.n2,sites=tuple(replace(s,Q=p['Q_n2']) for s in original.n2.sites))
                    model=replace(original,pores=pores,amines=am,co2=co2,n2=n2,xi=p['xi'],
                                  water_step=dict(p_s_ref=p['a_s_ref']*p_sat(298.),m=p['m_W'],Q=p['Q_W'],T_ref=298.))
                    base=replace(baseline,co2=co2,n2=n2,baseline=replace(baseline.baseline,Q_d=p['Q_d'],n_N=p['n_N'],
                                 eta0=baseline.baseline.n_N*baseline.baseline.eta0/p['n_N']))
                    drygas=wet_gas(308.15,1.,0.)
                    dry=[co2_total(model.equilibrium(float(w),drygas)) for w in candidates]
                    row={'sample':sample,'parameters':p,'dry_equilibrium':dry,'conditions':{}}
                    for kind in ('R1','R2'):
                        des=regeneration(kind,T=p['T_'+kind],P=1. if kind=='R1' else p['P_R2'],
                                         y_C=p['y_'+kind+'_C'],y_W=p['y_'+kind+'_W'])
                        for RH in scenario['RH_grid']:
                            ads=wet_gas(308.15,1.,RH)
                            cycles=[periodic_cycle(model,float(w),ads,des,tau_over_t=p['tau_over_t'],
                                                   tolerance=scenario['cycle_tolerance'],t_ads=p['t_ads'],t_des=p['t_des']) for w in grid]
                            q=[c['q_work'] for c in cycles]
                            baseq=[periodic_cycle(base,float(w),ads,des,tau_over_t=p['tau_over_t'],
                                                  t_ads=p['t_ads'],t_des=p['t_des'])['q_work'] for w in candidates]
                            candidate_q=np.array(q)[candidate_indices]
                            pairs=[dict(pair=[float(candidates[i]),float(candidates[j])],dry_difference=float(dry[i]-dry[j]),
                                        wet_work_difference=float(candidate_q[i]-candidate_q[j]),
                                        opposite=bool((dry[i]-dry[j])*(candidate_q[i]-candidate_q[j])<0)) for i,j in combinations(range(4),2)]
                            energy=heat(cycles[candidate_indices[2]],.2,ads.T,des.T,**{k:p[k] for k in
                                        ('cp_mof','cp_pei','cp_water','Q_phys','Q_d','Q_b','Q_n2','epsilon_s','epsilon_d')},Q_water=p['Q_water'])
                            row['conditions'][f'{kind}_RH{RH:g}']=dict(**diagnostics(q,grid),
                                    candidates=diagnostics(candidate_q,candidates),baseline=diagnostics(baseq,candidates),
                                    q_work=q,H1a_pairs=pairs,energy=energy,max_cycle_residual=max(c['residual'] for c in cycles))
                        dry_diag=row['conditions'][f'{kind}_RH0']
                        for RH in (40.,70.):
                            diag=row['conditions'][f'{kind}_RH{RH:g}']
                            diag['delta_vs_dry']=diag['delta']-dry_diag['delta']
                            diag['w_star_shift']=[min(diag['w_star'])-max(dry_diag['w_star']),max(diag['w_star'])-min(dry_diag['w_star'])]
                    accepted.append(row)
                except (Inadmissible, ValueError, RuntimeError) as exc:
                    rejected.append(dict(sample=sample,parameters=p,reason=str(exc)))
            rejected_fraction=len(rejected)/count
            stopped=rejected_fraction>.2
            correlations={}
            # Diagnostic associations only; no hypothesis verdict after branch rejection.
            if len(accepted)>=4:
                for condition in accepted[0]['conditions']:
                    outcomes={
                        'endpoint_contrast':[r['conditions'][condition]['endpoint_contrast'] for r in accepted],
                        'w_star_mid':[np.mean(r['conditions'][condition]['w_star']) for r in accepted],
                        'delta':[r['conditions'][condition]['delta'] for r in accepted],
                        'delta_vs_dry':[r['conditions'][condition].get('delta_vs_dry',0.) for r in accepted],
                        'rank_w_0.2':[r['conditions'][condition]['candidates']['ranks'][2] for r in accepted]}
                    cor={}
                    for target,y in outcomes.items():
                        if np.std(y)==0:continue
                        cor[target]={}
                        for param in p:
                            x=[r['parameters'][param] for r in accepted]
                            if np.std(x)>1e-14:
                                rho=spearmanr(x,y).statistic
                                if np.isfinite(rho):cor[target][param]=float(rho)
                    correlations[condition]=cor
            result['branches'][fit['interpretation']+'/'+branch]=dict(attempted=count,accepted=len(accepted),rejected=len(rejected),
                rejected_fraction=rejected_fraction,status='stopped_parameterization_review' if stopped else 'debug_only',
                samples=accepted,rejections=rejected,rank_correlations=correlations,
                verdict='данных недостаточно',reason='small debug ensemble; no source-bounded priors or production convergence')
    return result
