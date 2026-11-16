#!/usr/bin/env python3
"""Fail closed, with counts/rule names only; never print matched text or git identity."""

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


def command(root, args):
    return subprocess.run(args, cwd=root, capture_output=True, check=False)


def sensitive_rules(text):
    rules = []
    if "/Users/" in text:
        rules.append("absolute-user-path")
    emails = re.findall(r"[A-Za-z0-9_.+%-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})", text)
    if any(domain.lower() != "users.noreply.github.com" for domain in emails):
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
            counts[rule] = counts.get(rule, 0) + 1
        if relative.endswith(".ipynb"):
            try:
                notebook = json.loads(text)
                bad_notebooks += any(cell.get("outputs") or cell.get("execution_count") is not None for cell in notebook["cells"])
            except (ValueError, KeyError, TypeError):
                bad_notebooks += 1
    report("public-files-readable-no-symlinks", unreadable == 0)
    for rule in ("absolute-user-path", "non-noreply-email", "authorization-literal", "credential-literal"):
        report(f"public-text:{rule}:files={counts.get(rule, 0)}", counts.get(rule, 0) == 0)
    report("notebooks-without-outputs", bad_notebooks == 0)

    if not shutil.which("gitleaks"):
        report("gitleaks-installed", False)
    else:
        # Scanner output is captured, not echoed: even diagnostics must not expose values.
        # Exclusions apply ONLY to working-tree scanning, never history/staged scans.
        cache = root / ".uv-cache"
        cache.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=cache, prefix="publish-") as directory:
            config = Path(directory) / "gitleaks.toml"
            config.write_text('[extend]\nuseDefault = true\n[allowlist]\npaths = [\'(^|/)(\\.venv|\\.uv-cache|private|\\.git)(/|$)\']\n', encoding="utf-8")
            scans = [
                ("gitleaks-working-tree", ["detect", "--no-git", "--source", ".", "--config", str(config)]),
                ("gitleaks-all-history", ["detect", "--source", ".", "--log-opts=--all"]),
                ("gitleaks-staged", ["protect", "--staged", "--source", "."]),
            ]
            for label, args in scans:
                result = command(root, ["gitleaks", *args, "--redact", "--no-banner", "--no-color"])
                report(label, result.returncode == 0)
    print(f"publish-check: {len(failures)} failed checks")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(check(Path(__file__).resolve().parents[1]))
