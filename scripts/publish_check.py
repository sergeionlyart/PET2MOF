#!/usr/bin/env python3
"""Fail closed, with paths/rule names only; never print matched text or git identity."""

import fnmatch
import hashlib
import json
import re
import shutil
import stat
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


def load_allowlist(root, *, entries=None):
    """Exact paths and checks only; malformed review records fail closed."""
    if entries is None:
        entries = index_entries(root)
    entry = entries.get("configs/publish_allowlist.yaml")
    if entry is None:
        return []
    mode, oid = entry
    if mode not in {"100644", "100755"}:
        raise ValueError("non-regular allowlist")
    records = yaml.safe_load(index_blob(root, oid).decode("utf-8"))
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


# Canonical publication policy. .gitignore and .dockerignore mirror these
# patterns; regression tests enforce their agreement. Match directories at any
# depth, and root-relative paths containing a slash exactly as Git does.
CREDENTIAL_PATTERNS = (
    "**/credentials*.json", "**/auth.json", "**/service_account*.json",
    "**/application_default_credentials.json", "*.pem", "*.key", "*.p12", "*.pfx",
)
FORBIDDEN_PATTERNS = (
    ".env*", "*.env", "private/", "secrets/", ".secrets/", ".local/", ".agent_sessions/",
    *CREDENTIAL_PATTERNS, "data/raw/pdf/", "data/raw/html/", "data/raw/figures_full/",
)


def forbidden_path(relative):
    parts = Path(relative).parts
    for pattern in FORBIDDEN_PATTERNS:
        if pattern.endswith("/"):
            directory = pattern.rstrip("/")
            if ("/" in directory and relative.startswith(directory + "/")) or directory in parts[:-1]:
                return True
        elif pattern.startswith("**/"):
            if fnmatch.fnmatchcase(parts[-1], pattern[3:]):
                return True
        elif pattern == ".env*":
            # Only the final component may be the public template (T008-09).
            if any(fnmatch.fnmatchcase(part, pattern) for part in parts[:-1]):
                return True
            if parts[-1] != ".env.example" and fnmatch.fnmatchcase(parts[-1], pattern):
                return True
        elif any(fnmatch.fnmatchcase(part, pattern) for part in parts):
            return True
    return False


def index_entries(root):
    result = command(root, ["git", "ls-files", "--stage", "-z"])
    if result.returncode:
        raise ValueError("unreadable index")
    entries = {}
    for record in result.stdout.split(b"\0"):
        if not record:
            continue
        header, name = record.split(b"\t", 1)
        mode, oid, stage = header.decode("ascii").split()
        relative = name.decode("utf-8")
        if stage != "0" or mode not in {"100644", "100755", "120000", "160000"}:
            raise ValueError("unsupported index entry")
        if (not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", oid)
                or Path(relative).is_absolute() or ".." in Path(relative).parts):
            raise ValueError("invalid index entry")
        entries[relative] = (mode, oid)
    return entries


def index_blob(root, oid):
    result = command(root, ["git", "cat-file", "blob", oid])
    if result.returncode:
        raise ValueError("unreadable index blob")
    return result.stdout


def tree_oid(root):
    result = command(root, ["git", "write-tree"])
    oid = result.stdout.decode("ascii").strip()
    if result.returncode or not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", oid):
        raise ValueError("unreadable index tree")
    return oid


def index_matches_tree(root, entries, oid):
    result = command(root, ["git", "ls-tree", "-r", "-z", oid])
    if result.returncode:
        return False
    tree = {}
    for record in result.stdout.split(b"\0"):
        if record:
            header, name = record.split(b"\t", 1)
            mode, _, blob = header.decode("ascii").split()
            tree[name.decode("utf-8")] = (mode, blob)
    return entries == tree


def no_symlink_components(root, relative):
    """lstat, including dangling links; never open working file contents."""
    path = root
    for part in Path(relative).parts:
        path = path / part
        try:
            mode = path.lstat().st_mode
        except FileNotFoundError:
            return True  # Deleted working paths still have their index blobs.
        if stat.S_ISLNK(mode):
            return False
    return True


def owner_markers(root):
    """Literal strings that identify this machine's owner: home path and private global e-mail."""
    markers = []
    home = str(Path.home())
    if home.count("/") >= 2:
        markers.append(home + "/")
    email = command(root, ["git", "config", "--global", "user.email"])
    value = email.stdout.decode("utf-8", "replace").strip() if email.returncode == 0 else ""
    if "@" in value and not value.lower().endswith("@users.noreply.github.com"):
        markers.append(value)
    return markers


def check(root):
    root = Path(root).resolve()
    failures = []

    def report(label, ok):
        print(f"{'PASS' if ok else 'FAIL'} {label}")
        if not ok:
            failures.append(label)

    try:
        checked_tree = tree_oid(root)
        entries = index_entries(root)
        if not index_matches_tree(root, entries, checked_tree):
            raise ValueError("index changed while capturing tree")
    except (OSError, ValueError, UnicodeError):
        report("git-index-readable", False)
        return 1
    print(f"publish-check: tree={checked_tree}")
    private = {name for name in entries if forbidden_path(name)}
    report("no-private-tracked-files", not private)
    for name in sorted(private):
        print(f"FAIL forbidden-index:path={json.dumps(name, ensure_ascii=True)}")

    # Every local branch (main, holdout/*, report branches), HEAD and all tags are
    # publication roots. Every reachable commit tree is inspected, including files
    # deleted by later commits.
    history = command(root, ["git", "rev-list", "--branches", "--tags", "HEAD"])
    history_ok = history.returncode == 0
    seen = set()
    for commit in history.stdout.decode("ascii").splitlines() if history_ok else []:
        result = command(root, ["git", "ls-tree", "-r", "--name-only", "-z", commit])
        if result.returncode:
            history_ok = False
            continue
        for name in result.stdout.decode("utf-8").split("\0")[:-1]:
            if forbidden_path(name):
                history_ok = False
                if name not in seen:
                    print(f"FAIL forbidden-history:commit={commit}:path={json.dumps(name, ensure_ascii=True)}")
                    seen.add(name)
    report("no-private-history-files", history_ok)
    # Machine-specific owner markers (home directory, private global e-mail) must
    # not occur in any reachable commit. Values are never printed.
    markers = owner_markers(root)
    marker_ok = history.returncode == 0
    for commit in history.stdout.decode("ascii").splitlines() if marker_ok and markers else []:
        args = ["git", "grep", "-I", "-l", "-F"]
        for marker in markers:
            args += ["-e", marker]
        found = command(root, args + [commit])
        if found.returncode not in (0, 1):
            marker_ok = False
        elif found.returncode == 0:
            marker_ok = False
            for name in found.stdout.decode("utf-8", "replace").splitlines():
                print(f"FAIL owner-marker-history:path={json.dumps(name.split(':', 1)[-1], ensure_ascii=True)}:commit={commit}")
    report("no-owner-markers-in-history", marker_ok)
    report("no-workflows", not (root / ".github/workflows").exists()
           and not any(path.startswith(".github/workflows/") for path in entries))
    identity = command(root, ["git", "config", "user.email"])
    report("noreply-git-identity", identity.returncode == 0 and identity.stdout.strip().lower().endswith(b"@users.noreply.github.com"))
    try:
        allowlist = load_allowlist(root, entries=entries)
    except (OSError, ValueError, yaml.YAMLError):
        report("publish-allowlist-valid", False)
        allowlist = []
    # Materialize only index blob bytes. Neither own checks nor gitleaks snapshots
    # follow working-tree paths (even when parents are replaced with symlinks).
    blobs = {}
    unreadable = 0
    for relative, (mode, oid) in entries.items():
        try:
            safe = mode in {"100644", "100755"} and no_symlink_components(root, relative)
            if not safe:
                unreadable += 1
            elif relative not in private:
                blobs[relative] = index_blob(root, oid)
        except (OSError, ValueError):
            unreadable += 1
    for entry in allowlist:
        payload = blobs.get(entry["path"])
        if payload is None or hashlib.sha256(payload).hexdigest() != entry["sha256"]:
            report(f"publish-allowlist-current:path={json.dumps(entry['path'], ensure_ascii=True)}", False)
    counts = {}
    bad_notebooks = 0
    for relative, payload in blobs.items():
        try:
            text = payload.decode("utf-8")
        except UnicodeDecodeError:
            continue  # Binary artifacts require manual publication review (§10.3).
        for rule in sensitive_rules(text):
            if not allowed_text_check(allowlist, relative, rule, payload):
                counts[rule] = counts.get(rule, 0) + 1
                print(f"FAIL public-file:{rule}:path={json.dumps(relative, ensure_ascii=True)}")
        if relative.endswith(".ipynb"):
            try:
                notebook = json.loads(text)
                bad_notebooks += any(cell.get("outputs") or cell.get("execution_count") is not None for cell in notebook["cells"])
            except (ValueError, KeyError, TypeError, AttributeError):
                bad_notebooks += 1
    report("public-files-readable-no-symlinks", unreadable == 0)
    for rule in TEXT_CHECKS:
        report(f"public-text:{rule}:files={counts.get(rule, 0)}", counts.get(rule, 0) == 0)
    report("notebooks-without-outputs", bad_notebooks == 0)

    if not shutil.which("gitleaks"):
        report("gitleaks-installed", False)
    elif ".gitleaks.toml" not in blobs:
        report("gitleaks-index-config-present", False)
    else:
        with tempfile.TemporaryDirectory(prefix="publish-") as directory:
            snapshot = Path(directory) / "public"
            snapshot.mkdir()
            config = Path(directory) / "gitleaks.toml"
            config.write_bytes(blobs[".gitleaks.toml"])
            for relative, payload in blobs.items():
                target = snapshot / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(payload)
                target.chmod(int(entries[relative][0], 8) & 0o777)
            scans = [
                ("gitleaks-index-snapshot", snapshot, ["detect", "--no-git", "--source", "."]),
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
                        for path in sorted({item["File"] for item in findings}):
                            print(f"FAIL {label}:path={json.dumps(path, ensure_ascii=True)}")
                    except (OSError, ValueError, TypeError, KeyError):
                        report(f"{label}-report-readable", False)
    try:
        unchanged = tree_oid(root) == checked_tree
    except (OSError, ValueError, UnicodeError):
        unchanged = False
    report("git-index-unchanged", unchanged)
    print(f"publish-check: tree={checked_tree} {len(failures)} failed checks")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(check(Path(__file__).resolve().parents[1]))
