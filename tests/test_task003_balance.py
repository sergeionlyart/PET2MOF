"""Scientific invariants and numerical checks for the TASK-003 balance."""
import math

import numpy as np
import pytest

from pet2mof.task003 import balance as b
from pet2mof.task003.interpolation import interpolate, coordinate_corner_envelope


def test_units_and_s2_composition():
    c = b.s2_composition(.64,.194,'s-I')
    assert c.h == pytest.approx(1/1.64)
    assert sum((c.h,c.w,c.s)) == pytest.approx(1,abs=1e-12)
    assert b.N_NOMINAL_MMOL_G_PEI == pytest.approx(.3074*1000/14.007)
    assert b.capacity_mmol_g(c,0,2.67,b.N_NOMINAL_MMOL_G_PEI,.5) == pytest.approx(c.w*21.94616977225673*.5)
    volatile = b.s2_composition(.64,.194,'s-V')
    assert volatile.s == 0
    assert volatile.w/volatile.h == pytest.approx(c.w/c.h)
    assert volatile.h+volatile.w == pytest.approx(1,abs=1e-12)


@pytest.mark.parametrize('values',[(.7,.3,.01),(-.1,.5,.6),(float('nan'),.5,.5),(1.1,0.,0.)])
def test_invalid_mass_fractions(values):
    with pytest.raises(ValueError): b.Composition(*values)


@pytest.mark.parametrize('phi,n', [(-.1,22),(1.1,22),(.5,0),(.5,-1),(.5,math.inf)])
def test_invalid_phi_or_nitrogen(phi,n):
    with pytest.raises(ValueError): b.eta_min(b.Composition(.8,.2),phi,2.67,n,2.67)


def test_invalid_s2_original_not_hidden_by_volatile_branch():
    with pytest.raises(ValueError): b.s2_composition(.1,.5,'s-V')


def test_s100_loading_and_mass_bases():
    c=b.s100_composition(30,'w-C')
    f=b.s100_composition(30,'w-F')
    assert c.w==.3
    assert f.w==pytest.approx(30/130)
    assert b.s100_q_composite(3,c,'b-C')==3
    assert b.s100_q_composite(3,c,'b-M')==pytest.approx(2.1)
    with pytest.raises(ValueError): b.s100_composition(30,'unknown')


def test_no_pei_and_full_blocking():
    c=b.Composition(.8,0,.2)
    assert b.eta_min(c,1,2.67,22,2.67) is None
    assert b.capacity_mmol_g(c,1,2.67,22,.5)==pytest.approx(.8*2.67)
    c=b.Composition(.7,.2,.1)
    assert b.eta_min(c,0,2.67,22,1.1*2.67)==pytest.approx(1.1*2.67/(.2*22))
    assert b.capacity_mmol_g(c,0,2.67,22,0)==0


def test_host_nitrogen_subtracted_once():
    W,N,N0=.64,.09,.05
    w=b.s2_pei_mass_fraction(W,N,N0)
    h=1/(1+W)
    assert w==pytest.approx((N-h*N0)/.3074)
    assert h*N0+w*.3074==pytest.approx(N)
    assert w < N/.3074
    # No PEI when measured nitrogen is only diluted MOF nitrogen.
    assert b.s2_pei_mass_fraction(W,h*N0,N0)==pytest.approx(0,abs=1e-16)


def test_linker_and_pet_units():
    c=b.Composition(1,0)
    inv=b.linker_inventory(c,0)
    assert inv['pet_theoretical_g_kg_composite']/inv['bdc_acid_equivalent_g_kg_composite']==pytest.approx(192.17/166.13)
    assert inv['nitrogen_linker_mmol_g_composite']==0
    mix=b.linker_inventory(c,.54)
    assert mix['pet_linker_mole_fraction']==pytest.approx(.46)
    assert mix['nitrogen_linker_mmol_g_composite']==pytest.approx(mix['linker_mol_kg_composite']*.54)
    assert mix['pet_fragment_mass_fraction']==pytest.approx(mix['linker_mol_kg_composite']*.46*164.116/1000)
    assert b.linker_inventory(c,1)['pet_fragment_mass_fraction']==0
    # Positive caps lower the skeleton estimate, not the other way round.
    assert b.linker_inventory(c,.54,4.64,100)['pet_fragment_mass_fraction'] < b.linker_inventory(c,.54,4.64)['pet_fragment_mass_fraction']


def test_p302_class_boundaries():
    assert [b.classify_eta(v) for v in (-.1,0,.2,.3747,.4,.5,.500001)]==['A','A','B','B','C','C','D']
    assert b.classify_eta(.2,.195)=='D'
    assert b.classify_eta(.195,.195)=='B'


@pytest.mark.parametrize('q,expected',[(3.26,'admissible'),(10.,'entirely_above_ceiling')])
def test_line_intersection(q,expected):
    c=b.s2_composition(.64,.194,'s-I')
    iv=b.analog_interval(c,q,2.67,b.N_NOMINAL_MMOL_G_PEI)
    assert iv.status==expected
    if iv.phi_low is not None:
        assert b.eta_min(c,iv.phi_low,2.67,b.N_NOMINAL_MMOL_G_PEI,q)==pytest.approx(.5,abs=1e-12)
        assert 0<=iv.phi_low<=iv.phi_high<=1


def test_grid_boundary_matches_closed_form():
    checked=0
    for w in np.arange(1,51)/100:
        for s in (0.,1-1/1.64-.194):
            c=b.Composition(1-w-s,w,s)
            for q0 in (2.67,1.9015205857417268):
                for g in (1.,1.1):
                    for eta in (.195,.3747,.5):
                        root=b.phi_crit(c,g,q0,b.N_NOMINAL_MMOL_G_PEI,eta)
                        if not 0<=root<=1: continue
                        lo=math.floor(root*100)/100
                        hi=min(1.,lo+.01)
                        f_lo=b.eta_min(c,lo,q0,b.N_NOMINAL_MMOL_G_PEI,g*q0)
                        f_hi=b.eta_min(c,hi,q0,b.N_NOMINAL_MMOL_G_PEI,g*q0)
                        interpolated=lo+(eta-f_lo)*(hi-lo)/(f_hi-f_lo)
                        assert abs(interpolated-root)<1e-9
                        checked+=1
    assert checked>500


def bisect_threshold(c,gain,g,phis):
    def residual(k): return min(b.gain_pet(c,p,k,gain) for p in phis)-g
    lo,hi=1e-8,16.
    assert residual(lo)>=0 and residual(hi)<0
    for _ in range(80):
        mid=(lo+hi)/2
        if residual(mid)>=0: lo=mid
        else: hi=mid
    return (lo+hi)/2


@pytest.mark.parametrize('gain,g',[(1.22,1.),(1.22,1.1),(.95,1.),(1.05,1.1)])
def test_kstar_closed_form_against_bisection(gain,g):
    c=b.Composition(.65,.25,.1)
    numerical=bisect_threshold(c,gain,g,np.linspace(0,1,101))
    assert b.kstar_all(c,gain,g)==pytest.approx(numerical,abs=1e-12)
    if gain>=g: assert numerical==pytest.approx(gain/g)
    else: assert numerical<gain/g  # G/g is not an all-phi guarantee below k=1.
    iv=b.LineInterval(.3,.9,.5,.1,'admissible')
    assert b.kstar_admissible(c,gain,g,iv)==pytest.approx(bisect_threshold(c,gain,g,np.linspace(.3,.9,101)),abs=1e-12)


def test_transfer_identity_and_degenerate_control():
    c=b.Composition(.75,.25)
    for phi in (0.,.4,1.):
        assert b.gain_pet(c,phi,1,1.2)==pytest.approx(1.2)
        assert b.k_crit(c,phi,1.2,1.1)==pytest.approx((1.2-c.h*phi)/(1.1-c.h*phi))
    assert b.kstar_all(b.Composition(1,0),1,1)==1
    assert math.isinf(b.k_crit(b.Composition(1,0),1,1,1))


def test_interpolation_no_extrapolation_and_endpoint_uncertainty():
    assert interpolate([.1,.5,1.],[1.,2.,3.],.75)==2.5
    with pytest.raises(ValueError): interpolate([.1,.5],[1.,2.],.6)
    # Last point can lie exactly at target; this is an added support boundary vertex.
    env=coordinate_corner_envelope([.1,.8,1.],[.1,2.,3.],.99,.04,.1)
    assert env['unsupported_vertices']>0
    assert not env['full_envelope_known']
    assert env['support_boundary_vertices']>0
    assert env['q_high_supported_mmol_g']==pytest.approx(3.1)
