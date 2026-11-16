"""Local commands from a committed tree, with durable passports even on failure."""

import importlib.metadata
import json
import os
import platform
import re
import resource
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from .ocr.cache import sha256_file
from .ocr.security import Redactor


def _utc():
    return datetime.now(timezone.utc)


def _relative(root, path):
    result = (root / path).resolve()
    try:
        return result, result.relative_to(root).as_posix()
    except ValueError:
        raise ValueError("run paths must remain in repository") from None


def _hash_paths(root, paths):
    result = []
    for path in paths:
        absolute, relative = _relative(root, path)
        if ".env" in absolute.name or relative.startswith(("private/", "secrets/", ".secrets/")):
            raise ValueError("private inputs/outputs must not enter public run passports")
        result.append({"path": relative, "sha256": sha256_file(absolute)})
    return result


def _validate_output(root, path):
    absolute, relative = _relative(root, path)
    if ".env" in absolute.name or relative.startswith(("private/", "secrets/", ".secrets/")):
        raise ValueError("private outputs must not enter public run passports")


def _safe_command(command):
    redactor = Redactor()
    result, redact_next = [], False
    for item in command:
        if redact_next:
            result.append("***")
            redact_next = False
        elif re.search(r"(?i)(secret|token|password|api[_-]?key|credential)", item):
            key, separator, _ = item.partition("=")
            result.append(key + "=***" if separator else key)
            redact_next = not bool(separator)
        else:
            result.append(redactor.text(item))
    return result


def run_command(root, *, name, purpose, hypothesis, command, inputs=(), outputs=(), parameters=None,
                seed=None, checks=None, limitations=None, allow_dirty=False):
    root = Path(root).resolve()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", name):
        raise ValueError("invalid run name")
    if not purpose or not hypothesis or not command or any(not isinstance(item, str) for item in command):
        raise ValueError("purpose, hypothesis and command required")
    parameters = parameters or {}
    if any(not isinstance(value, dict) or "value" not in value or not value.get("unit") for value in parameters.values()):
        raise ValueError("each parameter needs value and unit (use dimensionless explicitly)")
    json.dumps(parameters, allow_nan=False)
    status = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"], cwd=root, capture_output=True, check=True).stdout
    if status and not allow_dirty:
        raise RuntimeError("dirty tree refused; --allow-dirty is debugging only")
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, check=True, text=True).stdout.strip()
    start = _utc()
    run_id = f"{start.strftime('%Y%m%dT%H%M%S%fZ')}-{commit[:8]}-{name}"
    input_hashes = _hash_paths(root, inputs)
    for path in outputs:
        _validate_output(root, path)
    versions = {"python": platform.python_version()}
    for package in ("pet2mof", "numpy", "scipy", "pandas", "matplotlib", "pyyaml", "pymupdf", "pillow", "jsonschema", "pytest"):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = "not-installed"
    directory = root / "runs" / run_id
    directory.mkdir(parents=True, exist_ok=False)
    passport_path = directory / "passport.json"
    passport = {
        "run_id": run_id, "purpose": purpose, "hypothesis": hypothesis, "commit_sha": commit,
        "versions": versions, "inputs": input_hashes, "parameters": parameters, "seed": seed,
        "command": _safe_command(command), "started_utc": start.isoformat(), "finished_utc": None,
        "status": "debug" if allow_dirty else "running", "exit_code": None, "resources": {},
        "outputs": [], "checks": checks or [], "limitations": limitations or [],
    }

    def save():
        temporary = directory / ".passport.tmp"
        temporary.write_text(json.dumps(passport, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        temporary.replace(passport_path)

    save()
    # Raw program output is private; caller must not pass secrets on the command line.
    logs = root / "private" / "run_logs" / run_id
    logs.mkdir(parents=True, mode=0o700)
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    clock = time.monotonic()
    error = None
    try:
        with os.fdopen(os.open(logs / "stdout.log", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb") as stdout, \
             os.fdopen(os.open(logs / "stderr.log", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb") as stderr:
            child_env = {key: os.environ[key] for key in ("PATH", "LANG", "LC_ALL", "SYSTEMROOT") if key in os.environ}
            completed = subprocess.run(command, cwd=root, env=child_env, stdout=stdout, stderr=stderr, check=False)
            code = completed.returncode
    except KeyboardInterrupt:
        code, error = 130, "interrupted"
    except Exception:
        code, error = 127, "command could not be executed"
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    passport["resources"] = {
        "elapsed_seconds": time.monotonic() - clock,
        "child_user_seconds": after.ru_utime - before.ru_utime,
        "child_system_seconds": after.ru_stime - before.ru_stime,
        "child_maxrss": after.ru_maxrss, "maxrss_unit": "bytes" if platform.system() == "Darwin" else "KiB",
        "maxrss_scope": "process-lifetime child high-water mark",
    }
    passport["exit_code"] = code
    passport["finished_utc"] = _utc().isoformat()
    passport["status"] = "debug" if allow_dirty else ("completed" if code == 0 else "failed")
    passport["execution_status"] = "completed" if code == 0 else "failed"
    if error:
        passport["limitations"].append(error)
    try:
        passport["outputs"] = _hash_paths(root, outputs)
    except Exception:
        passport["limitations"].append("declared outputs missing or invalid")
        passport["execution_status"] = "failed"
        if not allow_dirty:
            passport["status"] = "failed"
        if code == 0:
            passport["exit_code"] = 1
    save()
    return passport_path, passport
