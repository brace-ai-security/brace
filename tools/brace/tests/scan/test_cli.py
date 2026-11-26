"""The command line: arguments, exit codes, output files and paths."""
import json
import os
import subprocess
import sys

from support import AGENT, FLAG, TOOL_DIR, rules, run, write

import open_agent_security


def test_clean_repo_has_no_findings(tmp_path):
    write(tmp_path, ".mcp.json", json.dumps({"mcpServers": {"docs": {"command": "npx", "args": ["-y", "docs-mcp@1.2.3"]}}}))
    write(tmp_path, "Dockerfile", "FROM python@sha256:abc AS base\nFROM base\n")
    assert rules(tmp_path) == []
    assert run(tmp_path, fail_on="low")[0] == 0


def test_paths_are_relative_to_working_directory(tmp_path):
    write(tmp_path, "sub/run.sh", "claude --dangerously-skip-permissions\n")
    sf = tmp_path / "r.sarif"
    run(tmp_path / "sub", cwd=tmp_path, sarif_path=str(sf))
    loc = json.loads(sf.read_text())["runs"][0]["results"][0]["locations"][0]["physicalLocation"]
    assert loc["artifactLocation"]["uri"] == "sub/run.sh"


def test_sarif_does_not_follow_symlink(tmp_path):
    victim = tmp_path / "victim.txt"
    victim.write_text("keep")
    link = tmp_path / "out.sarif"
    link.symlink_to(victim)
    assert run(tmp_path, sarif_path=str(link))[0] == 2
    assert victim.read_text() == "keep"


def test_fail_on_threshold(tmp_path):
    write(tmp_path, ".mcp.json", AGENT)
    write(tmp_path, "Dockerfile", "FROM python:3.12\n")
    assert run(tmp_path, fail_on="high")[0] == 0
    assert run(tmp_path, fail_on="low")[0] == 1


def test_unicode_output_on_narrow_console(tmp_path):
    write(tmp_path, "run.sh", "claude --dangerously-skip-permissions\n")
    env = dict(os.environ, PYTHONIOENCODING="cp1252")
    p = subprocess.run([sys.executable, "-I", str(TOOL_DIR / "scan.py"), str(tmp_path), "--fail-on", "none"],
                       capture_output=True, env=env)
    assert p.returncode == 0, p.stderr.decode(errors="replace")


def test_version_flag():
    p = subprocess.run([sys.executable, "-I", str(TOOL_DIR / "scan.py"), "--version"], capture_output=True, text=True)
    assert p.stdout.strip() == f"open-agent-security {open_agent_security.__version__}"


def test_write_error_is_exit_2(tmp_path):
    write(tmp_path, "run.sh", "echo\n")
    assert run(tmp_path, sarif_path=str(tmp_path / "missing" / "r.sarif"))[0] == 2


def test_brace_py_scan_help_matches():
    p = subprocess.run([sys.executable, "-I", str(TOOL_DIR / "brace.py"), "scan", "--help"], capture_output=True, text=True)
    assert "incomplete" in p.stdout


def test_brace_scan_survives_a_narrow_console_encoding(tmp_path):
    write(tmp_path, "агент.sh", f"claude -p hi {FLAG}\n")
    env = {**os.environ, "PYTHONIOENCODING": "cp1252"}  # without -I, which would ignore it
    env.pop("GITHUB_ACTIONS", None)
    p = subprocess.run([sys.executable, str(TOOL_DIR / "brace.py"), "scan", str(tmp_path), "--fail-on", "none"],
                       capture_output=True, env=env, timeout=60)
    assert p.returncode == 0, p.stderr.decode("utf-8", "replace")
