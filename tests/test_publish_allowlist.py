"""Publication exceptions must preserve detection outside their reviewed scope."""

import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest
import yaml

from test_runs_publish import publish_module


@pytest.fixture
def tmp_path():
    # Synthetic secret markers must never enter the repository, even via basetemp.
    with tempfile.TemporaryDirectory(prefix="publish-test-") as directory:
        yield Path(directory)


@pytest.mark.parametrize("domain", ["example.com", "example.org", "example.net",
                                   "EXAMPLE.ORG", "fixture.test", "nested.fixture.invalid"])
def test_reserved_email_domains(domain):
    assert publish_module().sensitive_rules("person@" + domain) == []


@pytest.mark.parametrize("domain", ["university.edu", "example.org.attacker.com",
                                   "notexample.net", "test.com"])
def test_real_email_domains_fail(domain):
    assert "non-noreply-email" in publish_module().sensitive_rules("person@" + domain)


def test_hash_allowlist_is_exact_and_expires(tmp_path):
    module = publish_module()
    payload = b"reviewed pattern definition"
    entry = {"path": "reviewed.py", "check": "credential-literal",
             "reason": "Definition of the redaction pattern, reviewed by security",
             "sha256": hashlib.sha256(payload).hexdigest()}
    (tmp_path / "configs").mkdir()
    (tmp_path / "configs/publish_allowlist.yaml").write_text(yaml.safe_dump([entry]))
    records = module.load_allowlist(tmp_path)
    assert module.allowed_text_check(records, "reviewed.py", entry["check"], payload)
    assert not module.allowed_text_check(records, "reviewed.py", entry["check"], payload + b"changed")
    assert not module.allowed_text_check(records, "other.py", entry["check"], payload)
    assert not module.allowed_text_check(records, "reviewed.py", "authorization-literal", payload)


def test_hash_allowlist_controls_check_result(tmp_path, monkeypatch, capsys):
    module = publish_module()
    path = tmp_path / "reviewed.py"
    payload = ("private" + "_key").encode()
    path.write_bytes(payload)
    (tmp_path / "configs").mkdir()
    (tmp_path / "configs/publish_allowlist.yaml").write_text(yaml.safe_dump([
        {"path": "reviewed.py", "check": "credential-literal", "reason": "Pattern definition",
         "sha256": hashlib.sha256(payload).hexdigest()}]))

    def fake_command(root, args):
        if args[:2] == ["git", "ls-files"]:
            output = b"reviewed.py\0"
        elif args[:2] == ["git", "config"]:
            output = b"public@users.noreply.github.com"
        else:
            output = b""
        return subprocess.CompletedProcess(args, 0, output, b"")

    monkeypatch.setattr(module, "command", fake_command)
    monkeypatch.setattr(module.shutil, "which", lambda _: "gitleaks")
    assert module.check(tmp_path) == 0
    path.write_bytes(payload + b" changed")
    assert module.check(tmp_path) == 1
    assert 'path="reviewed.py"' in capsys.readouterr().out


def test_gitleaks_exceptions_require_match_and_path(tmp_path):
    assert shutil.which("gitleaks"), "gitleaks is required to verify publication safety"
    root = Path(__file__).resolve().parents[1]
    assert root not in tmp_path.resolve().parents
    nist = {"hashkey": "NIST-MATDB-" + "a1b2c3d4" * 4}
    crossref = {"key": "2026090315" + "561735100_cit48"}
    marker = {"api_key": "AIza" + "SyB9kQ2mN7vR4xT8wZ3pL6cD1fH5jG0sA9e"}
    files = {
        "data/raw/nist_isodb/public.json": nist,
        "sources/metadata/S2.crossref.json": crossref,
        "elsewhere/nist.json": nist,
        "elsewhere/data/raw/nist_isodb/nested.json": nist,
        "elsewhere/crossref.json": crossref,
        "data/raw/nist_isodb/secret.json": marker,
        "sources/metadata/secret.crossref.json": marker,
    }
    for relative, data in files.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data))
    report = tmp_path / "report.json"
    result = subprocess.run([
        "gitleaks", "detect", "--no-git", "--source", ".",
        "--config", str(root / ".gitleaks.toml"), "--redact", "--no-banner",
        "--report-format=json", "--report-path", str(report),
    ], cwd=tmp_path, capture_output=True)
    assert result.returncode == 1
    findings = json.loads(report.read_text())
    found = {Path(item["File"]).relative_to(tmp_path).as_posix()
             if Path(item["File"]).is_absolute() else item["File"] for item in findings}
    assert found == set(files) - {"data/raw/nist_isodb/public.json", "sources/metadata/S2.crossref.json"}
