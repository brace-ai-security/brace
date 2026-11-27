"""Security map and action plan: joins findings with the topology."""
import csv
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

TOOL_DIR = Path(__file__).resolve().parent.parent
ROOT = TOOL_DIR.parent.parent
sys.path.insert(0, str(TOOL_DIR))
sys.path.insert(0, str(ROOT / "skills/brace-review/scripts"))

import action_plan  # noqa: E402
import topology  # noqa: E402
import validate_findings  # noqa: E402

pytest.importorskip("jsonschema")
EXAMPLE = TOOL_DIR / "examples" / "billing-agent"


@pytest.fixture(scope="module")
def example(tmp_path_factory):
    """Rebuild the shipped example from the fixture plus its recorded overlay."""
    repo = tmp_path_factory.mktemp("ex") / "billing-agent"
    shutil.copytree(ROOT / "evals/fixtures/billing-agent", repo)
    shutil.copy(EXAMPLE / "brace-topology.overlay.json", repo)
    subprocess.run([sys.executable, str(ROOT / "skills/brace-review/scripts/review_coverage.py"),
                    "inventory", str(repo)], check=True, capture_output=True)
    bom = topology.build(repo, repo / "brace-inventory.json", repo / "config/agent.yaml",
                         repo / "brace-topology.overlay.json")
    findings = json.loads((EXAMPLE / "sample-findings.json").read_text())
    return bom, findings


def test_example_overlay_is_current(example):
    bom, _ = example
    assert topology.validate(bom) == []
    assert topology.stale_entries(bom) == [], "overlay evidence no longer matches the fixture"


def test_shipped_example_matches_generator(example, tmp_path):
    bom, findings = example
    shipped = json.loads((EXAMPLE / "topology.cdx.json").read_text())
    assert topology.compare(shipped, bom) == [], "regenerate examples/billing-agent (see its README)"
    nodes = topology.all_nodes(bom)
    actions, problems = action_plan.actions_from(findings, nodes)
    assert (EXAMPLE / "action-plan.md").read_text() == action_plan.report(findings, bom, actions, problems)


def test_actions_ordered_with_lead_roles(example):
    bom, findings = example
    actions, problems = action_plan.actions_from(findings, topology.all_nodes(bom))
    assert problems == []
    assert [a["rating"] for a in actions][-1] == "needs_evidence"
    assert actions[0]["gate"] == "Blocker" and actions[0]["rating"] == "gap"
    assert all(a["lead_role"] and a["steps"] and a["done_when"] for a in actions)


def test_report_sections_and_map(example):
    bom, findings = example
    actions, problems = action_plan.actions_from(findings, topology.all_nodes(bom))
    text = action_plan.report(findings, bom, actions, problems)
    for heading in ("## 1. Map", "## 2. Connections that matter", "## 3. Action list",
                    "## 4. How to fix each one", "## 5. What this report does not show"):
        assert heading in text
    assert "linkStyle" in text and "class " in text and "B06" in text
    assert "| issue_refund | payments API | can change, send or delete things; can move money" in text
    assert "Assigned to" not in text and "_____" not in text


def test_csv_for_trackers(example, tmp_path):
    bom, findings = example
    nodes = topology.all_nodes(bom)
    actions, _ = action_plan.actions_from(findings, nodes)
    out = tmp_path / "a.csv"
    action_plan.write_csv(out, actions, nodes)
    rows = list(csv.DictReader(out.open()))
    assert len(rows) == len(actions) and "assigned_to" not in rows[0]
    assert rows[0]["steps"].startswith("1. ")


def test_problems_flag_unknown_refs_missing_steps_and_hard_words(example):
    bom, _ = example
    findings = {"findings": [
        {"item": "B05", "rating": "gap", "summary": "x", "next_step": "Fix it.", "lead_role": "agent_team",
         "components": ["tool:nope"]},
        {"item": "B06", "rating": "gap", "summary": "y", "lead_role": "agent_team", "fix": {"steps": [
            "Institutionalize comprehensive authorization verification methodologies, operationalizing "
            "organizational accountability considerations systematically."], "done_when": "Done."}},
    ]}
    actions, problems = action_plan.actions_from(findings, topology.all_nodes(bom))
    text = "\n".join(problems)
    assert "'tool:nope' is not in the topology" in text
    assert "B05: no plain fix steps" in text
    assert "B06 step 1: reading grade" in text
    assert actions[0]["steps"] == ["Fix it."] and not actions[0]["plain"]


def test_grade_ignores_code_names():
    assert action_plan.grade("Open `src/tools/payments_registry_configuration.py` and go to line 91.") <= 8
    assert action_plan.plain_problems("Delete the token from the file.") == []


def test_validator_checks_action_fields(example, tmp_path):
    bom, _ = example
    path = tmp_path / "t.json"
    path.write_text(json.dumps(bom))
    refs = validate_findings.topology_refs(path)
    ok = {"rating": "gap", "components": ["mcp:accounting"],
          "fix": {"steps": ["Delete the token."], "done_when": "No token is in the code.", "effort": "small"}}
    assert validate_findings.action_fields("B03", ok, refs) == []
    bad = {"rating": "likely_pass", "components": ["mcp:nope", ""], "fix": {"steps": [], "effort": "huge"}}
    errs = "\n".join(validate_findings.action_fields("B03", bad, refs))
    assert "components must be a list" in errs and "fix.steps" in errs and "fix.effort" in errs
    assert "not in the topology" in "\n".join(
        validate_findings.action_fields("B03", {"components": ["mcp:nope"]}, refs))
    assert "nothing to fix" in "\n".join(validate_findings.action_fields(
        "B03", {"rating": "na_candidate", "fix": {"steps": ["x"], "done_when": ""}}, None))


def test_validator_checks_coverage_row_components(example, tmp_path):
    bom, _ = example
    path = tmp_path / "t.json"
    path.write_text(json.dumps(bom))
    refs = validate_findings.topology_refs(path)
    f = {"checks": [{"id": "B05.2", "coverage": [{"subject": "refund", "component": "tool:issue_refund"}],
                     "deviations": [{"subject": "mail", "component": "api:nope"}]}]}
    errs = validate_findings.action_fields("B05", f, refs)
    assert errs == ["B05: B05.2 deviations component 'api:nope' is not in the topology"]


def test_reference_problems_checks_files_and_lines():
    repo = ROOT / "evals/fixtures/billing-agent"
    assert action_plan.reference_problems("Open `src/tools/payments.py` and go to line 91.", repo) == []
    assert action_plan.reference_problems("Edit `src/tools/payments.py` lines 90 to 93.", repo) == []
    errs = action_plan.reference_problems("Open `src/tools/payment.py` line 3.", repo)
    assert errs and errs[0].startswith("`src/tools/payment.py` is not a file in the repository")
    assert action_plan.reference_problems("Create a new file `tests/test_refund.py`.", repo) == []
    errs = action_plan.reference_problems("Open `src/tools/payments.py` at line 9999.", repo)
    assert errs and "past the end" in errs[0]


def test_fix_test_rendered_as_code_block(example):
    bom, _ = example
    findings = {"findings": [{"item": "B05", "rating": "gap", "summary": "x", "lead_role": "agent_team",
                              "fix": {"steps": ["Create the test below."], "done_when": "It passes.",
                                      "test": {"file": "tests/test_x.py", "code": "def test_x():\n    assert True\n",
                                               "run": "python -m pytest tests/test_x.py"}}}]}
    actions, problems = action_plan.actions_from(findings, topology.all_nodes(bom))
    text = action_plan.report(findings, bom, actions, problems)
    assert "```py\ndef test_x():" in text and "Run it with `python -m pytest tests/test_x.py`." in text
    assert validate_findings.action_fields("B05", findings["findings"][0], None) == []
    bad = {"rating": "gap", "fix": {"steps": ["x"], "test": {"code": 1}}}
    assert "fix.test" in "\n".join(validate_findings.action_fields("B05", bad, None))


def test_json_output_matches_schema_and_sarif_shape(example):
    import jsonschema
    bom, findings = example
    actions, problems = action_plan.actions_from(findings, topology.all_nodes(bom))
    data = action_plan.plan_data(findings, bom, actions, problems)
    jsonschema.validate(data, json.loads((ROOT / "src/brace_tools/data/schemas/action-plan.schema.json").read_text()))
    assert data["summary"]["blocker_gaps"] == 4 and data["summary"]["actions"] == 8
    s = action_plan.sarif(data)
    run = s["runs"][0]
    assert s["version"] == "2.1.0" and len(run["results"]) == 8
    b06 = next(r for r in run["results"] if r["ruleId"] == "B06")
    assert b06["level"] == "error" and "How to fix:" in b06["message"]["text"]
    assert b06["locations"][0]["physicalLocation"]["region"]["startLine"] == 73
    r02 = next(r for r in run["results"] if r["ruleId"] == "R02")
    assert r02["level"] == "note" and "locations" not in r02


def test_fail_on_levels(example, tmp_path):
    bom, findings = example
    f, t = tmp_path / "f.json", tmp_path / "t.json"
    f.write_text(json.dumps(findings))
    t.write_text(json.dumps(bom))
    base = [str(f), str(t), "-o", str(tmp_path / "p.md")]
    assert action_plan.main(base + ["--fail-on", "none"]) == 0
    assert action_plan.main(base + ["--fail-on", "blocker"]) == 3
    only_needs = {**findings, "findings": [x for x in findings["findings"] if x["rating"] == "needs_evidence"]}
    f.write_text(json.dumps(only_needs))
    assert action_plan.main(base + ["--fail-on", "gap"]) == 0
    assert action_plan.main(base + ["--fail-on", "any"]) == 3


def test_html_escapes_untrusted_text(example):
    import report_html
    bom, findings = example
    evil = json.loads(json.dumps(findings))
    evil["findings"][0]["fix"]["problem"] = "<script>alert(1)</script> and `<img src=x onerror=alert(2)>`"
    evil["repo"] = "\"><script>alert(3)</script>"
    actions, problems = action_plan.actions_from(evil, topology.all_nodes(bom))
    page = report_html.render(action_plan.plan_data(evil, bom, actions, problems), bom)
    assert "<script>alert" not in page and "<img src=x" not in page
    assert "&lt;script&gt;alert(1)" in page
    assert page.count("<script") == 1  # only the Mermaid loader
    assert "securityLevel:'strict'" in page


def test_validator_checks_optional_aivss():
    ok = {"aivss": {"score": 7.4, "version": "0.8", "vector": "AIVSS:0.8/example"}}
    assert validate_findings.action_fields("B05", ok, None) == []
    assert validate_findings.action_fields("B05", {}, None) == []  # never required
    for bad in ({"aivss": 7}, {"aivss": {"score": 11}}, {"aivss": {"score": True}},
                {"aivss": {"score": 5, "version": 8}}, {"aivss": {"score": 5, "extra": 1}}):
        assert any("aivss" in e for e in validate_findings.action_fields("B05", bad, None)), bad
