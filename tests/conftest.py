"""Shared pytest configuration: src on path, network forbidden in tests."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import socket

import pytest


def pytest_configure(config):
    # --basetemp (pyproject) lives under .uv-cache/, which a fresh clone lacks.
    basetemp = config.getoption("basetemp")
    if basetemp:
        Path(config.rootpath, basetemp).parent.mkdir(parents=True, exist_ok=True)


@pytest.fixture(autouse=True)
def forbid_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("network forbidden in tests")
    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(socket, "getaddrinfo", denied)


@pytest.fixture
def pdf(tmp_path):
    import pymupdf
    path = tmp_path / "input.pdf"
    with pymupdf.open() as document:
        for text in ("First page: 12.5 mmol/g", "Second page: 0.2 bar", "Private unselected page"):
            page = document.new_page()
            page.insert_text((72, 72), text)
        document.save(path)
    return path


@pytest.fixture
def publication_repo(tmp_path, monkeypatch):
    run_git(tmp_path, "init", "-b", "main")
    run_git(tmp_path, "config", "user.name", "Synthetic test")
    run_git(tmp_path, "config", "user.email", "fixture@users.noreply.github.com")
    (tmp_path / "public.txt").write_text("safe")
    (tmp_path / ".gitleaks.toml").write_text("[extend]\nuseDefault = true\n")
    run_git(tmp_path, "add", "public.txt", ".gitleaks.toml")
    run_git(tmp_path, "commit", "-m", "synthetic baseline")
    from test_runs_publish import publish_module
    import subprocess
    module = publish_module()
    original = module.command

    def command(root, args):
        if args[0] == "gitleaks":
            return subprocess.CompletedProcess(args, 0, b"", b"")
        return original(root, args)

    monkeypatch.setattr(module, "command", command)
    monkeypatch.setattr(module.shutil, "which", lambda _: "gitleaks")
    return tmp_path, module


def run_git(root, *args):
    import subprocess
    return subprocess.run(["git", *args], cwd=root, capture_output=True, check=True).stdout


@pytest.fixture
def repo(publication_repo):
    return publication_repo
