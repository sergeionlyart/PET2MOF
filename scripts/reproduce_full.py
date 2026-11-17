#!/usr/bin/env python3
"""Clean prereg-v1 calibration + full ensemble, with one enclosing passport."""
from pathlib import Path
import sys
import subprocess
from pet2mof.runs import run_command
from predict_holdout import require_freeze


def main():
    root = Path(__file__).resolve().parents[1]
    require_freeze(root)
    inputs = ['Makefile', 'pyproject.toml', 'uv.lock', 'data/processed/c_series/manifest.json']
    for directory in ('configs', 'src/pet2mof/model', 'src/pet2mof/calibration'):
        inputs += [p.relative_to(root).as_posix() for p in sorted((root/directory).glob('*')) if p.suffix in ('.py', '.yaml')]
    for source in ('S100', 'S105', 'S106'):
        inputs += [p.relative_to(root).as_posix() for p in sorted((root/'data/processed/c_series').glob('C-'+source+'-*.csv'))]
    inputs += ['scripts/calibrate_final.py', 'scripts/ensemble.py', 'scripts/reproduce_full.py', 'scripts/predict_holdout.py',
               'src/pet2mof/data/c_series.py', 'src/pet2mof/runs.py', 'docs/hypotheses.md', 'docs/validation_protocol.md']
    # run.py rejects a dirty starting tree. Each child is sequential; no CI.
    path, passport = run_command(root, name='T018-full', purpose='Frozen C calibration and full branch ensemble',
        hypothesis='conditional forecast, branches separate', inputs=inputs,
        outputs=['configs/frozen_parameters.yaml', 'reports/ensemble/summary.json', 'reports/ensemble/SHA256SUMS.large'],
        command=[sys.executable, '-c',
                 'import subprocess,sys; subprocess.run([sys.executable,"scripts/calibrate_final.py"],check=True); '
                 'subprocess.run(["git","diff","--quiet","HEAD","--","configs/frozen_parameters.yaml"],check=True); '
                 'subprocess.run([sys.executable,"scripts/ensemble.py","--worker-run-id","{run_id}"],check=True)'],
        seed=12001, limitations=['requires independent prereg-v1 freeze and all required verified C inputs'])
    print(path.relative_to(root))
    return passport['exit_code']


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, FileNotFoundError, subprocess.CalledProcessError) as exc:
        print('full reproduction refused: '+str(exc), file=sys.stderr)
        raise SystemExit(2)
