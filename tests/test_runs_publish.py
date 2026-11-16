import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

from pet2mof import runs


@pytest.fixture
def fake_git(monkeypatch):
    original = subprocess.run
    state = {"dirty": False}
    def execute(command, **kwargs):
        if command[:2] == ["git", "status"]:
            return subprocess.CompletedProcess(command, 0, b"?? changed.py\n" if state["dirty"] else b"")
        if command[:2] == ["git", "rev-parse"]:
            return subprocess.CompletedProcess(command, 0, "a" * 40 + "\n")
        return original(command, **kwargs)
    monkeypatch.setattr(runs.subprocess, "run", execute)
    return state


def execute_run(tmp_path, command, **kwargs):
    return runs.run_command(tmp_path, name="test", purpose="offline verification", hypothesis="test fixture",
                            command=command, **kwargs)


def test_run_clean_inputs_outputs_and_failure(tmp_path, fake_git):
    (tmp_path / "input.txt").write_text("input")
    path, passport = execute_run(tmp_path, [sys.executable, "-c", "from pathlib import Path; Path('out.txt').write_text('output')"],
                                 inputs=["input.txt"], outputs=["out.txt"], parameters={"temperature": {"value": 298, "unit": "K"}}, seed=1)
    assert passport["status"] == "completed" and passport["exit_code"] == 0
    assert passport["commit_sha"] == "a" * 40
    assert len(passport["inputs"][0]["sha256"]) == len(passport["outputs"][0]["sha256"]) == 64
    assert json.loads(path.read_text())["seed"] == 1
    assert "-aaaaaaaa-test" in passport["run_id"]
    _, failed = execute_run(tmp_path, [sys.executable, "-c", "raise SystemExit(7)"])
    assert failed["status"] == "failed" and failed["exit_code"] == 7
    _, missing = execute_run(tmp_path, ["./nonexistent-executable"])
    assert missing["status"] == "failed" and missing["exit_code"] == 127


def test_run_dirty_refusal_debug_and_missing_output(tmp_path, fake_git):
    fake_git["dirty"] = True
    with pytest.raises(RuntimeError, match="dirty tree"):
        execute_run(tmp_path, [sys.executable, "-c", "pass"])
    assert not (tmp_path / "runs").exists()
    _, debug = execute_run(tmp_path, [sys.executable, "-c", "pass"], allow_dirty=True)
    assert debug["status"] == "debug"
    fake_git["dirty"] = False
    _, missing = execute_run(tmp_path, [sys.executable, "-c", "pass"], outputs=["missing"])
    assert missing["status"] == "failed" and missing["exit_code"] == 1


def test_run_rejects_paths_and_redacts_command(tmp_path, fake_git):
    for inputs in (["../outside"], [".env"], ["private/example"]):
        with pytest.raises(ValueError):
            execute_run(tmp_path, [sys.executable, "-c", "pass"], inputs=inputs)
    marker = "TESTSECRET-example"
    assert marker not in str(runs._safe_command(["tool", "--api-key", marker, "--token=" + marker]))
    with pytest.raises(ValueError):
        execute_run(tmp_path, [sys.executable, "-c", "pass"], parameters={"temperature": 298})


def publish_module():
    path = Path(__file__).resolve().parents[1] / "scripts/publish_check.py"
    spec = importlib.util.spec_from_file_location("publish_check", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_publication_rules():
    module = publish_module()
    assert "absolute-user-path" in module.sensitive_rules("/" + "Users/owner/file")
    assert "non-noreply-email" in module.sensitive_rules("person" + "@real-domain.edu")
    assert module.sensitive_rules("1+test" + "@users.noreply.github.com") == []
    assert "authorization-literal" in module.sensitive_rules("Bearer" + " " + "example")
    assert "credential-literal" in module.sensitive_rules("private" + "_key")


def test_publish_failure_output_has_no_matched_values(publication_repo, capsys):
    root, module = publication_repo
    (root / "example.py").write_text("Bearer" + " TESTSECRET-should-never-print")
    subprocess.run(["git", "add", "example.py"], cwd=root, check=True)
    assert module.check(root) == 1
    output = capsys.readouterr().out
    assert "TESTSECRET-should-never-print" not in output
    assert "FAIL public-text:authorization-literal" in output
    assert 'path="example.py"' in output


def test_run_id_substitution_matches_actual_passport(tmp_path,fake_git):
    _,passport=execute_run(tmp_path,[sys.executable,'-c',"from pathlib import Path; import sys; Path('id.txt').write_text(sys.argv[1])",'{run_id}'],outputs=['id.txt'])
    assert (tmp_path/'id.txt').read_text()==passport['run_id']
