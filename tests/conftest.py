"""Shared pytest configuration: src on path, network forbidden in tests."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import socket

import pytest


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
