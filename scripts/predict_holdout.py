#!/usr/bin/env python3
"""Predict from conditions only; never opens measured responses.

--dry-run accepts a synthetic directory outside holdout/. It bypasses the git
tag solely for tests, marks every output debug and never writes under holdout/.
"""
import argparse
import csv
import json
from pathlib import Path
import subprocess
import numpy as np
import yaml
from pet2mof.calibration.final import sha256, verify_frozen_inputs
from pet2mof.calibration.prediction import MODEL_LABELS, evaluate, derivatives

CONDITION_FIELDS = 'series point_id source_id extraction_id material gas observable unit basis T_K p_total_bar p_partial_bar y_CO2_dry RH_fraction w_PEI w_reading Mw_PEI notes'.split()


def require_freeze(root):
    def git(*args):
        return subprocess.run(['git', *args], cwd=root, text=True, capture_output=True, check=True).stdout.strip()
    try:
        head, tag = git('rev-parse', 'HEAD'), git('rev-parse', 'prereg-v1^{commit}')
    except subprocess.CalledProcessError:
        raise ValueError('prediction requires exact frozen prereg-v1 HEAD') from None
    if head != tag:
        raise ValueError('prediction requires exact frozen prereg-v1 HEAD')
    subprocess.run(['git', 'diff', '--exit-code', '--quiet', 'HEAD', '--', 'src', 'scripts', 'configs', 'docs', 'data/processed/c_series'],
                   cwd=root, check=True)
    if git('ls-files', '--others', '--exclude-standard', '--', 'src', 'scripts', 'configs', 'docs', 'data/processed/c_series'):
        raise ValueError('untracked scientific code/configuration is not frozen')
    return head


def predict(root, *, directory='holdout/v1', dry_run=False, parameters='configs/frozen_parameters.yaml'):
    root = Path(root).resolve()
    folder = (root/directory).resolve(); relative = folder.relative_to(root)
    if dry_run:
        if relative.parts and relative.parts[0] == 'holdout':
            raise ValueError('dry-run requires synthetic directory outside holdout/')
        commit = 'debug-synthetic'
    else:
        if relative.as_posix() != 'holdout/v1':
            raise ValueError('production conditions must be holdout/v1/conditions.csv')
        commit = require_freeze(root)
    parameter_path = (root/parameters).resolve(); parameter_path.relative_to(root)
    if not dry_run and parameter_path != root/'configs/frozen_parameters.yaml':
        raise ValueError('production requires frozen_parameters.yaml')
    frozen = yaml.safe_load(parameter_path.read_text())
    if frozen['include_provisional'] and not dry_run:
        raise ValueError('provisional calibration cannot predict production holdout')
    verify_frozen_inputs(root, frozen)
    path = folder/'conditions.csv'
    if path.is_symlink():
        raise ValueError('conditions input must be a regular conditions.csv file')
    with path.open(newline='') as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != CONDITION_FIELDS:
            raise ValueError('conditions schema mismatch; measured/extra fields forbidden')
        rows = list(reader)
    identities = [(r['series'], r['point_id']) for r in rows]
    if not rows or len(identities) != len(set(identities)):
        raise ValueError('empty conditions or duplicate point identity')
    predictions, derivs = [], []
    point = dict(fits=frozen['fits'], c_fits=frozen['c_fits'])
    for row in rows:
        for label in MODEL_LABELS:
            identity = dict(series=row['series'], point_id=row['point_id'], model=label)
            pred = dict(identity, q_pred=None, u_num=None, prediction_low=None, prediction_high=None,
                        status='not_testable', reason='', run_status='debug' if dry_run else 'frozen_prediction')
            der = dict(identity, dq_dp=None, dq_dT=None, dq_da=None, u_num=None)
            try:
                evaluate(row, point, label)
                values = [evaluate(row, sample, label) for sample in frozen['joint_draws']]
                q = float(np.median(values))
                low, high = np.quantile(values, [.025, .975])
                u_num = float(64*np.finfo(float).eps*max(1., abs(q), abs(low), abs(high)))
                pred.update(q_pred=float(q), u_num=u_num, prediction_low=float(low), prediction_high=float(high),
                            status='conditional_prediction', reason='calibration uncertainty only; unknown dq_dT/dq_da require zero matching input uncertainty')
                der.update(derivatives(row, point, label, ensemble=frozen['joint_draws']), u_num=u_num)
            except (ValueError, OverflowError) as exc:
                pred['reason'] = str(exc)
            predictions.append(pred); derivs.append(der)
    def write(name, records):
        with (folder/name).open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=list(records[0])); writer.writeheader(); writer.writerows(records)
    write('predictions.csv', predictions); write('model_derivatives.csv', derivs)
    metadata = dict(commit_sha=commit, conditions_sha256=sha256(path), parameters_sha256=sha256(parameter_path),
                    prediction_sha256=sha256(folder/'predictions.csv'), derivatives_sha256=sha256(folder/'model_derivatives.csv'),
                    uncertainty_method=frozen['uncertainty_method'], calibration_draws=len(frozen['joint_draws']),
                    prediction_center='median of joint calibration predictions; derivatives of the same median operator',
                    numerical_error='64*machine_epsilon*max(1,capacity,interval endpoints); analytical pure gas operators',
                    S2='D-11: S105 NH2 host, retained loading/Mw input only, S100 PEI parameters without refitting; moist/unknown basis untestable',
                    status='debug' if dry_run else 'frozen_prediction')
    (folder/'prediction_metadata.json').write_text(json.dumps(metadata, indent=2, allow_nan=False)+'\n')
    return predictions, derivs


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--directory', default='holdout/v1')
    args = parser.parse_args()
    try:
        predict(Path(__file__).resolve().parents[1], directory=args.directory, dry_run=args.dry_run)
    except (ValueError, FileNotFoundError, subprocess.CalledProcessError) as exc:
        parser.exit(2, str(exc)+'\n')
