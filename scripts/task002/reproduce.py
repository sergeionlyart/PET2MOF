#!/usr/bin/env python3
"""Run intake and A together under one scripts/run.py passport."""

import argparse
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    for script in ("accept_pack.py", "screen_s2.py"):
        result = subprocess.run([sys.executable, f"scripts/task002/{script}", "--run-id", args.run_id],
                                cwd=ROOT, check=False)
        if result.returncode:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
