"""Synthetic producer/consumer contracts; no V inputs or git mutations."""
import copy
import csv
import importlib.util
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
import yaml

from pet2mof.calibration.final import calibrate, selected_c
from pet2mof.calibration.prediction import MODEL_LABELS, evaluate, derivatives as model_derivatives
from pet2mof.calibration.ensemble import run_ensemble, summarize

ROOT = Path(__file__).resolve().parents[1]


def script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT/f'scripts/{name}.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


@pytest.fixture
def synthetic(tmp_path):
    configs = tmp_path/'configs'; configs.mkdir()
    for name in ('scenarios.yaml', 'revision.yaml', 'sourced_ranges.yaml'):
        (configs/name).write_text((ROOT/'configs'/name).read_text())
    fits = []
    for version in ('v1', 'v1.1-mof', 'v1.1-connectivity'):
        for reading in ('composite', 'ratio'):
            fits.append(dict(model_version=version, interpretation=reading, n_N=23., T_fit=298.,
                host=dict(q_sat=9., b=.3), models={
                    'M1': {'parameters': dict(A0=.4, lam=1., K_d=60., kappa=.5, **({'power': 3.} if version == 'v1.1-connectivity' else {}))},
                    'B1': {'parameters': dict(eta0=.2, K_d=50.)}}))
    c = dict(carriers=[dict(material=m, gas=g, q_sat=10. if g == 'CO2' else 2., b=.25 if g == 'CO2' else .1,
                           Q=20000. if g == 'CO2' else None, T_ref=298.)
                       for m in ('UiO-66', 'UiO-66-NH2') for g in ('CO2', 'N2')],
             water=[dict(material=f'UiO-66_{d}', q_max=20., a_s=.3, m=4., T_ref=293., Q=None,
                         equivalent_volume_cm3_g=.4) for d in (100, 160, 220)])
    joint = []
    for j in range(8):
        rec = copy.deepcopy(dict(fits=fits, c_fits=c))
        for f in rec['fits']:
            f['host']['q_sat'] *= .9+.025*j
            f['models']['M1']['parameters']['A0'] *= .9+.025*j
        for r in rec['c_fits']['carriers']:
            r['q_sat'] *= .9+.025*j
        joint.append(rec)
    frozen = dict(include_provisional=False, missing=[], inputs=[], fits=fits, c_fits=c, joint_draws=joint,
                  uncertainty_method='synthetic correlated parameter ensemble')
    (configs/'frozen_parameters.yaml').write_text(yaml.safe_dump(frozen))
    module = script('predict_holdout')
    row = {k: '' for k in module.CONDITION_FIELDS}
    row.update(series='synthetic', point_id='p1', source_id='synthetic', extraction_id='synthetic',
               material='UiO-66-NH2', gas='CO2', observable='q_CO2', unit='mmol/g', basis='dry_sorbent',
               T_K='298', p_total_bar='1', p_partial_bar='1', RH_fraction='0', w_PEI='0')
    return tmp_path, frozen, row


def test_verified_selection_does_not_promote_candidates():
    f, omitted = selected_c(ROOT)
    assert set(f.status) == {'verified'}
    assert set(f[f.source_id == 'S100'].material) == {'UiO-66', '10PEI@UiO-66', '20PEI@UiO-66', '30PEI@UiO-66', '40PEI@UiO-66'}
    assert len(f[f.source_id == 'S100']) == 48
    assert not (f.gas == 'N2').any()
    assert any('160' in r['series_id'] for r in omitted)
    sensitivity, _ = selected_c(ROOT, True)
    assert set(sensitivity.status) == {'verified', 'provisional'}


def test_final_calibration_deterministic_and_missing_inputs_honest():
    a = calibrate(ROOT, draws=8)
    b = calibrate(ROOT, draws=8)
    assert a == b
    assert len(a['fits']) == 6 and len(a['joint_draws']) == 8
    assert set(a['missing']) == {'S105/UiO-66/N2', 'S105/UiO-66-NH2/N2', 'S106/UiO-66_160'}
    assert all(r['status'] == 'verified' for r in a['inputs'])
    assert all(len(r['input_sha256']) == 64 for r in a['inputs'])
    assert all(not f['models']['M1']['metrics']['all_protocol_criteria'] for f in a['fits'])
    assert all(c['Q'] is None for c in a['c_fits']['water'])


def test_synthetic_predictions_derivatives_no_response_reads(synthetic, monkeypatch):
    root, frozen, row = synthetic
    module = script('predict_holdout')
    folder = root/'synthetic'; folder.mkdir()
    with (folder/'conditions.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=module.CONDITION_FIELDS); writer.writeheader(); writer.writerow(row)
    opened = []
    original = Path.open
    def guarded(path, mode='r', *args, **kwargs):
        if 'r' in mode:
            opened.append(path.name)
            assert path.name in {'frozen_parameters.yaml', 'conditions.csv', 'predictions.csv', 'model_derivatives.csv'}
        return original(path, mode, *args, **kwargs)
    with monkeypatch.context() as m:
        m.setattr(Path, 'open', guarded)
        predictions, derivatives = module.predict(root, directory='synthetic', dry_run=True)
    assert len(predictions) == len(MODEL_LABELS) == 12
    assert set(opened) == {'frozen_parameters.yaml', 'conditions.csv', 'predictions.csv', 'model_derivatives.csv'}
    assert all(p['status'] == 'conditional_prediction' for p in predictions)
    assert predictions[0]['q_pred'] == pytest.approx(1.975)
    assert predictions[0]['prediction_low'] < predictions[0]['prediction_high']
    assert derivatives[0]['dq_dp'] == pytest.approx(1.58, rel=1e-7)
    assert derivatives[0]['dq_dT'] == pytest.approx(-9.875*.25/(1.25**2)*20000/(8.31446261815324*298**2), rel=1e-6)
    assert derivatives[0]['dq_da'] is None
    assert json.loads((folder/'prediction_metadata.json').read_text())['status'] == 'debug'
    row['p_partial_bar'] = '0'
    boundary = model_derivatives(row, dict(fits=frozen['fits'], c_fits=frozen['c_fits']), MODEL_LABELS[0], ensemble=frozen['joint_draws'])
    assert boundary['dq_dp'] == pytest.approx(2.46875, rel=1e-8)
    with pytest.raises(ValueError, match='synthetic'):
        module.predict(root, dry_run=True)


def test_missing_tag_and_wrong_head_refused_before_conditions(synthetic, monkeypatch):
    root, _, _ = synthetic
    module = script('predict_holdout')
    def absent(*a, **kw):
        raise subprocess.CalledProcessError(128, ['git'])
    monkeypatch.setattr(module.subprocess, 'run', absent)
    with pytest.raises(ValueError, match='prereg-v1'):
        module.predict(root)
    def different(command, **kw):
        return SimpleNamespace(stdout='head' if command[-1] == 'HEAD' else 'tag')
    monkeypatch.setattr(module.subprocess, 'run', different)
    with pytest.raises(ValueError, match='prereg-v1'):
        module.predict(root)


def test_D11_transfer_and_basis_once_and_unknown_wet(synthetic):
    _, frozen, row = synthetic
    row.update(source_id='S2', material='PEI@UiO-66-NH2', w_PEI='.2', w_reading='retained', Mw_PEI='600')
    point = dict(fits=frozen['fits'], c_fits=frozen['c_fits'])
    composite = evaluate(row, point, 'M1/v1.1-mof/composite')
    assert composite == pytest.approx(.7*2+.2*23*.5*.4*np.exp(-.25)*60/61)
    # NH2 S105 host (2), not S100 bare host (9*.3/1.3).
    row['basis'] = 'dry_MOF'
    assert evaluate(row, point, 'M1/v1.1-mof/composite') == pytest.approx(composite/.8)
    row['RH_fraction'] = ''
    with pytest.raises(ValueError, match='unknown RH'):
        evaluate(row, point, 'M1/v1/composite')
    row['RH_fraction'] = '.4'
    with pytest.raises(ValueError, match='wet operator'):
        evaluate(row, point, 'M1/v1/composite')


def test_ensemble_deterministic_seed_and_separate_branches(synthetic):
    root, _, _ = synthetic
    options = dict(count=8, repeats=2, debug=True, branch_limit=2, plots=False, seed=180180)
    a = run_ensemble(root, output='reports/a', **options)
    b = run_ensemble(root, output='reports/b', **options)
    assert a['branches'] == b['branches']
    assert len(a['branches']) == 2
    assert {k.split('/')[0] for k in a['branches']} == {'stress', 'analog'}
    c = run_ensemble(root, output='reports/c', **dict(options, seed=180181))
    assert a['branches'] != c['branches']
    for branch in a['branches'].values():
        assert branch['accepted'] == 16 and branch['rejected'] == 0
        assert branch['convergence']['status'] == 'not_established'
    for path in (root/'reports/a').rglob('samples.npz'):
        relative = path.relative_to(root/'reports/a')
        with np.load(path) as x, np.load(root/'reports/b'/relative) as y:
            assert x.files == y.files
            assert all(np.array_equal(x[k], y[k]) for k in x.files)
    assert len((root/'reports/a/SHA256SUMS.large').read_text().splitlines()) == 2


def test_validator_model_labels_and_sidecar_contract(synthetic, monkeypatch):
    root, _, row = synthetic
    module = script('validate')
    folder = root/'holdout/v1'; folder.mkdir(parents=True)
    obs = dict(series='synthetic', point_id='p1', source_id='synthetic', extraction_id='synthetic',
               q=2., u_exp=.1, u_dig=.01, u_p=0., u_T=0., u_a=0., dq_dp=None, dq_dT=None, dq_da=None,
               scale=3., observable='q_CO2', comparable=True, inputs_known=True)
    pd.DataFrame([obs]).to_csv(folder/'observations.csv', index=False)
    pd.DataFrame([dict(series='synthetic', point_id='p1', model=m, q_pred=2., u_num=1e-12,
                       prediction_low=1.9, prediction_high=2.1) for m in MODEL_LABELS]).to_csv(folder/'predictions.csv', index=False)
    pd.DataFrame([dict(series='synthetic', point_id='p1', model=m, dq_dp=1.6, dq_dT=None, dq_da=None,
                       u_num=1e-12) for m in MODEL_LABELS]).to_csv(folder/'model_derivatives.csv', index=False)
    (folder/'prediction_metadata.json').write_text(json.dumps(dict(status='frozen_prediction', commit_sha='synthetic-head')))
    from pet2mof.calibration.final import sha256
    freeze = dict(commit_sha='synthetic-head', reviewer='synthetic', predictions_precede_disclosure=True)
    freeze.update({p.name+'_sha256': sha256(p) for p in folder.iterdir()})
    (folder/'freeze.json').write_text(json.dumps(freeze))
    monkeypatch.setattr(module.subprocess, 'run', lambda *a, **kw: SimpleNamespace(stdout='synthetic-head'))
    report = module.validate(root, output='reports/validation.json')
    assert len(report['series']) == 12 and {s['model'] for s in report['series']} == set(MODEL_LABELS)
    assert all(s['status'] != 'not_testable' for s in report['series'])
    # An unknown temperature slope with nonzero input uncertainty must fail closed.
    obs['u_T'] = .1
    pd.DataFrame([obs]).to_csv(folder/'observations.csv', index=False)
    freeze['observations.csv_sha256'] = sha256(folder/'observations.csv')
    (folder/'freeze.json').write_text(json.dumps(freeze))
    report = module.validate(root, output='reports/validation.json')
    assert all(s['status'] == 'not_testable' for s in report['series'])
