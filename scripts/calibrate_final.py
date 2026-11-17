#!/usr/bin/env python3
"""Deterministic final C calibration. No V inputs and no git mutation."""
import argparse
from pathlib import Path
import yaml
from pet2mof.calibration.final import calibrate


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--include-provisional', action='store_true')
    p.add_argument('--draws', type=int, default=64)
    p.add_argument('--seed', type=int, default=18018)
    p.add_argument('--output', type=Path)
    args = p.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = args.output or Path('configs/frozen_parameters_provisional.yaml' if args.include_provisional else 'configs/frozen_parameters.yaml')
    output = (root/output).resolve(); output.relative_to(root)
    result = calibrate(root, include_provisional=args.include_provisional, draws=args.draws, seed=args.seed)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(yaml.safe_dump(result, sort_keys=False, allow_unicode=True))
    print(f'{output.relative_to(root)}: {result["status"]}; {args.draws} joint draws; missing={result["missing"]}')


if __name__ == '__main__':
    main()
