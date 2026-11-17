#!/usr/bin/env python3
"""Clean prereg-v1 calibration + full ensemble, with one enclosing passport."""
from pathlib import Path
import argparse
import sys
import subprocess
from pet2mof.runs import run_command
from pet2mof.calibration.freeze import require_freeze


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rehearsal', action='store_true',
                        help='debug only: 2 branches x 2 repeats x 8 draws, no plots; never scientific evidence')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    require_freeze(root)
    if subprocess.run(['git', 'status', '--porcelain', '--untracked-files=all'], cwd=root,
                      check=True, capture_output=True).stdout:
        raise ValueError('full reproduction requires a clean tree, including in rehearsal')
    inputs = ['Makefile', 'pyproject.toml', 'uv.lock', 'data/processed/c_series/manifest.json']
    for directory in ('configs', 'src/pet2mof/model', 'src/pet2mof/calibration'):
        inputs += [p.relative_to(root).as_posix() for p in sorted((root/directory).glob('*')) if p.suffix in ('.py', '.yaml')]
    for source in ('S100', 'S105', 'S106'):
        inputs += [p.relative_to(root).as_posix() for p in sorted((root/'data/processed/c_series').glob('C-'+source+'-*.csv'))]
    inputs += ['scripts/calibrate_final.py', 'scripts/ensemble.py', 'scripts/reproduce_full.py', 'scripts/predict_holdout.py',
               'src/pet2mof/data/c_series.py', 'src/pet2mof/runs.py', 'docs/hypotheses.md', 'docs/validation_protocol.md']
    # run.py rejects a dirty starting tree. Each child is sequential; no CI.
    ensemble_args = ['--debug', '--samples', '8', '--repeats', '2', '--branch-limit', '2', '--no-plots'] if args.rehearsal else []
    path, passport = run_command(root, name='T020-rehearsal' if args.rehearsal else 'T018-full',
        purpose='Debug chain rehearsal' if args.rehearsal else 'Frozen C calibration and full branch ensemble',
        hypothesis='conditional forecast, branches separate', inputs=inputs,
        outputs=['configs/frozen_parameters.yaml', 'reports/ensemble/summary.json', 'reports/ensemble/SHA256SUMS.large'],
        command=[sys.executable, '-c',
                 'import subprocess,sys; subprocess.run([sys.executable,"scripts/calibrate_final.py"],check=True); '
                 'subprocess.run(["git","diff","--quiet","HEAD","--","configs/frozen_parameters.yaml"],check=True); '
                 'subprocess.run([sys.executable,"scripts/ensemble.py","--worker-run-id","{run_id}"]+'+repr(ensemble_args)+',check=True)'],
        seed=12001, allow_dirty=args.rehearsal,
        parameters={'rehearsal': {'value': args.rehearsal, 'unit': '1'}},
        limitations=['requires independent prereg-v1 freeze and all required verified C inputs']+
                    (['small debug rehearsal; not a production ensemble or convergence result'] if args.rehearsal else []))
    print(path.relative_to(root))
    return passport['exit_code']


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, FileNotFoundError, subprocess.CalledProcessError) as exc:
        print('full reproduction refused: '+str(exc), file=sys.stderr)
        raise SystemExit(2)
