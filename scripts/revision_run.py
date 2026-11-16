#!/usr/bin/env python3
"""T015 offline, hashed debug passports; no repository commit or V data reads."""
import argparse
import sys
from pathlib import Path
from pet2mof.runs import run_command
from pet2mof.model.config import load_config


def main():
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['demo','screen','report'])
    args=parser.parse_args();root=Path(__file__).resolve().parents[1]
    settings=load_config(root/'configs/revision.yaml')
    inputs=['Makefile','pyproject.toml','uv.lock','docs/model_spec.md','docs/parameters.md','docs/decisions.md',
            'docs/data_split.md','docs/validation_protocol.md','docs/hypotheses.md','reports/T013/demo.json',
            'configs/calibration.yaml','configs/scenarios.yaml','configs/revision.yaml','src/pet2mof/runs.py',
            'data/extraction/digitization/T006-S100-FigS5.csv','data/processed/c_series/manifest.json',
            'scripts/revision_run.py','scripts/revision_demo.py','scripts/revision_screen.py','scripts/revision_report.py']
    for folder in ('src/pet2mof/model','src/pet2mof/calibration'):
        inputs += [p.relative_to(root).as_posix() for p in sorted((root/folder).glob('*.py'))]
    inputs+=['src/pet2mof/data/c_series.py']
    inputs += [p.relative_to(root).as_posix() for p in sorted((root/'tests').glob('*.py'))]
    for source in ('S100','S105','S106'):
        inputs += [p.relative_to(root).as_posix() for p in sorted((root/'data/processed/c_series').glob('C-'+source+'-*.csv'))]
    if args.mode=='demo':
        outputs=['reports/T015/demo.json','configs/fitted_v1_1_debug.yaml','reports/T015/diagnosis_residuals.png',
                 'reports/T015/diagnosis_shapes.png','reports/T015/profile_composite.png','reports/T015/profile_ratio.png']
        outputs += [f'reports/T015/{v}_{b}.png' for v in ('v1','v1.1-mof','v1.1-connectivity') for b in ('composite','ratio')]
    elif args.mode=='screen':
        inputs+=['reports/T015/demo.json'];outputs=['reports/T015/screen.json']+[f'reports/T015/screen_samples_{seed}.npz' for seed in settings['seeds']]
    else:
        inputs+=['reports/T015/demo.json','reports/T015/screen.json','reports/T015/tests.xml'];outputs=['reviews/T015_diagnosis.md','reviews/T015_screening.md','reviews/T015_revision_report.md']
    path,passport=run_command(root,name='T015-'+args.mode,purpose='C-only revision / D-07 sensitivity',
          hypothesis='debug; no independent validation; данных недостаточно',
          command=[sys.executable,'scripts/revision_'+args.mode+'.py','--run-id','{run_id}'],
          inputs=inputs,outputs=outputs,seed=15015 if args.mode=='screen' else None,allow_dirty=True,
          parameters={'samples_per_cell':{'value':settings['samples'],'unit':'1'},'seeds':{'value':settings['seeds'],'unit':'1'}},
          limitations=['No commit authorized: all outputs debug; exact code/input SHA256 recorded.',
                       'Requested gpt-6.1-sol/high; actual settings not exposed by this interface.',
                       'No V source/data opened; T011v and independent T016 pending.'])
    print('run_id='+passport['run_id'],'exit_code='+str(passport['exit_code']),'seconds='+str(round(passport['resources']['elapsed_seconds'],3)),flush=True)
    print(path.relative_to(root))
    if passport['exit_code']:
        print('Private diagnostic log: private/run_logs/'+passport['run_id']+'/stderr.log')
    return passport['exit_code']

if __name__=='__main__':raise SystemExit(main())
