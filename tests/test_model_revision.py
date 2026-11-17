"""Actual T011 adapter, scalar/batch integration and CO2/H2O conservation."""
from dataclasses import replace
import json
from pathlib import Path
import numpy as np
import pytest
from pet2mof.data.c_series import load_series, standard_errors
from pet2mof.model.config import load_config
from pet2mof.model.amines import Amines
from pet2mof.model.pores import Pores
from pet2mof.model.cycle import Model, periodic_cycle
from pet2mof.model.gas import Gas, wet_gas, regeneration, p_sat
from pet2mof.model.isotherms import Isotherm, Site, iast
from pet2mof.model.batch import iast_batch, endpoint_grid, periodic_endpoints
from pet2mof.model.revision import observation, dry_prediction
from pet2mof.calibration.revision import covariance_csv
from pet2mof.calibration.revision_screening import draws,feasible_parameters,gas_arrays

ROOT=Path(__file__).resolve().parents[1]


def test_json_adapter_roles_status_hash_and_csv_uncertainty(tmp_path):
    f=load_series(ROOT,sources=('S100',),debug=True)
    assert len(f)==50 and sum(f.status=='verified')==48
    with pytest.raises(ValueError,match='debug'):load_series(ROOT,sources=('S105',))
    # T011b restores eleven visible GO markers across Fig8A/C and Fig9.
    assert len(load_series(ROOT,sources=('S105',),roles=('context_GO',),debug=True))==330
    with pytest.raises(ValueError,match='permitted'):load_series(ROOT,sources=('S2',),debug=True)
    x=f[f.status=='verified'].reset_index(drop=True)
    C=covariance_csv(x)
    assert np.linalg.eigvalsh(C).min()>0
    assert standard_errors(x,np.zeros(len(x)))==pytest.approx(x.q_err_mmol_g/np.sqrt(3))
    folder=tmp_path/'data/processed/c_series';folder.mkdir(parents=True)
    m=json.loads((ROOT/'data/processed/c_series/manifest.json').read_text())
    sid=next(k for k in m['series'] if k.startswith('C-S100'))
    (folder/'manifest.json').write_text(json.dumps(dict(fields=m['fields'],series={sid:m['series'][sid]})))
    (folder/(sid+'.csv')).write_text('tampered')
    with pytest.raises(ValueError,match='hash'):load_series(tmp_path,sources=('S100',),debug=True)


def test_batch_iast_against_scalar_independent_solver():
    rng=np.random.default_rng(15);n=30
    pc=rng.uniform(.0001,.1,n);pn=rng.uniform(.05,1.,n);T=rng.uniform(290.,400.,n)
    qc=rng.uniform(2.,20.,n);bc=rng.uniform(.05,5.,n);Qc=rng.uniform(0.,60000.,n)
    qn=rng.uniform(1.,4.,n);bn=rng.uniform(.01,.3,n);Qn=rng.uniform(0.,40000.,n)
    values=iast_batch(pc,pn,T,qc,bc,Qc,qn,bn,Qn)
    for i in range(n):
        expected=iast(float(pc[i]),float(pn[i]),float(T[i]),Isotherm((Site(qc[i],bc[i],Qc[i]),)),Isotherm((Site(qn[i],bn[i],Qn[i]),)))
        assert [values[0][i],values[1][i]]==pytest.approx(expected,rel=1e-9,abs=1e-11)


@pytest.mark.parametrize('version',['v1','v1.1-mof','v1.1-connectivity'])
@pytest.mark.parametrize('branch',['neutral','availability','bicarbonate','suppression','affinity'])
def test_actual_producer_batch_consumer_scalar_and_conservation(version,branch):
    # Synthetic fit inputs avoid making outputs a prerequisite for make test.
    fit=dict(T_fit=298.,n_N=23.,host=dict(q_sat=9.,b=.3),models={'M1':{'parameters':dict(A0=.4,lam=1.,K_d=60.,kappa=.5,power=3.)}})
    carrier={'CO2':dict(q_sat=10.,b=.25),'N2':dict(q_sat=2.,b=.1)}
    water=dict(a_s=.3,m=4.,T_ref=293.,equivalent_volume_cm3_g=.4)
    scenario=load_config(ROOT/'configs/scenarios.yaml')['scenario']
    raw=draws(scenario,8,17017,branch,23*.4)
    p=feasible_parameters(raw,water,version)
    grid=np.linspace(0,.3,7);gas=gas_arrays(p,'ads',70.)
    batch=endpoint_grid(fit,carrier,water,p,grid,gas,version=version,transfer='S100-own-temperature-ratio-S105')
    scalar_models=[]
    for i in range(8):
        am=Amines(p['n_N'][i],23*.4/p['n_N'][i],1.,60.,Q_d=p['Q_d'][i],Q_b=p['Q_b'][i],
              **{k:p[k][i] for k in ('gamma','h_max','K_h','K_b','f1','f2','f3')},water_limited=True)
        pore=dict(V_p0=p['V_p0'][i],rho_pei=p['rho_pei'][i],W_max=p['W_max'][i],K_WP=p['K_WP'][i],alpha_in=p['alpha_in'][i],rho_water=p['rho_water'][i])
        if version=='v1.1-connectivity':pore.update(f_in=0.,connectivity_kappa=p['kappa'][i],connectivity_power=p['power'][i])
        else:pore['f_in']=p['kappa'][i]*p['rho_pei'][i]*p['V_p0'][i]
        model=Model(Isotherm((Site(9.,.3,p['Q_phys'][i]),)),Isotherm((Site(2.,.1,p['Q_n2'][i]),)),Pores(**pore),am,
             dict(p_s_ref=.3*p_sat(293.),m=4.,Q=p['Q_W'][i],T_ref=293.),xi=p['xi'][i],coupled_water=branch=='bicarbonate')
        scalar_models.append(model)
        for j,w in enumerate(grid):
            assert model.equilibrium(float(w),wet_gas(308.15,1.,70.))==pytest.approx(batch[i,j],rel=1e-9,abs=1e-10)
    desgas=gas_arrays(p,'R1')
    bd=endpoint_grid(fit,carrier,water,p,grid,desgas,version=version,transfer='S100-own-temperature-ratio-S105')
    a,d=periodic_endpoints(batch,bd,p['tau_over_t']*1800,p['t_ads'],p['t_des'],coupled=branch=='bicarbonate')
    assert np.min(a[...,5]-a[...,3])>=-1e-12 and np.min(d[...,5]-d[...,3])>=-1e-12
    for i,model in enumerate(scalar_models):
        dg=Gas(float(desgas['T'][i]),1.,float(desgas['p_C'][i]),float(desgas['p_N'][i]),float(p['y_R1_W'][i]))
        cyc=periodic_cycle(model,.3,wet_gas(308.15,1.,70.),dg,tau_over_t=p['tau_over_t'][i]*1800/p['t_ads'][i],
                           tau_des_over_t=p['tau_over_t'][i]*1800/p['t_des'][i])
        assert cyc['ads']==pytest.approx(a[i,-1],abs=2e-8)
        assert cyc['des']==pytest.approx(d[i,-1],abs=2e-8)
        if branch=='bicarbonate':
            # Separate free/bound water and N, with no CO2 or H2O clipping.
            assert cyc['delta_water']==pytest.approx(sum(a[i,-1,4:])-sum(d[i,-1,4:]))


def test_observation_basis_is_applied_once_and_w_zero_limit():
    for version in ('v1','v1.1-mof','v1.1-connectivity'):
        assert dry_prediction(.2,0.,1.5,23.,[.4,1.,60.,.5,3.],version)==pytest.approx(1.5)
    assert observation(1.,.2,'v1.1-mof')==1.25
    with pytest.raises(ValueError):observation(1.,1.,'v1.1-mof')


def test_bicarbonate_water_limited_even_under_tiny_water():
    am=Amines(23.,1.,0.,60.,h_max=1.,K_h=.001,K_b=10000.,water_limited=True)
    for W in (0.,1e-12,.01,10.):
        q=am.equilibrium(.3,.7,1.,298.,W)
        assert 0 <= q['b'] <= W+1e-12
        assert q['N_d']+q['N_b']==pytest.approx(q['N_acc'])


def test_bicarbonate_retains_its_water_during_dry_regeneration():
    am=Amines(23.,.5,1.,50.,h_max=.8,K_h=.1,K_b=30.,water_limited=True)
    model=Model(Isotherm((Site(5.,.5),)),Isotherm((Site(1.,.1),)),
        Pores(.5,1.05,f_in=.1,W_max=30.,K_WP=.2,alpha_in=.1),am,
        dict(p_s_ref=.3*p_sat(298.),m=4.,Q=40000.,T_ref=298.),coupled_water=True)
    cyc=periodic_cycle(model,.2,wet_gas(308.15,1.,70.),regeneration('R1',y_W=0.),tau_over_t=1.)
    assert cyc['equilibrium_des'][3]==cyc['equilibrium_des'][5]==0.
    assert cyc['des'][3]>0 and cyc['des'][5]>=cyc['des'][3]
    assert cyc['kinetic_scheme']=='common_six_pool_relaxation'
    # Constant full-state relaxation preserves free water even between endpoints.
    for t in np.linspace(0,1,11):
        state=t*np.array(cyc['ads'])+(1-t)*np.array(cyc['des'])
        assert state[5]-state[3]>=0
        assert .01801528*(state[4]+.1*state[5])<=model.pores.state(.2,0.,0.)['V_dry']+1e-12


def test_sensitivity_adapter_preserves_unknown_errors_and_blocks_fit():
    f=load_series(ROOT,sources=('NIST-10.1021Ie202325p',),roles=('sensitivity_only',),debug=True)
    assert len(f)==23 and f.q_err_mmol_g.isna().all()
    with pytest.raises(ValueError,match='unknown'):standard_errors(f,np.ones(len(f)))
    with pytest.raises(ValueError,match='debug'):load_series(ROOT,sources=('NIST-10.1021Ie202325p',),roles=('sensitivity_only',))
