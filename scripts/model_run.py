#!/usr/bin/env python3
"""Construct a complete local debug passport through the existing scripts/run.py.

No dependencies/network/holdout discovery. Source paths are explicit C allowlists.
All model code and configuration bytes are hashed even though commits are forbidden.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import yaml
from pet2mof.model.config import load_config


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['demo','screen'])
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    out=root/'reports/T013';out.mkdir(parents=True,exist_ok=True)
    scenario=load_config(root/'configs/scenarios.yaml')['scenario']
    raw=yaml.safe_load((root/'configs/scenarios.yaml').read_text())['scenario']
    parameters={k:v for k,v in raw.items() if isinstance(v,dict) and 'value' in v}
    # Nested and interval assumptions remain in hashed configs/scenarios.yaml.
    param_path=out/'run_parameters.json'
    param_path.write_text(json.dumps(parameters,indent=2,allow_nan=False)+'\n')
    inputs=['configs/calibration.yaml','configs/scenarios.yaml','configs/constants.yaml','configs/demo_expected.yaml',
            'data/extraction/digitization/T006-S100-FigS5.csv',
            'data/extraction/digitization/T006-S100-FigS5.digitization.yaml',
            'docs/model_spec.md','docs/parameters.md','docs/validation_protocol.md','docs/decisions.md','docs/data_split.md',
            'pyproject.toml','uv.lock','Makefile','src/pet2mof/units.py','src/pet2mof/runs.py','src/pet2mof/data/nist_isodb.py']
    for folder in ('src/pet2mof/model','src/pet2mof/calibration'):
        inputs.extend(str(p.relative_to(root)) for p in sorted((root/folder).glob('*.py')))
    inputs.extend('scripts/'+p for p in ('run.py','demo.py','model_run.py','model_report.py','screen.py','calibrate.py','validate.py'))
    inputs.extend(str(p.relative_to(root)) for p in sorted((root/'tests').glob('test_model_*.py')))
    for prefix in ('10.1021acs.inorgchem.5b00435.','10.1039C2cp23839j.'):
        inputs.extend(str(p.relative_to(root)) for p in sorted((root/'data/raw/nist_isodb/isotherms').glob(prefix+'*.json')))
    if args.mode=='screen':inputs.append('reports/T013/demo.json')
    outputs=['reports/T013/demo.json','configs/fitted_debug.yaml'] if args.mode=='demo' else ['reports/T013/screen.json']
    command=[sys.executable,'scripts/run.py','--name','T013-'+args.mode,'--purpose','C control reproduction' if args.mode=='demo' else 'D-07 wide stress screening',
             '--hypothesis','debug only; no validation or hypothesis verdict','--allow-dirty','--seed',str(scenario['seed']),
             '--parameters',str(param_path.relative_to(root))]
    for path in inputs:command+=['--input',path]
    for path in outputs:command+=['--output',path]
    command+=['--',sys.executable,'scripts/'+('demo.py' if args.mode=='demo' else 'screen.py')]
    return subprocess.run(command,cwd=root,check=False).returncode

if __name__=='__main__':raise SystemExit(main())
