"""D-18, IAPWS and C/V contracts, using synthetic responses exclusively."""
import copy
import csv
import json

import numpy as np
import pandas as pd
import pytest

from test_freeze_prep import synthetic, script
from pet2mof.calibration.final import sha256
from pet2mof.calibration.prediction import MODEL_LABELS, evaluate, applicability
from pet2mof.calibration.revision import covariance_csv, complete_metrics
from pet2mof.model.gas import p_sat
from pet2mof.model.revision import dry_prediction
from pet2mof.calibration.ensemble import run_ensemble


def comparison(synthetic, monkeypatch, *, condition=None, observation=None, q=None):
    root, frozen, row = synthetic
    row.update(condition or {})
    # Explicit C temperatures are frozen from C rows, not guessed from V.
    for sample in [frozen, *frozen['joint_draws']]:
        for c in sample['c_fits']['carriers']:
            c['calibration_temperatures_K'] = [273., 298., 318.] if c['gas'] == 'CO2' else [298.]
    import yaml
    (root/'configs/frozen_parameters.yaml').write_text(yaml.safe_dump(frozen))
    folder = root/'holdout/v1'; folder.mkdir(parents=True)
    producer = script('predict_holdout')
    with (folder/'conditions.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=producer.CONDITION_FIELDS)
        writer.writeheader(); writer.writerow(row)
    monkeypatch.setattr(producer, 'require_freeze', lambda _: 'synthetic-head')
    predictions, derivs = producer.predict(root)
    obs = dict(series=row['series'], point_id=row['point_id'], source_id='synthetic', extraction_id='synthetic',
               q=predictions[0]['q_pred'] if q is None else q, u_exp=.1, u_dig=.01, u_p=.001,
               u_T=.1, u_a=None, dq_dp=None, dq_dT=None, dq_da=None,
               scale=3., observable=row['observable'], comparable=True, inputs_known=True)
    obs.update(observation or {})
    pd.DataFrame([obs]).to_csv(folder/'observations.csv', index=False)
    freeze = dict(commit_sha='synthetic-head', reviewer='synthetic', predictions_precede_disclosure=True)
    freeze.update({p.name+'_sha256': sha256(p) for p in folder.iterdir()})
    (folder/'freeze.json').write_text(json.dumps(freeze))
    consumer = script('validate')
    monkeypatch.setattr(consumer, 'require_freeze', lambda _: 'synthetic-head')
    result = consumer.validate(root)
    return result, predictions, derivs


def test_dry_activity_exact_zero_does_not_require_humidity_slope(synthetic, monkeypatch):
    report, _, side = comparison(synthetic, monkeypatch)
    assert side[0]['dq_da'] is None and side[0]['dry_series'] is True
    assert len(report['comparison_groups']['full']) == 12
    assert not report['comparison_groups']['conditional']
    assert report['full_verdict_available']
    r = report['series'][0]
    assert r['status'] == 'pass' and r['dry_activity_points'] == ['p1']


@pytest.mark.parametrize('T', [297., 298., 299.])
def test_unknown_temperature_error_at_matching_C_temperature(synthetic, monkeypatch, T):
    report, _, _ = comparison(synthetic, monkeypatch, condition={'T_K': str(T)}, observation={'u_T': None})
    assert len(report['comparison_groups']['conditional']) == 12
    assert not report['comparison_groups']['full'] and not report['full_verdict_available']
    for r in report['series']:
        assert r['status'] == 'conditional_comparison'
        assert r['conditional_reasons'] == ['T-uncertainty excluded']
        assert r['excluded_T_points'] == ['p1']
        assert r['within_conditional_tolerances']


@pytest.mark.parametrize('condition', [
    {'gas': 'N2', 'observable': 'q_N2', 'T_K': '308'},
    {'material': 'PEI@UiO-66-NH2', 'w_PEI': '.2', 'w_reading': 'retained', 'Mw_PEI': '600', 'T_K': '308'},
])
def test_single_temperature_component_transfer_refused(synthetic, monkeypatch, condition):
    report, pred, _ = comparison(synthetic, monkeypatch, condition=condition, q=1.)
    assert all(p['status'] == 'not_testable' and 'temperature coefficient unknown' in p['reason'] for p in pred)
    assert all(r['status'] == 'not_testable' and r['prediction_reasons'] for r in report['series'])


def test_unknown_uT_between_C_temperatures_is_not_excluded(synthetic, monkeypatch):
    report, pred, _ = comparison(synthetic, monkeypatch, condition={'T_K': '308'}, observation={'u_T': None})
    assert pred[0]['q_pred'] is not None  # CO2 has calibrated Q, prediction exists.
    assert all(r['status'] == 'not_testable' for r in report['series'])


def test_single_temperature_known_nonzero_error_still_requires_slope(synthetic, monkeypatch):
    report, _, _ = comparison(synthetic, monkeypatch, condition={'gas': 'N2', 'observable': 'q_N2'})
    assert all(r['status'] == 'not_testable' for r in report['series'])


def test_single_temperature_unknown_error_can_be_excluded(synthetic, monkeypatch):
    report, _, _ = comparison(synthetic, monkeypatch, condition={'gas': 'N2', 'observable': 'q_N2'}, observation={'u_T': None})
    assert all(r['status'] == 'conditional_comparison' for r in report['series'])


def test_unknown_exp_uses_separate_three_percent_scenario(synthetic, monkeypatch):
    report, _, side = comparison(synthetic, monkeypatch, observation={'u_exp': None, 'u_T': 0.})
    r = report['series'][0]
    assert r['status'] == 'conditional_comparison'
    assert r['conditional_reasons'] == ['experimental uncertainty unknown; 3% source-scale scenario']
    u = np.sqrt((.03*3/np.sqrt(3))**2+.01**2+(side[0]['dq_dp']*.001)**2)
    assert r['mean_U'] == pytest.approx(1.96*np.hypot(u,side[0]['u_num']))


def test_conditional_failure_stays_conditional_and_lists_both_reasons(synthetic, monkeypatch):
    report, _, _ = comparison(synthetic, monkeypatch, observation={'u_exp': None, 'u_T': None}, q=20.)
    r = report['series'][0]
    assert r['status'] == 'conditional_comparison' and not r['within_conditional_tolerances']
    assert len(r['conditional_reasons']) == 2


def test_unknown_exp_without_scale_is_not_testable(synthetic, monkeypatch):
    report, _, _ = comparison(synthetic, monkeypatch, observation={'u_exp': None, 'scale': None})
    assert all(r['status'] == 'not_testable' for r in report['series'])


@pytest.mark.parametrize('rh', ['', '.4'])
def test_unknown_or_wet_conditions_do_not_get_dry_exemption(synthetic, monkeypatch, rh):
    report, _, side = comparison(synthetic, monkeypatch, condition={'RH_fraction': rh}, q=1.)
    assert all(r['status'] == 'not_testable' for r in report['series'])
    assert all(not d['dry_series'] for d in side)


@pytest.mark.parametrize('model', ['M1', 'B1'])
@pytest.mark.parametrize('reading', ['composite', 'ratio'])
def test_conditions_predictions_D11_and_MOF_operator_once(synthetic, monkeypatch, model, reading):
    report, pred, _ = comparison(synthetic, monkeypatch, condition=dict(
        source_id='S2', material='PEI@UiO-66-NH2', w_PEI='.2', w_reading='retained', Mw_PEI='600', basis='dry_MOF'),
        observation={'u_T': None})
    _, frozen, row = synthetic
    label = f'{model}/v1.1-mof/{reading}'
    # Same parameters as C calibration, with the D-11 S105 NH2 carrier substituted
    # once. dry_prediction is C's observation operator (already per dry MOF).
    values = []
    for sample in frozen['joint_draws']:
        f = next(f for f in sample['fits'] if f['model_version'] == 'v1.1-mof' and f['interpretation'] == reading)
        c = next(c for c in sample['c_fits']['carriers'] if c['material'] == 'UiO-66-NH2' and c['gas'] == 'CO2')
        host = c['q_sat']*c['b']/(1+c['b'])
        m = f['models'][model]['parameters']
        columns = ['eta0', 'K_d'] if model == 'B1' else ['A0', 'lam', 'K_d', 'kappa']
        values.append(float(dry_prediction(1., .2, host, f['n_N'], [m[k] for k in columns], 'v1.1-mof', model == 'B1')))
        # Altering S100 bare host cannot change the D-11 carrier a second time.
        before = evaluate(row, sample, label)
        altered = copy.deepcopy(sample)
        for f2 in altered['fits']:
            f2['host'] = dict(q_sat=900., b=100.)
        assert evaluate(row, altered, label) == before
    prediction = next(p for p in pred if p['model'] == label)
    assert prediction['q_pred'] == pytest.approx(np.median(values), rel=1e-13)
    assert prediction['q_pred'] != pytest.approx(np.median(values)/.8)  # double normalization would fail


def test_C_and_V_U_share_same_marginal_definition(synthetic, monkeypatch):
    report, _, side = comparison(synthetic, monkeypatch, observation=dict(
        u_exp=0., u_dig=.06/np.sqrt(3), u_p=.02/np.sqrt(3), u_T=0.))
    slope = side[0]['dq_dp']
    f = pd.DataFrame(dict(series_id=['synthetic']*3, p_bar=[0., 1., 2.],
                          q_mmol_g=[1., 1.+slope, 1.+2*slope], q_err_mmol_g=[.06]*3, p_err_bar=[.02]*3))
    C = covariance_csv(f, .5)
    marginal = (.06**2+(slope*.02)**2)/3
    assert np.diag(C) == pytest.approx([marginal]*3)
    assert C[0,1] == pytest.approx(.5*marginal)
    c_report = complete_metrics(f, f.q_mmol_g, C)
    assert report['series'][0]['mean_U'] == pytest.approx(c_report['mean_U'], rel=1e-12)
    # Sharing allocates existing variance; it never adds a second extraction floor.
    assert covariance_csv(f, 0.).diagonal() == pytest.approx(C.diagonal())


@pytest.mark.parametrize('T,pa,tolerance', [(273.16,611.657,.0005), (373.1243,101325.,.5), (647.096,22064000.,.5)])
def test_iapws_table1_pressure(T, pa, tolerance):
    # extraction_id T020-IAPWS-SR1-86; Table 1 p/Pa, printed rounding.
    assert p_sat(T)*1e5 == pytest.approx(pa, abs=tolerance, rel=0)


@pytest.mark.parametrize('T,pa_K,tolerance', [(273.16,44.436693,.000005), (373.1243,3616.,.5), (647.096,268000.,500.)])
def test_iapws_table1_pressure_derivative(T, pa_K, tolerance):
    h = .001
    if T == 273.16:
        slope = (-3*p_sat(T)+4*p_sat(T+h)-p_sat(T+2*h))/(2*h)
    elif T == 647.096:
        slope = (3*p_sat(T)-4*p_sat(T-h)+p_sat(T-2*h))/(2*h)
    else:
        slope = (p_sat(T+h)-p_sat(T-h))/(2*h)
    assert slope*1e5 == pytest.approx(pa_K, abs=tolerance, rel=0)


def test_iapws_independent_T011_reference():
    assert p_sat(293.) == pytest.approx(.02317544979505042, rel=2e-14)


@pytest.mark.parametrize('options', [dict(count=8192), dict(count=4096, repeats=8), dict(count=4096, seed=12002)])
def test_D18_production_sample_size_fixed(synthetic, options):
    root, _, _ = synthetic
    with pytest.raises(ValueError, match='exactly 4096'):
        run_ensemble(root, **options)
