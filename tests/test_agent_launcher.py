"""Argument guards of scripts/agents/run_codex_task.sh (no Codex call: every case exits before launch)."""
import os
import pathlib
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "scripts" / "agents" / "run_codex_task.sh"


def run(*args, env_extra=None):
    env = {"PATH": os.environ["PATH"], "HOME": os.environ.get("HOME", "/tmp")}
    env.update(env_extra or {})
    return subprocess.run(["bash", str(LAUNCHER), *args], capture_output=True, text=True, env=env, cwd=ROOT)


@pytest.mark.parametrize("model", ["gpt-6.2-mini", "gpt-5.5", "gpt-6-sol", "gpt-6.2-terra"])
def test_unknown_models_refused(model):
    r = run("T", model, "low", "read-only", "off", "/dev/null", "/nonexistent")
    assert r.returncode == 2 and "model not allowed" in r.stderr


@pytest.mark.parametrize("model", ["gpt-6-astra", "gpt-6.1-sol"])
def test_legacy_models_need_explicit_flag(model):
    r = run("T", model, "low", "read-only", "off", "/dev/null", "/nonexistent")
    assert r.returncode == 2 and "PET2MOF_ALLOW_LEGACY_MODEL=1" in r.stderr


def test_ultra_refused_for_new_models():
    r = run("T", "gpt-6.2-astra", "ultra", "read-only", "off", "/dev/null", "/nonexistent")
    assert r.returncode == 2 and "effort not allowed" in r.stderr


def test_preamble_forbids_subagents_and_confirmation_waits():
    text = (ROOT / "scripts" / "agents" / "prompt_preamble.md").read_text(encoding="utf-8")
    assert "spawn_agent" in text and "подтверждения ждать не от кого" in text
