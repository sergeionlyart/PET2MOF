"""T021 regressions: synthetic packages only; git tags only in temporary clones."""
import json
from pathlib import Path
import subprocess
import tempfile

import numpy as np
import pandas as pd
import pytest

from test_freeze_prep import ROOT, script, synthetic
from test_prereg_rules import comparison
from pet2mof.calibration.ensemble import parameter_draws, run_ensemble
from pet2mof.calibration.final import sha256
from pet2mof.calibration.revision_screening import draws, gas_arrays, nominal_controls
from pet2mof.model.config import load_config


@pytest.fixture
def frozen_clone():
    cache = ROOT/'.uv-cache'; cache.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='T022-guard-', dir=cache) as temporary:
        clone = Path(temporary)/'clone'
        subprocess.run(['git', 'clone', '--quiet', '--no-local', '--single-branch', '--no-tags',
                        str(ROOT), str(clone)], check=True, capture_output=True)
        subprocess.run(['git', 'tag', 'prereg-v1'], cwd=clone, check=True)
        yield clone


@pytest.mark.parametrize('change', ['unstaged', 'staged', 'untracked'])
def test_validation_freeze_guard_precedes_any_holdout_read(frozen_clone, monkeypatch, change):
    root = frozen_clone
    validator = script('validate')
    # Baseline actually passes the real shared git guard.
    validator.require_freeze(root)
    folder = root/'holdout/v1'; folder.mkdir(parents=True)
    for name in ('observations.csv', 'conditions.csv', 'predictions.csv',
                 'model_derivatives.csv', 'prediction_metadata.json', 'freeze.json'):
        (folder/name).write_text('must not be read')
    scientific = root/'src/pet2mof/calibration/metrics.py'
    if change == 'untracked':
        scientific = root/'configs/unregistered.yaml'
    scientific.write_text(scientific.read_text()+'\n# synthetic mutation\n' if scientific.exists() else 'synthetic: true\n')
    if change == 'staged':
        subprocess.run(['git', 'add', 'src/pet2mof/calibration/metrics.py'], cwd=root, check=True)
    def forbidden(*a, **kw):
        pytest.fail('holdout files must not be opened after scientific mutation')
    monkeypatch.setattr(Path, 'open', forbidden)
    with pytest.raises(ValueError, match='changed after freeze|not frozen'):
        validator.validate(root)


def validate_package(root, monkeypatch):
    validator = script('validate')
    monkeypatch.setattr(validator, 'require_freeze', lambda _: 'synthetic-head')
    return validator.validate(root)


def refresh_freeze(folder):
    """Re-sign outer manifest so tests isolate the inner producer contract."""
    path = folder/'freeze.json'
    freeze = json.loads(path.read_text())
    for file in folder.iterdir():
        if file.name != 'freeze.json':
            freeze[file.name+'_sha256'] = sha256(file)
    path.write_text(json.dumps(freeze))


def forbid_observation_parse(monkeypatch):
    original = pd.read_csv
    def guarded(path, *a, **kw):
        assert Path(path).name != 'observations.csv', 'invalid package reached observation parser'
        return original(path, *a, **kw)
    monkeypatch.setattr(pd, 'read_csv', guarded)


@pytest.mark.parametrize('missing', ['predictions.csv', 'model_derivatives.csv', 'prediction_metadata.json'])
def test_incomplete_package_refused(synthetic, monkeypatch, missing):
    comparison(synthetic, monkeypatch)
    root, _, _ = synthetic
    (root/'holdout/v1'/missing).unlink()
    forbid_observation_parse(monkeypatch)
    with pytest.raises(FileNotFoundError, match='complete prediction package'):
        validate_package(root, monkeypatch)


@pytest.mark.parametrize('kind', ['rows_debug', 'rows_missing_status', 'metadata_debug'])
def test_debug_or_unmarked_predictions_refused(synthetic, monkeypatch, kind):
    comparison(synthetic, monkeypatch)
    root, _, _ = synthetic
    folder = root/'holdout/v1'
    path = folder/'prediction_metadata.json'
    metadata = json.loads(path.read_text())
    if kind == 'metadata_debug':
        metadata['status'] = 'debug'
    else:
        pred = pd.read_csv(folder/'predictions.csv')
        if kind == 'rows_debug':
            pred.loc[0, 'run_status'] = 'debug'
        else:
            pred = pred.drop(columns='run_status')
        pred.to_csv(folder/'predictions.csv', index=False)
        metadata['prediction_sha256'] = sha256(folder/'predictions.csv')
    path.write_text(json.dumps(metadata))
    refresh_freeze(folder)
    forbid_observation_parse(monkeypatch)
    with pytest.raises(ValueError, match='unfrozen|run_status=frozen_prediction'):
        validate_package(root, monkeypatch)


@pytest.mark.parametrize('field', ['conditions_sha256', 'parameters_sha256', 'prediction_sha256', 'derivatives_sha256'])
@pytest.mark.parametrize('mutation', ['wrong', 'missing'])
def test_all_internal_hashes_required_and_verified(synthetic, monkeypatch, field, mutation):
    comparison(synthetic, monkeypatch)
    root, _, _ = synthetic
    folder = root/'holdout/v1'
    path = folder/'prediction_metadata.json'
    metadata = json.loads(path.read_text())
    if mutation == 'wrong':
        metadata[field] = '0'*64
    else:
        del metadata[field]
    path.write_text(json.dumps(metadata))
    refresh_freeze(folder)
    forbid_observation_parse(monkeypatch)
    with pytest.raises(ValueError, match='metadata hash mismatch: '+field):
        validate_package(root, monkeypatch)


@pytest.mark.parametrize('name', ['observations.csv', 'conditions.csv', 'predictions.csv',
                                 'model_derivatives.csv', 'prediction_metadata.json'])
def test_all_package_files_must_be_hashed_in_freeze(synthetic, monkeypatch, name):
    comparison(synthetic, monkeypatch)
    root, _, _ = synthetic
    path = root/'holdout/v1/freeze.json'
    freeze = json.loads(path.read_text())
    del freeze[name+'_sha256']
    path.write_text(json.dumps(freeze))
    forbid_observation_parse(monkeypatch)
    with pytest.raises(ValueError, match='frozen holdout input hash mismatch'):
        validate_package(root, monkeypatch)


def test_decisive_ensemble_fixed_controls_and_varying_materials(synthetic):
    root, frozen, _ = synthetic
    scenario = load_config(root/'configs/scenarios.yaml')['scenario']
    settings = load_config(root/'configs/revision.yaml')
    import yaml
    sourced = yaml.safe_load((root/'configs/sourced_ranges.yaml').read_text())
    fixed = nominal_controls(scenario)
    # Independent expectations from model_spec §6, so a wrong mapping cannot pass
    # merely because the sampler and report share the same implementation.
    assert fixed == dict(T_ads=308.15, P_ads=1., z_ads_C=.05, T_R1=383.15, P_R1=1.,
                         T_R2=363.15, P_R2=.1, y_R1_C=.001, y_R1_W=.001,
                         y_R2_C=.01, y_R2_W=.01, t_ads=1800., t_des=1800.)
    for measure in ('stress', 'analog'):
        for seed in (12001, 12002):
            p = parameter_draws(scenario, settings, sourced, 64, seed, 'availability', frozen['fits'][0], measure)
            assert all(np.array_equal(p[k], np.full(64, v)) for k, v in fixed.items())
            assert np.ptp(p['Q_d']) > 0 and np.ptp(p['n_N']) > 0 and np.ptp(p['tau_over_t']) > 0
            for kind in ('ads', 'R1', 'R2'):
                gas = gas_arrays(p, kind, RH=40)
                assert all(np.ptp(v) == 0 for v in gas.values())
    result = run_ensemble(root, count=64, repeats=2, debug=True, branch_limit=2, plots=False)
    assert result['analysis_role'] == 'nominal_H1_H1a' and result['fixed_controls'] == fixed
    assert result['control_sensitivity']['decisive'] is False
    for path in (root/'reports/ensemble').rglob('samples.npz'):
        with np.load(path) as evidence:
            for repeat in range(2):
                names = evidence[f'{repeat}/parameter_names'].tolist()
                values = evidence[f'{repeat}/parameters']
                for key, value in fixed.items():
                    assert np.array_equal(values[:, names.index(key)], np.full(64, value))
    # The legacy screening remains a separate, non-decisive control sensitivity.
    sensitivity = draws(scenario, 64, 12001, 'availability', 10., settings)
    assert np.ptp(sensitivity['T_R1']) > 0 and np.ptp(sensitivity['t_des']) > 0
