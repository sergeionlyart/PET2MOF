#!/usr/bin/env python3
"""Accept the distributed pack offline, executing only in a disposable copy."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
PACK = ROOT / "data/task002/PET2MOF_Task002_DataPack_v1.0"
SOURCE_COMMIT = "66bae26af9970c3142b72d25031c844b5461708f"
EXCEPTIONS = {"PET_CO2_Task_002_RU.md", "PET_CO2_Task_002_RU.pdf"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest_check(pack: Path) -> tuple[list[dict], list[dict], list[str]]:
    checks, excluded, retained = [], [], []
    seen = set()
    for line in (pack / "metadata/SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
        digest, rel = line.split("  ", 1)
        path = (pack / rel).resolve()
        if not path.is_relative_to(pack.resolve()) or rel in seen:
            raise ValueError("Unsafe or duplicate manifest path")
        seen.add(rel)
        if rel in EXCEPTIONS:
            excluded.append(dict(path=rel, expected_sha256=digest,
                                 reason="owner originals omitted from public pack; docs/task002/intake.md"))
            continue
        actual = sha256(path) if path.is_file() else None
        checks.append(dict(path=rel, expected_sha256=digest, actual_sha256=actual, passed=actual == digest))
        retained.append(line)
    if {r["path"] for r in excluded} != EXCEPTIONS:
        raise ValueError("Expected exactly two work-order manifest exceptions")
    return checks, excluded, retained


def function_asts(source: str) -> dict[str, str]:
    wanted = {"_number", "evaluate"}
    nodes = [n for n in ast.parse(source).body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
             and n.name in wanted]
    if len(nodes) != 2 or {n.name for n in nodes} != wanted:
        raise ValueError("Both unique top-level functions are required")
    return {n.name: ast.dump(n, include_attributes=False) for n in nodes}


def git_output(*args: str) -> bytes:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, check=True).stdout


def accept(pack: Path, run_id: str) -> dict:
    report = dict(task_id="T030-task002-screening", run_id=run_id,
                  status="failed", scope="integrity and numerical reproduction; not physical validation",
                  python_version=sys.version, interpreter="current sys.executable",
                  source_commit=SOURCE_COMMIT, commands=[], byte_comparisons=[], errors=[])
    try:
        report["head_sha"] = git_output("rev-parse", "HEAD").decode().strip()
        checks, exclusions, retained = manifest_check(pack)
        report["manifest"] = checks
        report["manifest_exceptions"] = exclusions
        report["manifest_sha256"] = sha256(pack / "metadata/SHA256SUMS.txt")
        for entry in exclusions:
            print(f"manifest exception: {entry['path']} — {entry['reason']}")
        if not all(r["passed"] for r in checks):
            raise ValueError("Distributed manifest mismatch; execution refused")
        originals = {p.relative_to(pack).as_posix(): p.read_bytes()
                     for p in (pack / "reference").rglob("*") if p.is_file()}
        originals["checks/data_check.json"] = (pack / "checks/data_check.json").read_bytes()
        # Only the copied manifest is adapted. All package scripts remain byte-identical.
        with tempfile.TemporaryDirectory(prefix="pet2mof-task002-") as temporary:
            copied = Path(temporary) / "pack"
            shutil.copytree(pack, copied, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            (copied / "metadata/SHA256SUMS.txt").write_text("\n".join(retained) + "\n", encoding="utf-8")
            child_env = {k: os.environ[k] for k in ("PATH", "LANG", "LC_ALL", "SYSTEMROOT") if k in os.environ}
            child_env["PYTHONDONTWRITEBYTECODE"] = "1"
            for args in (["scripts/check_data.py"], ["-m", "unittest", "discover", "-s", "tests"],
                         ["scripts/reference_baseline.py"]):
                result = subprocess.run([sys.executable, *args], cwd=copied, env=child_env,
                                        capture_output=True, text=True, check=False)
                report["commands"].append(dict(command=["{current_python}", *args], exit_code=result.returncode,
                                               stdout=result.stdout, stderr=result.stderr))
            generated = {p.relative_to(copied).as_posix() for p in (copied / "reference").rglob("*") if p.is_file()}
            report["reference_file_set_matches"] = generated == set(originals) - {"checks/data_check.json"}
            for rel, original in sorted(originals.items()):
                target = copied / rel
                actual = target.read_bytes() if target.is_file() else None
                report["byte_comparisons"].append(dict(path=rel, passed=actual == original,
                    supplied_sha256=hashlib.sha256(original).hexdigest(),
                    generated_sha256=hashlib.sha256(actual).hexdigest() if actual is not None else None))
            report["data_check_counts"] = json.loads((copied / "checks/data_check.json").read_text())["counts"]
        legacy = []
        files = sorted((pack / "data/legacy_original").glob("*.csv"))
        for path in files:
            data = path.read_bytes()
            actual = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
            expected = git_output("rev-parse", f"{SOURCE_COMMIT}:data/processed/c_series/{path.name}").decode().strip()
            legacy.append(dict(path=path.relative_to(pack).as_posix(), actual_git_blob_sha1=actual,
                               expected_git_blob_sha1=expected, passed=actual == expected))
        report["legacy_blobs"] = legacy
        historic = git_output("show", f"{SOURCE_COMMIT}:src/pet2mof/calibration/prediction.py").decode()
        fixture = (pack / "audit_fixture/prediction_excerpt.py").read_text(encoding="utf-8")
        original_ast, fixture_ast = function_asts(historic), function_asts(fixture)
        report["ast_functions"] = {name: original_ast[name] == fixture_ast[name] for name in original_ast}
        passed = (len(legacy) == 5 and all(r["passed"] for r in legacy)
                  and all(report["ast_functions"].values()) and report["reference_file_set_matches"]
                  and all(r["passed"] for r in report["byte_comparisons"])
                  and all(c["exit_code"] == 0 for c in report["commands"]))
        report["status"] = "passed" if passed else "failed"
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        # Avoid absolute machine paths and raw external errors in public evidence.
        report["errors"].append(type(error).__name__ + ": acceptance could not complete; check input files and local Git objects")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default="debug-unregistered")
    args = parser.parse_args()
    report = accept(PACK, args.run_id)
    output = ROOT / "reports/task002/intake/acceptance.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"acceptance: {report['status']} → reports/task002/intake/acceptance.json")
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
