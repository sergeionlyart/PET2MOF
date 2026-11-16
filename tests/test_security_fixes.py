"""T008 regressions: synthetic fixtures, offline providers and disposable Git repos."""

import hashlib
import json
import multiprocessing
import os
import subprocess
import sys
import types
from pathlib import Path

import pytest
import yaml

from pet2mof.ocr import adapter, local
from pet2mof.ocr.config import Config
from pet2mof.ocr.ledger import BudgetStop, Ledger
from test_ocr import configure, fake_requests
from test_runs_publish import publish_module


@pytest.mark.ocr
@pytest.mark.parametrize("quote", ["'", '"'])
def test_t008_01_foreign_multiline_cannot_enable_ocr(tmp_path, quote):
    configure(tmp_path)
    settings = (tmp_path / ".env").read_text()
    (tmp_path / ".env").write_text("OPENAI_API_KEY=" + quote + "TESTSECRET-foreign\n" + settings + "\n" + quote)
    config = Config(tmp_path)
    assert not config.readiness()["external_allowed"]
    assert not config._values


@pytest.mark.ocr
def test_t008_01_supported_grammar(tmp_path):
    configure(tmp_path)
    settings = (tmp_path / ".env").read_text().splitlines()
    (tmp_path / ".env").write_text("\ufeff# comment\n" + "\n".join(
        "export " + line.split("=", 1)[0] + "='" + line.split("=", 1)[1] + "' # comment"
        for line in settings))
    assert Config(tmp_path).readiness()["external_allowed"]


@pytest.mark.ocr
def test_t008_01_quotes_comments_and_own_multiline(tmp_path):
    configure(tmp_path)
    with (tmp_path / ".env").open("a") as stream:
        stream.write('\nOCR_PROVIDER=mistral # literal provider\n'
                     'MISTRAL_API_KEY="TESTSECRET-line1\nOCR_EXTERNAL_ENABLED=false\nline3" # comment\n'
                     'MISTRAL_OCR_MODEL="fixed-\\u0032\\u0030\\u0032\\u0036"\n')
    config = Config(tmp_path)
    assert config.readiness()["external_allowed"]
    assert config.value("MISTRAL_API_KEY") == "TESTSECRET-line1\nOCR_EXTERNAL_ENABLED=false\nline3"
    assert config.value("MISTRAL_OCR_MODEL") == "fixed-2026"


@pytest.mark.ocr
@pytest.mark.parametrize("suffix", ['FOREIGN="unfinished', 'FOREIGN="ok" trailing',
    'FOREIGN=$(echo ignored)', 'FOREIGN=${OTHER}', 'not an assignment',
    'export FOREIGN', 'FOREIGN=value; command'])
def test_t008_01_unsupported_fails_closed(tmp_path, suffix):
    configure(tmp_path)
    with (tmp_path / ".env").open("a") as stream:
        stream.write("\n" + suffix)
    status = Config(tmp_path).readiness()
    assert status["external_allowed"] is False
    assert status["reason"] == "env_syntax_unsupported"


def git(root, *args):
    return subprocess.run(["git", *args], cwd=root, capture_output=True, check=True).stdout


@pytest.mark.parametrize("kind", ["path", "email", "authorization", "credential", "notebook"])
def test_t008_02_staged_payload_cannot_hide_in_worktree(repo, capsys, kind):
    root, module = repo
    payload = {"path": "/" + "Users/synthetic-owner/file", "email": "test" + "@university.edu",
               "authorization": "Bearer" + " TESTSECRET-staged", "credential": "private" + "_key",
               "notebook": json.dumps({"cells": [{"outputs": ["synthetic"], "execution_count": 1}]})}[kind]
    name = "item.ipynb" if kind == "notebook" else "item.txt"
    (root / name).write_text(payload)
    git(root, "add", name)
    (root / name).write_text('{"cells": []}' if kind == "notebook" else "safe")
    assert module.check(root) == 1
    output = capsys.readouterr().out
    rule = {"path": "public-text:absolute-user-path", "email": "public-text:non-noreply-email",
            "authorization": "public-text:authorization-literal", "credential": "public-text:credential-literal",
            "notebook": "notebooks-without-outputs"}[kind]
    assert "FAIL " + rule in output
    assert "synthetic-owner" not in output


def test_t008_02_allowlist_and_digest_use_index(repo, capsys):
    root, module = repo
    payload = ("private" + "_key").encode()
    (root / "public.txt").write_bytes(payload)
    (root / "configs").mkdir()
    allow = root / "configs/publish_allowlist.yaml"
    allow.write_text(yaml.safe_dump([dict(path="public.txt", check="credential-literal",
        reason="Synthetic review", sha256=hashlib.sha256(payload).hexdigest())]))
    git(root, "add", "public.txt", "configs/publish_allowlist.yaml")
    (root / "public.txt").write_text("different working text")
    allow.write_text("invalid working YAML: [")
    tree = git(root, "write-tree").decode().strip()
    assert module.check(root) == 0
    assert "tree=" + tree in capsys.readouterr().out
    # Now stage changed bytes while retaining the reviewed working bytes.
    git(root, "add", "public.txt")
    (root / "public.txt").write_bytes(payload)
    assert module.check(root) == 1
    assert "FAIL publish-allowlist-current" in capsys.readouterr().out


def test_t008_02_index_change_invalidates_result(repo, monkeypatch, capsys):
    root, module = repo
    original = module.command
    changed = False

    def command(scan_root, args):
        nonlocal changed
        if args[0] == "gitleaks" and not changed:
            changed = True
            (root / "public.txt").write_text("changed during check")
            git(root, "add", "public.txt")
        return original(scan_root, args)

    monkeypatch.setattr(module, "command", command)
    assert module.check(root) == 1
    assert "FAIL git-index-unchanged" in capsys.readouterr().out


@pytest.mark.parametrize("executable", [False, True])
def test_t008_02_snapshot_uses_index_bytes_and_modes(repo, monkeypatch, executable):
    root, module = repo
    mode = 0o755 if executable else 0o644
    (root / "public.txt").chmod(mode)
    git(root, "add", "public.txt")
    if not executable:
        (root / "public.txt").write_text("working bytes must not enter snapshot")
    (root / "public.txt").chmod(0o644 if executable else 0o755)
    inspected = []
    original = module.command

    def command(scan_root, args):
        if args[:2] == ["gitleaks", "detect"] and "--no-git" in args:
            copied = scan_root / "public.txt"
            assert copied.read_text() == "safe"
            assert copied.stat().st_mode & 0o777 == mode
            inspected.append(True)
        return original(scan_root, args)

    monkeypatch.setattr(module, "command", command)
    assert module.check(root) == 0
    assert inspected


FORBIDDEN = [".env.backup", ".envrc", "nested/.env.secret", "nested/settings.env",
    "private/session.txt", "secrets/notes.txt", ".secrets/notes.txt", ".local/file",
    ".agent_sessions/log", "nested/credentials-demo.json", "nested/auth.json",
    "nested/service_account-demo.json", "nested/application_default_credentials.json",
    "nested/key.pem", "key.key", "key.p12", "key.pfx", "data/raw/pdf/a.pdf",
    "data/raw/html/a.html", "data/raw/figures_full/a.png"]


@pytest.mark.parametrize("name", FORBIDDEN)
def test_t008_03_forbidden_index_paths(repo, name, capsys):
    root, module = repo
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("synthetic private text")
    git(root, "add", "-f", name)
    assert module.check(root) == 1
    assert "FAIL no-private-tracked-files" in capsys.readouterr().out


@pytest.mark.parametrize("ref", ["main", "tag", "HEAD"])
def test_t008_03_deleted_history_still_rejected(repo, ref, capsys):
    root, module = repo
    if ref != "main":
        git(root, "checkout", "-b", "candidate")
    (root / "private").mkdir()
    (root / "private/session.txt").write_text("synthetic private text")
    git(root, "add", "private/session.txt")
    git(root, "commit", "-m", "synthetic private history")
    if ref == "tag":
        git(root, "tag", "synthetic-release")
    git(root, "rm", "private/session.txt")
    git(root, "commit", "-m", "delete private file")
    if ref == "tag":
        git(root, "checkout", "main")
        git(root, "branch", "-D", "candidate")
    assert module.check(root) == 1
    assert "FAIL no-private-history-files" in capsys.readouterr().out


def test_t008_03_gitignore_matches_policy():
    module = publish_module()
    root = Path(__file__).resolve().parents[1]
    patterns = set((root / ".gitignore").read_text().splitlines())
    assert set(module.FORBIDDEN_PATTERNS) <= patterns
    secrets = (root / ".gitignore").read_text().split("# --- Python / tooling ---")[0]
    secret_patterns = {line for line in secrets.splitlines() if line and not line.startswith(("#", "!"))}
    assert secret_patterns == {pattern for pattern in module.FORBIDDEN_PATTERNS if not pattern.startswith("data/")}
    for name in FORBIDDEN:
        result = subprocess.run(["git", "check-ignore", "--no-index", "--", name], cwd=root, capture_output=True)
        assert result.returncode == 0, name
    assert not module.forbidden_path(".env.example")
    assert not module.forbidden_path("nested/.env.example")


@pytest.mark.parametrize("kind", ["parent", "dangling", "index-only"])
def test_t008_04_symlinks_rejected_without_reading_target(repo, tmp_path, kind, monkeypatch, capsys):
    root, module = repo
    (root / "docs").mkdir()
    path = root / "docs/item.txt"
    path.write_text("safe staged file")
    git(root, "add", "docs/item.txt")
    path.unlink()
    if kind == "parent":
        target = root / "outside"
        target.mkdir()
        (target / "item.txt").write_text("TESTSECRET-symlink-target")
        (root / "docs").rmdir()
        (root / "docs").symlink_to(target, target_is_directory=True)
    else:
        path.symlink_to(root / "nonexistent")
        if kind == "index-only":
            git(root, "add", "docs/item.txt")
            path.unlink()
            path.write_text("ordinary working file")
    original = Path.read_bytes

    def guarded(path):
        assert path != root / "docs/item.txt", "must read index blobs, never the working path"
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", guarded)
    assert module.check(root) == 1
    assert "FAIL public-files-readable-no-symlinks" in capsys.readouterr().out


@pytest.mark.ocr
@pytest.mark.parametrize("key,value", [("GOOGLE_CLOUD_PROJECT", "other-project"),
    ("GOOGLE_DOCUMENT_AI_LOCATION", "us"), ("GOOGLE_DOCUMENT_AI_PROCESSOR_ID", "other"),
    ("GOOGLE_DOCUMENT_AI_PROCESSOR_VERSION", "other-version")])
def test_t008_05_google_resource_changes_miss_cache(tmp_path, pdf, monkeypatch, key, value):
    settings = dict(OCR_PROVIDER="google_docai", GOOGLE_CLOUD_PROJECT="demo-project",
        GOOGLE_DOCUMENT_AI_LOCATION="eu", GOOGLE_DOCUMENT_AI_PROCESSOR_ID="demo",
        GOOGLE_DOCUMENT_AI_PROCESSOR_VERSION="fixed")
    monkeypatch.setattr(Config, "google_credentials", lambda self: object())
    cloud = types.ModuleType("google.cloud")
    cloud.documentai = object()
    monkeypatch.setitem(sys.modules, "google.cloud", cloud)
    calls = []

    def provider(config, payload):
        calls.append(config.value(key))
        return {"text": "synthetic " + str(len(calls))}, config.value("GOOGLE_DOCUMENT_AI_PROCESSOR_VERSION")

    monkeypatch.setattr(adapter, "_google", provider)
    configure(tmp_path, **settings)
    first = adapter.OCRAdapter(tmp_path).extract(pdf, [1], "external", purpose="test")
    configure(tmp_path, **(settings | {key: value}))
    client = adapter.OCRAdapter(tmp_path)
    second = client.extract(pdf, [1], "external", purpose="test")
    assert len(calls) == 2
    assert first["cache_key"] != second["cache_key"]
    assert client.extract(pdf, [1], "external", purpose="repeat")["cache_key"] == second["cache_key"]
    assert len(calls) == 2


def _concurrent_reservation(root, ready, result):
    ready.set()
    try:
        Ledger(root, budget="10", page_limit=10, price="0.1", provider="mistral").reserve(1)
        result.put("reserved")
    except BudgetStop:
        result.put("blocked")


@pytest.mark.ocr
def test_t008_06_auth_charge_blocks_concurrent_reservation(tmp_path, pdf, monkeypatch):
    configure(tmp_path)
    fake_requests(monkeypatch)
    monkeypatch.setattr(adapter, "_mistral", lambda *args: (_ for _ in ()).throw(adapter.AuthorizationError()))
    # At the first post-charge unlock, let a second process attempt to reserve.
    # The old confirm(); stop() pair deterministically lets it through here.
    original = adapter.Ledger._locked
    from contextlib import contextmanager
    observed = []

    @contextmanager
    def locked(book):
        with original(book) as state:
            yield state
            charged = any(a["status"] == "charged" for a in state["attempts"].values())
        if charged and not observed:
            observed.append(True)
            context = multiprocessing.get_context("spawn")
            ready, result = context.Event(), context.Queue()
            process = context.Process(target=_concurrent_reservation, args=(str(tmp_path), ready, result))
            process.start()
            try:
                assert ready.wait(10)
                assert result.get(timeout=10) == "blocked"
            finally:
                process.join(10)
                if process.is_alive():
                    process.terminate()
                    process.join()
            assert process.exitcode == 0

    monkeypatch.setattr(adapter.Ledger, "_locked", locked)
    with pytest.raises(adapter.AuthorizationError):
        adapter.OCRAdapter(tmp_path).extract(pdf, [1], "external", purpose="test")
    assert observed
    state = Ledger(tmp_path, budget="10", page_limit=10, price="0.1", provider="mistral").snapshot()
    assert state["blocked"] == "authorization"
    assert len(state["attempts"]) == 1


@pytest.mark.ocr
@pytest.mark.parametrize("method", ["pdftotext", "tesseract"])
def test_t008_07_local_children_get_minimal_environment(tmp_path, pdf, monkeypatch, method):
    monkeypatch.setenv("OPENAI_API_KEY", "TESTSECRET-parent-only")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "TESTSECRET-parent-path")
    monkeypatch.setenv("INJECTED_UNKNOWN", "TESTSECRET-parent-only")
    monkeypatch.setattr(local.shutil, "which", lambda name: "/synthetic/" + name)
    calls = []

    def run(args, **kwargs):
        calls.append(args)
        assert kwargs.get("env") is not None
        assert set(kwargs["env"]) <= {"PATH", "LANG", "LC_ALL", "SYSTEMROOT"}
        assert kwargs["env"] == {key: os.environ[key] for key in ("PATH", "LANG", "LC_ALL", "SYSTEMROOT") if key in os.environ}
        return subprocess.CompletedProcess(args, 0, b"synthetic output\n", b"")

    monkeypatch.setattr(local.subprocess, "run", run)
    local.extract_local(pdf, [1], method=method, workdir=tmp_path)
    assert len(calls) == 2


def test_t008_08_credential_ignore_patterns_agree():
    root = Path(__file__).resolve().parents[1]
    git_patterns = set((root / ".gitignore").read_text().splitlines())
    docker_patterns = set((root / ".dockerignore").read_text().splitlines())
    credentials = {pattern for pattern in git_patterns if pattern.endswith((".json", ".pem", ".key", ".p12", ".pfx"))}
    assert "**/application_default_credentials.json" in credentials
    assert credentials <= git_patterns
    assert credentials <= docker_patterns
    assert {pattern for pattern in docker_patterns if pattern.endswith((".json", ".pem", ".key", ".p12", ".pfx"))} == credentials
