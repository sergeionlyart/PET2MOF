"""Independent conservation, thermodynamic and mixture checks; no V data."""
from dataclasses import replace
import math
import numpy as np
import pytest
from pet2mof.model import Inadmissible
from pet2mof.model.gas import Gas, wet_gas, p_sat, regeneration
from pet2mof.model.isotherms import Site, Isotherm, affinity, iast, iast_numerical, hill
from pet2mof.model.pores import Pores
from pet2mof.model.amines import Amines
from pet2mof.model.baseline import Baseline
from pet2mof.model.cycle import Model, periodic_cycle, finite_fraction, co2_total, heat, selectivity
from pet2mof.units import convert_pressure, normalize_capacity


def model():
    return Model(Isotherm((Site(5.,1.,20000.),)),Isotherm((Site(2.,.1,10000.),)),
                 Pores(.6,1.05,.2,1.,.1,30.,.2),Amines(23.,.5,1.,40.,Q_d=60000.),
                 dict(p_s_ref=.015,m=5.,Q=40000.,T_ref=298.))


@pytest.mark.parametrize('T,expected',[(273.16,.00611657),(373.15,1.01417994),(647.096,220.64)])
def test_iapws_reference_transcription(T,expected):
    assert p_sat(T)==pytest.approx(expected,rel=3e-6)


def test_gas_dry_to_wet_units():
    gas=wet_gas(308.15,1.,70.)
    assert sum(gas.y)==pytest.approx(1.)
    assert gas.p_C/.05==pytest.approx(1-gas.p_W)
    assert gas.a==pytest.approx(.7)
    assert convert_pressure(gas.p_C,'bar','kPa')==pytest.approx(100*gas.p_C)
    assert gas.y[0]<.05
    assert regeneration('R2').p_C==pytest.approx(.001)
    for call in (lambda:wet_gas(373.15,.1,100.),lambda:Gas(298.,1.,.5,.6,0.),lambda:p_sat(250.)):
        with pytest.raises(ValueError):call()


@pytest.mark.parametrize('dsl',[False,True])
@pytest.mark.parametrize('pC,pN,T',[(.05,.95,308.15),(.001,.099,363.15),(.7,.3,273.16),(1.,1.,323.)])
def test_iast_independent_quadrature(dsl,pC,pN,T):
    co2=Isotherm((Site(4.,2.,20000.),Site(1.,10.,30000.)) if dsl else (Site(4.,2.,20000.),))
    n2=Isotherm((Site(2.,.1,10000.),Site(.5,.3,15000.)) if dsl else (Site(2.,.1,10000.),))
    assert iast(pC,pN,T,co2,n2)==pytest.approx(iast_numerical(pC,pN,T,co2,n2),rel=2e-8,abs=1e-10)


def test_iast_equal_capacity_extended_langmuir_and_pure_limits():
    C,N=Isotherm((Site(4.,2.),)),Isotherm((Site(4.,.1),))
    q=iast(.05,.95,298.,C,N)
    assert q==pytest.approx((4*2*.05/(1+2*.05+.1*.95),4*.1*.95/(1+2*.05+.1*.95)))
    assert iast(1.,0.,298.,C,N)==pytest.approx((C.uptake(1.,298.),0.))
    assert iast(0.,0.,298.,C,N)==(0.,0.)
    assert affinity(2.,20000.,280.)>2.
    assert C.uptake(1e-10,298.)/1e-10==pytest.approx(8.)
    with pytest.raises(ValueError):iast(-1.,1.,298.,C,N)


def test_water_hill_and_volume_conservation():
    p=Pores(.6,1.05,.2,1.,.1,30.,.2)
    for a in (0.,.4,.7,1.):
        s=p.state(.2,a,hill(a,298.,p_s_ref=.015,m=5.))
        assert s['V_dry']==pytest.approx(s['V_g']+p.v_water*s['W_M']+p.alpha_in*p.v_water*s['W_P'])
        assert s['V_host']-s['V_pei']==pytest.approx(s['V_dry'])
        assert min(s.values())>=0
    dry=p.state(.2,0.,0.)
    assert dry['W_M']==dry['W_P']==0
    with pytest.raises(Inadmissible,match='PEI volume'):
        replace(p,f_in=1.).state(.8,0.,0.)
    with pytest.raises(Inadmissible,match='water exceeds'):
        replace(p,alpha_in=1.,W_max=10000.).state(.2,.7,.5)


def test_nonoverlapping_nitrogen_pools_and_bicarbonate_water():
    a=Amines(23.,.5,1.,40.,h_max=.8,K_b=100.)
    s=a.equilibrium(.2,.7,.05,298.,10.)
    assert s['N_d']+s['N_b']==pytest.approx(s['N_acc'])
    assert s['d']/a.nu_d+s['b']<=s['N_acc']<=.2*a.n_N
    assert s['b']<=10.
    assert a.equilibrium(.2,0.,.05,298.,0.)['b']==0
    assert replace(a,f1=.1,f2=.1,f3=.8).nu_d==pytest.approx(.2)
    assert replace(a,f1=0.,f2=0.,f3=1.).equilibrium(.2,0.,.05,298.,0.)['d']==0
    with pytest.raises(Inadmissible,match='bicarbonate'):
        a.equilibrium(.2,.7,.05,298.,0.)
    with pytest.raises(ValueError):replace(a,f3=.9)


def test_w0_reduces_to_same_carrier_and_normalization():
    m=model();g=wet_gas(308.15,1.,0.)
    state=m.equilibrium(0.,g)
    assert state[:2]==pytest.approx(iast(g.p_C,g.p_N,g.T,m.co2,m.n2))
    assert state[2:].sum()==0
    assert normalize_capacity(2.,'mof','composite',pei_mass_fraction=.2)==pytest.approx(1.6)
    allpei=replace(m,pores=replace(m.pores,f_in=0.,alpha_in=0.),amines=replace(m.amines,lam=0.))
    assert allpei.equilibrium(1.,g)[0]==0


@pytest.mark.parametrize('tau',[0.,.1,1.,10.])
def test_periodic_residual_and_exact_chemical_solution(tau):
    m=model();ads=wet_gas(308.15,1.,40.);des=regeneration('R1')
    r=periodic_cycle(m,.2,ads,des,tau_over_t=tau)
    tighter=periodic_cycle(m,.2,ads,des,tau_over_t=tau,tolerance=1e-11)
    assert r['residual']<=1e-9
    assert r['q_work']==pytest.approx(tighter['q_work'],abs=1e-8)
    qa,qd=np.array(r['equilibrium_ads']),np.array(r['equilibrium_des'])
    retention=1-finite_fraction(tau)
    expected_ads=(qa[2]+retention*qd[2])/(1+retention)
    expected_des=(qd[2]+retention*qa[2])/(1+retention)
    assert r['ads'][2]==pytest.approx(expected_ads,abs=1e-8)
    assert r['des'][2]==pytest.approx(expected_des,abs=1e-8)
    assert r['des'][2]>0  # residual is carried, never reset to empty
    if tau==0:
        assert r['ads']==pytest.approx(qa)
        assert r['des']==pytest.approx(qd)
    assert heat(r,.2,ads.T,des.T)['status']=='unknown'
    assert selectivity([1.,0.,0.,0.,0.,0.],ads) is None


def test_retained_bicarbonate_rejects_instant_drying():
    m=model();m=replace(m,amines=replace(m.amines,h_max=.7,K_b=100.))
    des=Gas(383.15,1.,.001,.999,0.)
    with pytest.raises(Inadmissible,match='retained'):
        periodic_cycle(m,.2,wet_gas(308.15,1.,70.),des,tau_over_t=1.)


def test_B0_cancels_constant_and_B1_same_tau():
    m=model();base=replace(m,baseline=Baseline(23.,.2,50.,60000.),B0=True)
    ads,des=wet_gas(308.15,1.,40.),regeneration('R2')
    r=periodic_cycle(base,.2,ads,des)
    phys=.8*(iast(ads.p_C,ads.p_N,ads.T,m.co2,m.n2)[0]-iast(des.p_C,des.p_N,des.T,m.co2,m.n2)[0])
    assert r['q_work']==pytest.approx(phys)
    assert r['ads'][2]==r['des'][2]
    b1=periodic_cycle(replace(base,B0=False),.2,ads,des,tau_over_t=1.)
    assert b1['ads'][2]>b1['des'][2]
    assert heat(b1,.2,ads.T,des.T)['status']=='unknown'


def test_heat_units_and_negative_work_not_clipped():
    r=dict(ads=[1.,.1,1.,.2,2.,1.],des=[.2,.05,.1,.1,.5,.5],q_work=1.8,baseline_water_available=True)
    h=heat(r,.2,300.,350.,cp_mof=1.,cp_pei=2.,cp_water=4.,Q_phys=20000.,Q_d=60000.,Q_b=60000.,Q_water=40000.,Q_n2=10000.)
    assert h['desorption_J_g']==pytest.approx(.001*(.8*20000+.9*60000+.1*60000+2*40000+.05*10000))
    assert h['sensible_J_g'][0]==pytest.approx(60.)
    assert h['specific_J_g_co2'][0]==pytest.approx(h['heat_J_g'][0]/(.001*44.0095*1.8))
    assert heat(r|{'q_work':-1.},.2,300.,350.,cp_mof=1.,cp_pei=2.,cp_water=4.,Q_phys=20000.,Q_d=60000.,Q_b=60000.,Q_water=40000.,Q_n2=10000.)['specific_J_g_co2'] is None
    m=model();g1=wet_gas(298.,1.,0.,z_C=.001);g2=wet_gas(298.,1.,0.,z_C=.5)
    assert periodic_cycle(m,.2,g1,g2)['q_work']<0
