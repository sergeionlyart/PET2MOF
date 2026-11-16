#!/usr/bin/env python3
"""Fail closed, with paths/rule names only; never print matched text or git identity."""

import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import yaml


def command(root, args):
    return subprocess.run(args, cwd=root, capture_output=True, check=False)


TEXT_CHECKS = ("absolute-user-path", "non-noreply-email", "authorization-literal", "credential-literal")


def reserved_email_domain(domain):
    domain = domain.lower()
    return (domain in {"example.com", "example.org", "example.net"}
            or domain.endswith((".test", ".invalid")))


def load_allowlist(root):
    """Exact paths and checks only; malformed review records fail closed."""
    path = root / "configs/publish_allowlist.yaml"
    if path.is_symlink():
        raise ValueError("symlink allowlist")
    if not path.exists():
        return []
    records = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise ValueError("expected review records")
    for entry in records:
        if not isinstance(entry, dict) or set(entry) != {"path", "check", "reason", "sha256"}:
            raise ValueError("invalid review record")
        if not all(isinstance(value, str) for value in entry.values()):
            raise ValueError("invalid review value")
        relative = Path(entry["path"])
        if (relative.is_absolute() or ".." in relative.parts
                or relative.as_posix() != entry["path"]
                or entry["check"] not in TEXT_CHECKS or not entry["reason"].strip()
                or not re.fullmatch(r"[0-9a-f]{64}", entry["sha256"])):
            raise ValueError("invalid review scope")
    return records


def allowed_text_check(records, relative, rule, payload):
    digest = hashlib.sha256(payload).hexdigest()
    return any(entry["path"] == relative and entry["check"] == rule
               and entry["sha256"] == digest for entry in records)


def sensitive_rules(text):
    rules = []
    if "/Users/" in text:
        rules.append("absolute-user-path")
    emails = re.findall(r"[A-Za-z0-9_.+%-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})", text)
    if any(domain.lower() != "users.noreply.github.com" and not reserved_email_domain(domain) for domain in emails):
        rules.append("non-noreply-email")
    if "Bearer " in text:
        rules.append("authorization-literal")
    if "private_key" in text:
        rules.append("credential-literal")
    return rules


def check(root):
    root = Path(root).resolve()
    failures = []

    def report(label, ok):
        print(f"{'PASS' if ok else 'FAIL'} {label}")
        if not ok:
            failures.append(label)

    tracked_run = command(root, ["git", "ls-files", "-z"])
    if tracked_run.returncode:
        report("git-index-readable", False)
        return 1
    tracked = tracked_run.stdout.decode().split("\0")[:-1]
    # Also inspect untracked publishable source files in this pre-commit worktree.
    untracked_run = command(root, ["git", "ls-files", "--others", "--exclude-standard", "-z"])
    report("git-untracked-readable", untracked_run.returncode == 0)
    public = sorted(set(tracked + untracked_run.stdout.decode().split("\0")[:-1]))

    def dotenv(path):
        name = Path(path).name
        return name != ".env.example" and (name == ".env" or name.endswith(".env") or name.startswith(".env."))

    report("dotenv-not-in-index", not any(dotenv(path) for path in tracked))
    history = command(root, ["git", "log", "--all", "--format=%H", "--", ".env", "*.env", ".env.*", ":(exclude).env.example", ":(exclude)**/.env.example"])
    report("dotenv-not-in-history", history.returncode == 0 and not history.stdout.strip())
    report("no-workflows", not (root / ".github/workflows").exists()
           and not any(path.startswith(".github/workflows/") for path in public))
    private = ("private/", "data/raw/pdf/", "data/raw/html/")
    report("no-private-tracked-files", not any(path.startswith(private) for path in tracked))
    identity = command(root, ["git", "config", "user.email"])
    report("noreply-git-identity", identity.returncode == 0 and identity.stdout.strip().lower().endswith(b"@users.noreply.github.com"))
    try:
        allowlist = load_allowlist(root)
    except (OSError, ValueError, yaml.YAMLError):
        report("publish-allowlist-valid", False)
        allowlist = []
    for entry in allowlist:
        reviewed = root / entry["path"]
        try:
            relative = Path(entry["path"])
            current = (entry["path"] in public and not dotenv(entry["path"])
                       and not entry["path"].startswith(private)
                       and not any((root / parent).is_symlink()
                                   for parent in (relative, *relative.parents))
                       and hashlib.sha256(reviewed.read_bytes()).hexdigest() == entry["sha256"])
        except OSError:
            current = False
        if not current:
            report(f"publish-allowlist-current:path={json.dumps(entry['path'], ensure_ascii=True)}", False)
    counts = {}
    bad_notebooks = 0
    unreadable = 0
    for relative in public:
        if dotenv(relative) or relative.startswith(private):
            continue  # Do not read secret/private contents, even if incorrectly tracked.
        path = root / relative
        if not path.exists():
            continue  # Tracked deletions have no working-tree content.
        if path.is_symlink():
            unreadable += 1  # Never follow a symlink to credentials outside the worktree.
            continue
        try:
            payload = path.read_bytes()
            text = payload.decode("utf-8")
        except UnicodeDecodeError:
            continue  # Binary artifacts require the manual publication review (§10.3).
        except OSError:
            unreadable += 1
            continue
        for rule in sensitive_rules(text):
            if not allowed_text_check(allowlist, relative, rule, payload):
                counts[rule] = counts.get(rule, 0) + 1
                print(f"FAIL public-file:{rule}:path={json.dumps(relative, ensure_ascii=True)}")
        if relative.endswith(".ipynb"):
            try:
                notebook = json.loads(text)
                bad_notebooks += any(cell.get("outputs") or cell.get("execution_count") is not None for cell in notebook["cells"])
            except (ValueError, KeyError, TypeError):
                bad_notebooks += 1
    report("public-files-readable-no-symlinks", unreadable == 0)
    for rule in TEXT_CHECKS:
        report(f"public-text:{rule}:files={counts.get(rule, 0)}", counts.get(rule, 0) == 0)
    report("notebooks-without-outputs", bad_notebooks == 0)

    if not shutil.which("gitleaks"):
        report("gitleaks-installed", False)
    else:
        # Scan only publishable working-tree files. Private/ignored directories are
        # never copied; the same checked-in config governs all three scans.
        config = root / ".gitleaks.toml"
        with tempfile.TemporaryDirectory(prefix="publish-") as directory:
            snapshot = Path(directory) / "public"
            snapshot.mkdir()
            for relative in public:
                source = root / relative
                if (dotenv(relative) or relative.startswith(private)
                        or not source.is_file() or source.is_symlink()):
                    continue
                target = snapshot / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
            scans = [
                ("gitleaks-working-tree", snapshot, ["detect", "--no-git", "--source", "."]),
                ("gitleaks-all-history", root, ["detect", "--source", ".", "--log-opts=--all"]),
                ("gitleaks-staged", root, ["protect", "--staged", "--source", "."]),
            ]
            for label, scan_root, args in scans:
                scan_report = Path(directory) / f"{label}.json"
                result = command(scan_root, ["gitleaks", *args, "--config", str(config),
                                        "--redact", "--no-banner", "--no-color",
                                        "--report-format=json", "--report-path", str(scan_report)])
                report(label, result.returncode == 0)
                if result.returncode and scan_report.is_file():
                    try:
                        findings = json.loads(scan_report.read_text(encoding="utf-8"))
                        paths = {item["File"] for item in findings}
                        for path in sorted(paths):
                            print(f"FAIL {label}:path={json.dumps(path, ensure_ascii=True)}")
                    except (OSError, ValueError, TypeError, KeyError):
                        report(f"{label}-report-readable", False)
    print(f"publish-check: {len(failures)} failed checks")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(check(Path(__file__).resolve().parents[1]))
