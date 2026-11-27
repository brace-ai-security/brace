"""Characterisation goldens for the action plan and topology tools (migration guard).

Each case runs a command-line tool on a checked-in example and compares the bytes it writes
with tests/fixtures/char_golden/. A change here must be reviewed and explained.
Regenerate: BRACE_REGEN_GOLDEN=1 pytest tests/test_char_golden.py -p no:xdist
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

TOOL_DIR = Path(__file__).resolve().parent.parent
ROOT = TOOL_DIR.parent.parent
GOLDEN = TOOL_DIR / "tests" / "fixtures" / "char_golden"
BILL = TOOL_DIR / "examples" / "billing-agent"
TRAVEL = TOOL_DIR / "examples" / "travel-agent"
REGEN = os.environ.get("BRACE_REGEN_GOLDEN") == "1"


def tool(name: str) -> list[str]:
    return [sys.executable, str(TOOL_DIR / name)]


def run(cmd, cwd):
    p = subprocess.run([str(c) for c in cmd], cwd=cwd, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def compare(name: str, data: bytes):
    path = GOLDEN / name
    if REGEN:
        path.write_bytes(data)
    assert path.exists(), f"missing golden {name}; regenerate with BRACE_REGEN_GOLDEN=1"
    assert data == path.read_bytes(), f"{name} differs from its golden"


def test_action_plan_outputs(tmp_path):
    code, _, err = run([*tool("action_plan.py"), BILL / "sample-findings.json", BILL / "topology.cdx.json",
                        "-o", "plan.md", "--csv", "actions.csv", "--json", "plan.json", "--sarif", "plan.sarif",
                        "--html", "plan.html", "--strict"], tmp_path)
    assert code == 0, err
    for out in ("plan.md", "actions.csv", "plan.json", "plan.sarif", "plan.html"):
        compare(f"billing.{out}", (tmp_path / out).read_bytes())


@pytest.mark.parametrize("ex", [BILL, TRAVEL], ids=["billing", "travel"])
def test_topology_mermaid_and_report(tmp_path, ex):
    code, _, err = run([*tool("topology.py"), "mermaid", ex / "topology.cdx.json", "-o", "map.mmd"], tmp_path)
    assert code == 0, err
    compare(f"{ex.name}.mmd", (tmp_path / "map.mmd").read_bytes())
    code, _, err = run([*tool("topology.py"), "report", ex / "topology.cdx.json", "--findings",
                        ex / "sample-findings.json", "-o", "report.html"], tmp_path)
    assert code == 0, err
    compare(f"{ex.name}.report.html", (tmp_path / "report.html").read_bytes())
    code, out, err = run([*tool("topology.py"), "validate", ex / "topology.cdx.json"], tmp_path)
    assert code == 0, err


def test_topology_build_travel(tmp_path):
    repo = tmp_path / "repo"
    shutil.copytree(TRAVEL / "repo", repo)
    code, _, err = run([*tool("topology.py"), "build", "repo", "-o", "bom.json", "--agent-config",
                        "repo/config/agent.yaml", "--overlay", TRAVEL / "brace-topology.overlay.json"], tmp_path)
    assert code == 0, err
    compare("travel.build.cdx.json", (tmp_path / "bom.json").read_bytes())


def test_exit_codes(tmp_path):
    """Exit codes of the three command lines as they are today (usage error 2; unreadable input
    1 for the plan and topology tools; a folder with no record 2 for the record checker)."""
    (tmp_path / "bad.json").write_text("{not json")
    cases = [
        (["action_plan.py"], 2),
        (["action_plan.py", "missing.json", "missing.cdx.json", "-o", "x.md"], 1),
        (["topology.py"], 2),
        (["topology.py", "validate", "bad.json"], 1),
        (["topology.py", "validate", "missing.json"], 1),
        (["brace.py"], 2),
        (["brace.py", "nosuch"], 2),
        (["brace.py", "check", "--dir", "."], 2),
    ]
    for argv, want in cases:
        assert run([*tool(argv[0]), *argv[1:]], tmp_path)[0] == want, argv
