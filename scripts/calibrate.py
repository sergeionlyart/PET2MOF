#!/usr/bin/env python3
"""Explicit verified C-loader by default; provisional NIST requires --debug-nist."""
import argparse
import json
from pathlib import Path
from pet2mof.calibration.fit import verified_carriers, provisional_carriers

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--debug-nist',action='store_true')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    try:
        rows=provisional_carriers(root) if args.debug_nist else verified_carriers(root)
    except (FileNotFoundError,ValueError) as exc:
        parser.exit(2,str(exc)+'\n')
    out=root/'reports/T013';out.mkdir(parents=True,exist_ok=True)
    (out/'carrier_fit.json').write_text(json.dumps(rows,indent=2,allow_nan=False)+'\n')
