#!/usr/bin/env python3
"""D-07 stress screening only. Invoke via scripts/model_run.py screen for passport."""
import argparse
import json
from pathlib import Path
from pet2mof.calibration.screening import screen
from pet2mof.model.config import load_config

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--samples',type=int)
    parser.add_argument('--seed',type=int)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    demo=json.loads((root/'reports/T013/demo.json').read_text())
    scenario=load_config(root/'configs/scenarios.yaml')['scenario']
    result=screen(demo['fits'],demo['carriers'],scenario,count=args.samples,seed=args.seed)
    path=root/'reports/T013/screen.json'
    path.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    for name,b in result['branches'].items():
        print(name,b['status'],'accepted',b['accepted'],'rejected',b['rejected'])
