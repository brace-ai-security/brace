"""Packaging and the GitHub Action: version, wheel, action.yml and tooling."""
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import venv
import zipfile
from pathlib import Path

import pytest
import yaml
from support import FLAG, ROOT, TOOL_DIR, write

import open_agent_security


def scan_step() -> dict:
    action = yaml.safe_load((ROOT / "action.yml").read_text(encoding="utf-8"))
    return next(s for s in action["runs"]["steps"] if s.get("id") == "scan")


def build_tool() -> list[str] | None:
    if shutil.which("uv"):
        return ["uv", "build", "--wheel", "--offline", "-o"]
    if importlib.util.find_spec("build") is None:
        return None
    return [sys.executable, "-m", "build", "--wheel", "--no-isolation", "-o"]


def build_leftovers() -> set[Path]:
    """What setuptools leaves in the source tree: build/ and *.egg-info."""
    return {*ROOT.glob("build"), *ROOT.glob("*.egg-info"), *(TOOL_DIR.glob("*.egg-info"))}


def test_package_version_is_single_sourced():
    text = (TOOL_DIR.parent.parent / "pyproject.toml").read_text()
    assert 'attr = "open_agent_security.__version__"' in text and open_agent_security.__version__


def test_action_yml_is_valid_and_hardened():
    yaml = pytest.importorskip("yaml")
    action = yaml.safe_load((ROOT / "action.yml").read_text(encoding="utf-8"))
    assert set(action["inputs"]) == {"path", "fail-on", "upload-sarif", "category", "python-version"}
    assert set(action["outputs"]) == {"findings", "sarif", "incomplete"}
    steps = action["runs"]["steps"]
    assert [s["id"] for s in steps if "id" in s] == ["scan"]
    for s in steps:
        if "uses" in s:
            assert re.fullmatch(r"[\w.\-]+/[\w.\-/]+@[0-9a-f]{40}", s["uses"]), s["uses"]
        if "run" in s:
            assert "${{" not in s["run"], "inputs must reach scripts through env, not ${{ }}"


def test_tooling_checks_the_cyclonedx_download():
    text = (ROOT / ".github/workflows/tooling.yml").read_text()
    assert re.search(r"CDX_SHA256: [0-9a-f]{64}", text) and "sha256sum -c" in text


def test_action_runs_built_in_rules_only():
    assert scan_step()["env"]["OPEN_AGENT_SECURITY_PLUGINS"] == ""


def test_action_exit_2_message_names_the_config_file():
    action = (ROOT / "action.yml").read_text(encoding="utf-8")
    assert "malformed .open-agent-security.toml" in action


def test_the_wheel_installs_and_runs(tmp_path):
    tool = build_tool()
    if tool is None:
        pytest.skip("no wheel build tool (uv or python -m build) is available")
    out = tmp_path / "dist"
    before = build_leftovers()
    try:
        p = subprocess.run([*tool, str(out), str(ROOT)], capture_output=True, timeout=300)
    finally:
        for left in build_leftovers() - before:
            shutil.rmtree(left, ignore_errors=True)
    if p.returncode != 0:
        pytest.skip("the wheel could not be built offline: " + p.stderr.decode("utf-8", "replace")[-300:])
    wheel = next(out.glob("*.whl"))
    venv.create(tmp_path / "venv", with_pip=True)
    bindir = tmp_path / "venv" / ("Scripts" if os.name == "nt" else "bin")
    p = subprocess.run([str(bindir / "python"), "-m", "pip", "install", "--no-index", "--no-deps", str(wheel)],
                       capture_output=True, timeout=300)
    assert p.returncode == 0, p.stderr.decode("utf-8", "replace")
    exe = str(bindir / "open-agent-security")
    assert subprocess.run([exe, "--version"], capture_output=True, timeout=60).returncode == 0
    write(tmp_path, "repo/run.sh", f"claude -p hi {FLAG}\n")
    p = subprocess.run([exe, str(tmp_path / "repo"), "--json", "--fail-on", "none"], capture_output=True, timeout=60)
    assert p.returncode == 0 and [f["rule"] for f in json.loads(p.stdout)["findings"]] == ["AP01"]
    gl, junit = tmp_path / "gl.json", tmp_path / "junit.xml"
    p = subprocess.run([exe, str(tmp_path / "repo"), "--fail-on", "none", "--output", f"gitlab-sast={gl}",
                        "--output", f"junit={junit}"], capture_output=True, timeout=60)
    assert p.returncode == 0 and json.loads(gl.read_text())["vulnerabilities"] and "<failure" in junit.read_text()
    with zipfile.ZipFile(wheel) as z:  # the JSON report schema ships in the wheel
        assert "open_agent_security/report/schema/report-1.schema.json" in z.namelist()


def test_python_311_is_required_everywhere():
    assert 'requires-python = ">=3.11"' in (ROOT / "pyproject.toml").read_text()
    action = (ROOT / "action.yml").read_text()
    assert "sys.version_info < (3, 11)" in action and "needs Python 3.11 or newer" in action


def test_pre_commit_hook_runs_the_whole_repository():
    hooks = yaml.safe_load((ROOT / ".pre-commit-hooks.yaml").read_text(encoding="utf-8"))
    assert hooks == [{"id": "open-agent-security", "name": "open-agent-security", "description": hooks[0]["description"],
                      "entry": "open-agent-security", "language": "python", "pass_filenames": False,
                      "always_run": True}]
