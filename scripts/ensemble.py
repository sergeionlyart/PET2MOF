#!/usr/bin/env python3
"""Branch ensembles with local passports; full defaults: 4 x 4096 per branch."""
import argparse
from pathlib import Path
import sys
import subprocess
import yaml
from pet2mof.calibration.ensemble import run_ensemble
from pet2mof.runs import run_command


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--parameters', default='configs/frozen_parameters.yaml')
    p.add_argument('--output', default='reports/ensemble')
    p.add_argument('--samples', type=int, default=4096)
    p.add_argument('--repeats', type=int, default=4)
    p.add_argument('--seed', type=int, default=12001)
    p.add_argument('--debug', action='store_true', help='allow dirty tree; all output debug')
    p.add_argument('--branch-limit', type=int)
    p.add_argument('--no-plots', action='store_true')
    p.add_argument('--worker-run-id', help=argparse.SUPPRESS)
    args = p.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = (root/args.output).resolve(); output.relative_to(root)
    parameters = (root/args.parameters).resolve(); parameters.relative_to(root)
    if not args.debug:
        from predict_holdout import require_freeze
        require_freeze(root)
    if args.worker_run_id:
        run_ensemble(root, frozen_path=args.parameters, output=args.output, count=args.samples, repeats=args.repeats,
                     seed=args.seed, debug=args.debug, run_id=args.worker_run_id, branch_limit=args.branch_limit,
                     plots=not args.no_plots)
        return 0
    if args.branch_limit is not None and (args.branch_limit < 1 or args.branch_limit > 360):
        p.error('branch-limit must be in 1..360')
    if args.no_plots and not args.debug:
        p.error('production requires maps')
    frozen = yaml.safe_load(parameters.read_text())
    if frozen['missing']:
        p.error('missing calibrated inputs: '+str(frozen['missing']))
    inputs = [args.parameters, 'Makefile', 'pyproject.toml', 'uv.lock', 'scripts/ensemble.py',
              'scripts/calibrate_final.py', 'scripts/predict_holdout.py', 'scripts/validate.py',
              'configs/scenarios.yaml', 'configs/revision.yaml', 'configs/sourced_ranges.yaml',
              'docs/hypotheses.md', 'docs/validation_protocol.md', 'docs/decisions.md', 'data/processed/c_series/manifest.json']
    for folder in ('src/pet2mof/model', 'src/pet2mof/calibration'):
        inputs += [str(s.relative_to(root)) for s in sorted((root/folder).glob('*.py'))]
    inputs += ['src/pet2mof/runs.py', 'src/pet2mof/data/c_series.py']
    inputs += sorted({r['input_path'] for r in frozen['inputs']})
    command = [sys.executable, 'scripts/ensemble.py', *sys.argv[1:], '--worker-run-id', '{run_id}']
    path, passport = run_command(root, name='T018-ensemble', purpose='Separate mechanism/structure/reading/transfer/defect ensembles',
        hypothesis='conditional forecast; no pooling of branches; no independent validation claim', command=command,
        inputs=inputs, outputs=[str((output/s).relative_to(root)) for s in ('summary.json', 'SHA256SUMS.large')],
        seed=args.seed, allow_dirty=args.debug,
        parameters={'samples_per_repeat': {'value': args.samples, 'unit': '1'}, 'repeats': {'value': args.repeats, 'unit': '1'}},
        limitations=['target U unknown: full protocol convergence and decisive hypothesis status cannot be certified',
                     'analog ranges are provisional proxy sensitivity, not a target prior'])
    print(f'run_id={passport["run_id"]} status={passport["status"]} exit_code={passport["exit_code"]} seconds={passport["resources"]["elapsed_seconds"]:.3f}')
    print(path.relative_to(root))
    if passport['exit_code']:
        print('Diagnostics: private/run_logs/'+passport['run_id']+'/stderr.log')
    return passport['exit_code']


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, FileNotFoundError, subprocess.CalledProcessError) as exc:
        print('ensemble refused: '+str(exc), file=sys.stderr)
        raise SystemExit(2)
