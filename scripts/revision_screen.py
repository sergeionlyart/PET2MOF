#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from pet2mof.model.config import load_config
from pet2mof.calibration.revision_screening import screen_revision

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--run-id',required=True);args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    demo=json.loads((root/'reports/T015/demo.json').read_text())
    result=screen_revision(root,demo,load_config(root/'configs/scenarios.yaml')['scenario'],load_config(root/'configs/revision.yaml'))
    result['run_id']=args.run_id;result['fit_run_id']=demo['run_id'];result['dataset_ids']=demo['dataset_ids']
    (root/'reports/T015/screen.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
