"""Current Vp operator: S2 condition shape, synthetic model parameters only."""
import math

import pytest

from pet2mof.calibration.prediction import MODEL_LABELS, evaluate


@pytest.fixture
def row():
    # Shape specified in T032 for S2-Table1-Vp-ratio; not a measured response.
    return dict(source_id='S2', material='PEI@UiO-66-NH2', gas='N2', T_K='77',
                RH_fraction='', p_partial_bar='', observable='Vp_ratio_to_w0',
                unit='1', basis='dry_sorbent', w_PEI='.2', w_reading='retained',
                Mw_PEI='600')


@pytest.fixture
def sample():
    # Deliberately no c_fits, T_fit or adsorption parameters: Vp needs none.
    return {'fits': [dict(model_version=version, interpretation=reading, models={
        'B1': {'parameters': {}},
        'M1': {'parameters': {'kappa': .5, 'power': 3.}},
    }) for version in ('v1', 'v1.1-mof', 'v1.1-connectivity')
        for reading in ('composite', 'ratio')]}


def expected(label, basis, w):
    model, version, _ = label.split('/')
    if model == 'B1':
        scale = 1-w
    elif version == 'v1.1-connectivity':
        scale = (1-w)*math.exp(-(.5*w/(1-w))**3)
    else:
        scale = 1-w-.5*w
    return scale/(1-w) if basis == 'dry_MOF' else scale


@pytest.mark.parametrize('label', MODEL_LABELS)
@pytest.mark.parametrize('basis', ['dry_sorbent', 'dry_MOF'])
def test_s2_porosimetry_formula_without_adsorption_inputs(row, sample, label, basis):
    row['basis'] = basis
    assert evaluate(row, sample, label) == pytest.approx(expected(label, basis, .2))


@pytest.mark.parametrize('label', MODEL_LABELS)
@pytest.mark.parametrize('basis', ['dry_sorbent', 'dry_MOF'])
def test_label_loading_interpretation(row, sample, label, basis):
    row.update(source_id='synthetic', w_reading='label', basis=basis)
    w = .2/1.2 if label.endswith('/ratio') else .2
    assert evaluate(row, sample, label) == pytest.approx(expected(label, basis, w))


@pytest.mark.parametrize('temperature', [None, '', ' ', 77., 298., 400.])
def test_temperature_optional_and_no_co2_gas_required(row, sample, temperature):
    row['T_K'] = temperature
    row.pop('RH_fraction')
    row.pop('p_partial_bar')
    row['gas'] = 'N2'
    assert evaluate(row, sample, 'M1/v1/composite') == pytest.approx(.7)
    row.pop('T_K')
    assert evaluate(row, sample, 'M1/v1/composite') == pytest.approx(.7)


@pytest.mark.parametrize('temperature', [0, -1, 'nan', 'inf', '-inf', 'invalid'])
def test_invalid_supplied_temperature_refused(row, sample, temperature):
    row['T_K'] = temperature
    with pytest.raises(ValueError):
        evaluate(row, sample, 'M1/v1/composite')


@pytest.mark.parametrize('changes,reason', [
    ({'material': 'unknown'}, 'unsupported material'),
    ({'basis': 'unknown'}, 'unknown mass basis'),
    ({'unit': 'mmol/g'}, 'observable unit mismatch'),
    ({'w_PEI': '-.1'}, 'invalid PEI fraction/material'),
    ({'w_PEI': '1'}, 'invalid PEI fraction/material'),
    ({'w_PEI': '1.1'}, 'invalid PEI fraction/material'),
    ({'w_PEI': ''}, 'unknown w_PEI'),
    ({'w_PEI': 'nan'}, 'nonfinite w_PEI'),
    ({'material': 'UiO-66-NH2'}, 'invalid PEI fraction/material'),
    ({'material': 'UiO-66'}, 'invalid PEI fraction/material'),
    ({'w_reading': ''}, 'unknown loading reading'),
    ({'w_reading': 'unknown'}, 'unknown loading reading'),
    ({'w_reading': 'label'}, 'D-11 requires retained loading and Mw=600'),
    ({'Mw_PEI': '601'}, 'D-11 requires retained loading and Mw=600'),
    ({'Mw_PEI': ''}, 'unknown Mw_PEI'),
    ({'w_PEI': '.8'}, 'loading outside feasible dry-pore domain'),
])
def test_normalization_and_d11_refusals(row, sample, changes, reason):
    row.update(changes)
    with pytest.raises(ValueError, match=reason):
        evaluate(row, sample, 'M1/v1/composite')


@pytest.mark.parametrize('material', ['UiO-66', 'UiO-66-NH2', 'PEI@UiO-66-NH2'])
@pytest.mark.parametrize('label', MODEL_LABELS)
def test_zero_loading_reference(row, sample, material, label):
    row.update(material=material, w_PEI='0')
    assert evaluate(row, sample, label) == 1.


def test_zero_scale_allowed(row, sample):
    # kappa=1 and w=.5 give exactly zero accessible pore volume.
    row['w_PEI'] = '.5'
    sample['fits'][0]['models']['M1']['parameters']['kappa'] = 1.
    assert evaluate(row, sample, 'M1/v1/composite') == 0.


@pytest.mark.parametrize('observable', ['q_CO2', 'q_CO2_ratio_to_w0'])
@pytest.mark.parametrize('missing', ['RH_fraction', 'p_partial_bar'])
@pytest.mark.parametrize('label', MODEL_LABELS)
def test_co2_still_requires_humidity_and_pressure(row, sample, observable, missing, label):
    row.update(observable=observable, gas='CO2', T_K='298',
               unit='mmol/g' if observable == 'q_CO2' else '1',
               RH_fraction='0', p_partial_bar='1')
    row.pop(missing)
    for fit in sample['fits']:
        fit['T_fit'] = 298.
    sample['c_fits'] = {'carriers': [dict(material='UiO-66-NH2', gas='CO2',
                                       Q=None, T_ref=298.)]}
    with pytest.raises(ValueError, match='unknown '+missing):
        evaluate(row, sample, label)
