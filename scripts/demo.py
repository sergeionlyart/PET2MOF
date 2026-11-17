#!/usr/bin/env python3
"""Fast, entirely offline debug example; called under scripts/run.py by make."""
import argparse
from pathlib import Path
from pet2mof.calibration.demo import reproduce

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--initialize-reference',action='store_true',help='compute without regression check; never rewrites expectations')
    args=parser.parse_args()
    result=reproduce(Path(__file__).resolve().parents[1],check_expected=not args.initialize_reference)
    print(result['regression_scalars'])
