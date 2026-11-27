"""examples/policy/rego: OPA/Conftest policies over the scanner's JSON report.

The example inputs are checked against report-1.schema.json everywhere. The policies run only
when `opa` or `conftest` is installed (set OPA or CONFTEST to a binary off PATH); nothing is
downloaded.
"""
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
POLICY = ROOT / "examples" / "policy"
REGO = POLICY / "rego"
INPUTS = POLICY / "inputs"
SCHEMA = ROOT / "src/open_agent_security/report/schema/report-1.schema.json"


def tool(name):
    return os.environ.get(name.upper()) or shutil.which(name)


def test_policies_and_readme_exist():
    names = {p.name for p in REGO.glob("*.rego")}
    assert {"no_critical.rego", "unpinned_mcp.rego", "suppression_reason.rego", "complete_scan.rego",
            "policy_test.rego"} <= names
    assert "conftest test" in (POLICY / "README.md").read_text() and "opa eval" in (POLICY / "README.md").read_text()


@pytest.mark.parametrize("name", ["pass.json", "fail.json"])
def test_example_inputs_match_the_report_schema(name):
    jsonschema = pytest.importorskip("jsonschema")
    jsonschema.Draft202012Validator(json.loads(SCHEMA.read_text())).validate(json.loads((INPUTS / name).read_text()))


def opa_deny(opa, name, data=True):
    args = [opa, "eval", "--format", "json", "-d", str(REGO), "-i", str(INPUTS / name)]
    args += ["-d", str(INPUTS / "approved.json")] if data else []
    r = subprocess.run(args + ["data.main.deny"], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)["result"][0]["expressions"][0]["value"]


def test_opa_unit_tests_and_examples():
    opa = tool("opa")
    if not opa:
        pytest.skip("opa not installed")
    r = subprocess.run([opa, "test", str(REGO)], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
    assert opa_deny(opa, "pass.json") == []
    assert len(opa_deny(opa, "pass.json", data=False)) == 1  # local-dev-server is unpinned and not approved
    fail = opa_deny(opa, "fail.json")
    assert any("critical finding AP03" in m for m in fail)
    assert any('"docs"' in m for m in fail) and not any('"local-dev-server"' in m for m in fail)
    assert any("without a written reason" in m for m in fail)


def test_conftest_examples():
    conftest = tool("conftest")
    if not conftest:
        pytest.skip("conftest not installed")
    base = [conftest, "test", "-p", str(REGO), "--data", str(INPUTS / "approved.json")]
    ok = subprocess.run(base + [str(INPUTS / "pass.json")], capture_output=True, text=True, timeout=60)
    assert ok.returncode == 0, ok.stdout + ok.stderr
    bad = subprocess.run(base + [str(INPUTS / "fail.json")], capture_output=True, text=True, timeout=60)
    assert bad.returncode == 1 and "AP03" in bad.stdout
