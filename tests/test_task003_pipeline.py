"""Input-to-output contract checks, without independent-review artifacts."""
import importlib.util
from pathlib import Path

import pytest

from pet2mof.task003 import balance as b

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('task003_pipeline',ROOT/'scripts/task003/run_balance.py')
pipeline=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pipeline)


@pytest.fixture(scope='module')
def inputs(): return pipeline.records()


def test_input_branch_coverage_and_common_pressure(inputs):
    recs,envelopes=inputs
    assert len(recs)==32
    assert len(envelopes)==5
    assert {r['p_bar'] for r in envelopes}=={.896}
    assert next(r['q0'] for r in recs if r['series']=='S100')==pytest.approx(1.9015205857417268)
    assert {r['branch'] for r in recs}=={'s-I','s-V','w-C','w-F'}
    pipeline.check_bounds()


def test_author_formula_and_rounding(inputs):
    rows=pipeline.s2_formula_rows(inputs[0],'unit-test')
    assert len(rows)==6
    assert all(r['table_interval_intersects_reconstruction'] for r in rows)
    c96=next(r for r in rows if r['sample_id']=='S2-C96')
    from fractions import Fraction
    expected=(Fraction(95,1000)-Fraction(5,100)/Fraction(19,10))/Fraction(3074,10000)
    assert c96['pei_reconstructed_mass_fraction']==pytest.approx(float(expected),abs=1e-14)
    assert abs(c96['delta_percentage_points'])<.06
    assert round(c96['pei_reconstructed_mass_fraction']*100,1)==22.3


def test_material_scenarios_and_ga_flags(inputs):
    rows=list(pipeline.material_rows(inputs[0],'unit-test','S2 recipe'))
    assert len(rows)==264
    actual=[r for r in rows if r['route']=='analog']
    assert len(actual)==22
    assert all(r['pet_fragment_mass_fraction']==0 for r in actual)
    assert all(abs(r['fraction_sum']-1)<1e-12 for r in rows)
    invalid={r['sample_id'] for r in actual if r['sI_ga_check_applies'] and not r['sI_ga_feed_consistent']}
    assert invalid=={'S2-C96','S2-I96'}
    r1=next(r for r in rows if r['sample_id']=='S2-C72' and r['structure_scenario']=='PET-UiO-66_ideal')
    assert r1['pet_linker_mole_fraction']==1
    assert r1['src06_mof_conversion']==.78
    assert r1['pet_src06_scenario_low_g_kg_composite']>=r1['pet_theoretical_g_kg_composite']
    r2=next(r for r in rows if r['structure_scenario']=='PET-UiO-66-NH2-50%_ideal')
    assert r2['nh2_linker_mole_fraction']==.54
    assert r2['pet_linker_mole_fraction']==pytest.approx(.46)
    assert not any(r['pei_feed_g_kg_composite'] is not None for r in actual if r['series']=='S100')


def test_full_grid_contract_and_pet_unknown(inputs):
    count=0
    for r in pipeline.design_rows(inputs[0],'unit-test'):
        count+=1
        assert abs(r['h']+r['w']+r['s']-1)<1e-12
        assert r['extraction_id']
        if r['q_host_origin']=='unknown_PET':
            assert r['q_host_mmol_g_mof'] is None
            assert r['eta_min_mol_co2_mol_n'] is None
            assert r['phi_crit_lit'] is None
            assert r['absolute_missing_reason']
        elif r['w']:
            assert r['eta_min_normalized']==pytest.approx(r['eta_min_mol_co2_mol_n']*r['n_n_mmol_g_pei']/r['q_host_mmol_g_mof'])
    assert count==61812


def test_transfer_points_are_on_admissible_lines(inputs):
    recs=inputs[0]
    rr,ss=pipeline.transfer_rows(recs,'unit-test')
    lookup={(r['sample'],r['branch'],r['basis']):r for r in recs}
    assert len(ss)==128
    for row in rr:
        assert row['extraction_id']
        if row['phi'] is None: continue
        r=lookup[row['sample_id'],row['composition_branch'],row['mass_basis_branch']]
        eta=row['eta_mol_co2_mol_n']
        if eta is not None:
            assert -1e-12<=eta<=row['eta_ceiling']+1e-12
            assert b.capacity_mmol_g(r['c'],row['phi'],r['q0'],b.N_NOMINAL_MMOL_G_PEI,max(0,eta))==pytest.approx(r['q'])
        assert row['gain_pet_k08']>=0


def test_uncertainty_contains_separate_systematic_and_individual(inputs):
    rows=pipeline.uncertainty_rows(*inputs,'unit-test')
    families={r['family'] for r in rows}
    assert 'systematic_discrete_branches' in families
    assert 'coupled_N_balance_and_nN' in families
    assert 'individual_table_rounding' in families
    assert any(f.startswith('one_factor:') for f in families)
    assert all(r['low'] is None or r['low']<=r['high'] for r in rows)
