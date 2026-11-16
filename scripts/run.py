#!/usr/bin/env python3
"""Example: uv run --locked python scripts/run.py --name demo --purpose ... --hypothesis ... -- python ..."""

import argparse
import json
from pathlib import Path

from pet2mof.runs import run_command


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True)
    parser.add_argument("--purpose", required=True)
    parser.add_argument("--hypothesis", required=True)
    parser.add_argument("--input", action="append", default=[])
    parser.add_argument("--output", action="append", default=[])
    parser.add_argument("--parameters", type=Path, help="JSON mapping: parameter -> {value, unit}")
    parser.add_argument("--seed", type=int)
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    parameters = json.loads(args.parameters.read_text()) if args.parameters else {}
    try:
        path, passport = run_command(Path(__file__).resolve().parents[1], name=args.name,
            purpose=args.purpose, hypothesis=args.hypothesis, command=command, inputs=args.input,
            outputs=args.output, parameters=parameters, seed=args.seed, allow_dirty=args.allow_dirty)
    except (RuntimeError, ValueError):
        print("run refused: check clean tree, paths and required metadata")
        return 2
    print(f"run_id={passport['run_id']} status={passport['status']} exit_code={passport['exit_code']}")
    print(path.relative_to(Path(__file__).resolve().parents[1]))
    return passport["exit_code"] if passport["exit_code"] >= 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
