"""Run the composite GitHub Action's shell steps locally, the way the runner would."""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

TOOL_DIR = Path(__file__).resolve().parents[2] / "tools" / "brace"
ROOT = TOOL_DIR.parent.parent
ACTION = ROOT / "actions" / "plan" / "action.yml"
EXAMPLE = TOOL_DIR / "examples" / "billing-agent"
pytest.importorskip("jsonschema")


def _deps_importable() -> bool:
    import importlib.util
    return all(importlib.util.find_spec(m) for m in ("yaml", "jsonschema"))


def evaluate(expr: str, inputs: dict, outputs: dict) -> str:
    expr = expr.strip()
    if expr == "github.action_path":
        return str(ACTION.parent)
    m = re.fullmatch(r"inputs\.([\w-]+)", expr)
    if m:
        return inputs[m.group(1)]
    m = re.fullmatch(r"steps\.(\w+)\.outputs\.(\w+)", expr)
    if m:
        return outputs.get(m.group(1), {}).get(m.group(2), "")
    raise AssertionError(f"unsupported expression {expr}")


def sub(text: str, inputs: dict, outputs: dict) -> str:
    return re.sub(r"\$\{\{(.*?)\}\}", lambda m: evaluate(m.group(1), inputs, outputs), text)


def run_action(workdir: Path, **overrides) -> tuple[list[tuple[str, int]], dict, str]:
    spec = yaml.safe_load(ACTION.read_text())
    inputs = {k: str(v.get("default", "")) for k, v in spec["inputs"].items()}
    inputs.update({k.replace("_", "-"): v for k, v in overrides.items()})
    outputs, results = {}, []
    summary = workdir / "summary.md"
    for step in spec["runs"]["steps"]:
        if "run" not in step:
            continue  # setup-python, upload-artifact, upload-sarif need the hosted runner
        cond = step.get("if", "")
        m = re.fullmatch(r"inputs\.([\w-]+) == '(\w+)'", cond)
        if m and inputs[m.group(1)] != m.group(2):
            continue
        if step["name"] == "Install BRACE dependencies" and _deps_importable():
            # The step builds a venv and pip-installs hash-pinned wheels from PyPI; here the same
            # dependencies are already importable, so the test interpreter stands in for the venv.
            assert "--require-hashes" in step["run"] and "requirements.txt" in step["run"], step["run"]
            outputs["setup"] = {"python": sys.executable}
            results.append((step["name"], 0))
            continue
        out_file = workdir / f"out-{len(results)}.txt"
        out_file.write_text("")
        env = {**os.environ, "GITHUB_OUTPUT": str(out_file), "GITHUB_STEP_SUMMARY": str(summary),
               "GITHUB_ACTION_PATH": str(ACTION.parent),
               "PATH": f"{Path(sys.executable).parent}:{os.environ['PATH']}"}
        env.update({k: sub(str(v), inputs, outputs) for k, v in (step.get("env") or {}).items()})
        proc = subprocess.run(["bash", "-e", "-c", step["run"]], cwd=workdir, env=env,
                              capture_output=True, text=True)
        results.append((step["name"], proc.returncode))
        if step.get("id"):
            outputs[step["id"]] = dict(line.split("=", 1) for line in out_file.read_text().splitlines() if "=" in line)
        if proc.returncode and step["name"] != "Apply the gate":
            raise AssertionError(f"{step['name']} failed: {proc.stderr}")
    return results, outputs, summary.read_text() if summary.exists() else ""


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "billing-agent"
    shutil.copytree(ROOT / "evals/fixtures/billing-agent", r)
    shutil.copy(EXAMPLE / "brace-topology.overlay.json", r)
    shutil.copy(EXAMPLE / "sample-findings.json", r / "brace-findings.json")
    subprocess.run([sys.executable, str(ROOT / "skills/brace-review/scripts/review_coverage.py"), "inventory", str(r)],
                   check=True, capture_output=True)
    return r


def test_action_builds_map_writes_outputs_and_fails_on_g1(repo):
    results, outputs, summary = run_action(repo, build_topology="true", agent_config="config/agent.yaml")
    assert dict(results)["Apply the gate"] == 1  # the sample has Blocker gaps
    assert outputs["plan"]["exit_code"] == "3"
    assert outputs["plan"]["blocker_gaps"] == "4" and outputs["plan"]["actions"] == "8"
    assert outputs["record"]["status"] == "missing"
    out = repo / "brace-report"
    for name in ("brace-action-plan.md", "brace-action-plan.html", "brace-action-plan.json", "brace.sarif",
                 "brace-actions.csv"):
        assert (out / name).is_file(), name
    sarif = json.loads((out / "brace.sarif").read_text())
    assert sarif["version"] == "2.1.0" and len(sarif["runs"][0]["results"]) == 8
    assert "```mermaid" in summary and "Map record: missing" in summary


def test_action_passes_with_fail_on_none_and_drift_fail_blocks(repo):
    results, outputs, _ = run_action(repo, build_topology="true", agent_config="config/agent.yaml", fail_on="none")
    assert dict(results)["Apply the gate"] == 0
    results, outputs, _ = run_action(repo, build_topology="true", agent_config="config/agent.yaml",
                                     fail_on="none", record_drift="fail")
    assert dict(results)["Apply the gate"] == 1 and outputs["record"]["status"] == "missing"


def test_inputs_never_interpolated_into_shell():
    spec = yaml.safe_load(ACTION.read_text())
    for step in spec["runs"]["steps"]:
        assert "${{" not in step.get("run", ""), f"{step['name']} puts an expression straight into the script"


def test_action_is_pinned_isolated_and_stops_workflow_commands():
    spec = yaml.safe_load(ACTION.read_text())
    steps = spec["runs"]["steps"]
    for step in steps:
        if "uses" in step:
            assert re.fullmatch(r"[\w.\-]+/[\w.\-/]+@[0-9a-f]{40}", step["uses"]), step["uses"]
    runs = [s.get("run", "") for s in steps]
    for name in ("Build the map", "Write the action plan", "Compare the map with the record"):
        run = next(s["run"] for s in steps if s.get("name") == name)
        assert '-I "$GITHUB_ACTION_PATH/brace_run.py"' in run and "::stop-commands::" in run, name
    assert not any("python -" in r or "<<" in r for r in runs), "no inline Python reading workspace files"
    req = (ACTION.parent / "requirements.txt").read_text()
    pins = [l for l in req.splitlines() if l and not l.startswith((" ", "#"))]
    assert pins and all("==" in l for l in pins) and req.count("--hash=sha256:") >= len(pins)


def test_launcher_ignores_a_planted_module(tmp_path):
    (tmp_path / "json.py").write_text("raise SystemExit('PWNED')\n")
    (tmp_path / "brace_tools").mkdir()
    (tmp_path / "brace_tools" / "__init__.py").write_text("raise SystemExit('PWNED')\n")
    p = subprocess.run([sys.executable, "-I", str(ACTION.parent / "brace_run.py"), "--version"], cwd=tmp_path,
                       capture_output=True, text=True)
    assert p.returncode == 0 and "PWNED" not in p.stdout + p.stderr
