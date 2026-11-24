"""Prototype CycloneDX topology: build, validate and render one fixture."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

TOOL_DIR = Path(__file__).resolve().parent.parent
ROOT = TOOL_DIR.parent.parent
sys.path.insert(0, str(TOOL_DIR))

import topology  # noqa: E402

pytest.importorskip("jsonschema")
FIXTURE = ROOT / "evals" / "fixtures" / "billing-agent"


@pytest.fixture(scope="module")
def bom(tmp_path_factory):
    repo = tmp_path_factory.mktemp("billing") / "billing-agent"
    shutil.copytree(FIXTURE, repo)
    subprocess.run([sys.executable, str(ROOT / "skills/brace-review/scripts/review_coverage.py"),
                    "inventory", str(repo)], check=True, capture_output=True)
    return topology.build(repo, repo / "brace-inventory.json", repo / "config" / "agent.yaml")


def test_valid_against_cyclonedx_1_7(bom):
    assert bom["specVersion"] == "1.7"
    assert topology.validate(bom) == []


def test_declared_nodes(bom):
    svc = {s["bom-ref"]: s for s in bom["services"]}
    mcp = svc["mcp:accounting"]
    assert mcp["endpoints"] == ["https://accounting-mcp.internal.ledgerly.io/mcp"]
    assert mcp["authenticated"] is True
    assert {t["bom-ref"] for t in mcp["services"]} == {"mcp:accounting/get_customer", "mcp:accounting/list_payments"}
    assert "tool:issue_refund" in svc
    refs = {c["bom-ref"] for c in bom["components"]}
    assert {"unit:src/agent.py", "unit:src/drafter.py", "data:audit-log"} <= refs


def test_marked_incomplete_and_zone_unknown(bom):
    assert bom["compositions"][0]["aggregate"] == "incomplete"
    names = {p["name"]: p["value"] for p in bom["services"][0]["properties"]}
    assert names["brace:trust_zone"] == "unknown"
    assert "x-trust-boundary" not in bom["services"][0]


def test_no_secret_values(bom):
    text = json.dumps(bom)
    assert "Bearer" not in text and "${" not in text


def test_validate_rejects_bad_refs_and_types(bom):
    bad = json.loads(json.dumps(bom))
    bad["dependencies"].append({"ref": "missing"})
    bad["services"][0]["authenticated"] = "yes"
    errors = topology.validate(bad)
    assert any("unknown bom-ref missing" in e for e in errors)
    assert any(e.startswith("schema:") for e in errors)


def test_redact_args():
    assert topology.redact_args(["--token", "abc", "--region", "eu", "API_KEY=x"]) == [
        "--token", "<redacted>", "--region", "eu", "API_KEY=<redacted>"]


def test_mermaid_renders_every_node(bom):
    text = topology.mermaid(bom)
    assert text.startswith("flowchart LR")
    for name in ("billing-agent", "accounting", "issue_refund", "audit log"):
        assert name in text


def _overlay_repo(tmp_path):
    repo = tmp_path / "billing-agent"
    shutil.copytree(FIXTURE, repo)
    cfg = repo / "config/agent.yaml"  # test the overlay alone: drop the declared connections
    cfg.write_text(cfg.read_text().split("\n# What the agent is meant to reach")[0])
    subprocess.run([sys.executable, str(ROOT / "skills/brace-review/scripts/review_coverage.py"),
                    "inventory", str(repo)], check=True, capture_output=True)
    return repo


def _run(*args):
    return topology.main([str(a) for a in args])


def test_overlay_verifies_quotes_and_merges(tmp_path):
    repo = _overlay_repo(tmp_path)
    q = "psycopg.connect(self.dsn, row_factory=dict_row)"
    assert _run("add-node", repo, "--ref", "data:invoices-db", "--kind", "data_store",
                "--evidence", "src/tools/invoices.py:31", "--quote", "DROP TABLE") == 1
    assert _run("add-node", repo, "--ref", "data:invoices-db", "--kind", "data_store",
                "--evidence", "src/tools/invoices.py:31", "--quote", q) == 0
    assert _run("add-edge", repo, "--from", "tool:get_invoice", "--to", "data:invoices-db", "--label", "read",
                "--evidence", "src/tools/invoices.py:31", "--quote", "psycopg.connect") == 0
    assert _run("set-zone", repo, "--ref", "mcp:accounting", "--zone", "internal",
                "--evidence", ".mcp.json:5", "--quote", "accounting-mcp.internal") == 0
    bom = topology.build(repo, repo / "brace-inventory.json", repo / "config/agent.yaml",
                         repo / "brace-topology.overlay.json")
    assert topology.validate(bom) == [] and topology.stale_entries(bom) == []
    db = next(c for c in bom["components"] if c["bom-ref"] == "data:invoices-db")
    assert db["type"] == "data" and {"name": "brace:source", "value": "traced"} in db["properties"]
    assert next(s for s in bom["services"] if s["bom-ref"] == "mcp:accounting")["trustZone"] == "internal"
    assert "-->|\"read\"|" in topology.mermaid(bom)


def test_record_proposes_create_then_update_and_needs_apply(tmp_path):
    repo = _overlay_repo(tmp_path)
    rec = tmp_path / ".brace" / "topology.cdx.json"
    out = tmp_path / "t.cdx.json"
    assert _run("build", repo, "-o", out, "--agent-config", repo / "config/agent.yaml") == 0
    assert _run("record", out, "--record", rec) == 3 and not rec.exists()   # proposes create
    assert _run("record", out, "--record", rec, "--apply") == 0 and rec.exists()
    assert _run("record", out, "--record", rec) == 0                          # matches
    assert _run("add-node", repo, "--ref", "api:payments", "--kind", "external_api",
                "--evidence", "src/tools/payments.py:48", "--quote", 'self.base = pc["base_url"]') == 0
    assert _run("build", repo, "-o", out, "--agent-config", repo / "config/agent.yaml") == 0
    before = rec.read_text()
    assert _run("record", out, "--record", rec) == 3 and rec.read_text() == before  # proposes update
    assert any("+ node api:payments" in d for d in topology.compare(json.loads(before), json.loads(out.read_text())))
    assert _run("record", out, "--record", rec, "--apply") == 0 and rec.read_text() != before


def test_stale_overlay_blocks_apply(tmp_path):
    repo = _overlay_repo(tmp_path)
    assert _run("add-node", repo, "--ref", "data:invoices-db", "--kind", "data_store",
                "--evidence", "src/tools/invoices.py:31", "--quote", "psycopg.connect(self.dsn") == 0
    f = repo / "src/tools/invoices.py"
    f.write_text(f.read_text().replace("psycopg.connect(self.dsn", "psycopg.connect(dsn=self.dsn"))
    out = tmp_path / "t.cdx.json"
    assert _run("build", repo, "-o", out, "--agent-config", repo / "config/agent.yaml") == 0
    assert topology.stale_entries(json.loads(out.read_text()))
    assert _run("record", out, "--record", tmp_path / "rec.json", "--apply") == 1
    assert not (tmp_path / "rec.json").exists()


def test_overlay_node_matching_declared_part_merges(tmp_path):
    repo = _overlay_repo(tmp_path)
    assert _run("add-node", repo, "--ref", "tool:issue_refund", "--kind", "tool",
                "--evidence", "src/tools/payments.py:66", "--quote", "def issue_refund") == 0
    bom = topology.build(repo, repo / "brace-inventory.json", repo / "config/agent.yaml",
                         repo / "brace-topology.overlay.json")
    assert topology.validate(bom) == []
    node = next(x for x in bom["services"] if x["bom-ref"] == "tool:issue_refund")
    assert {"name": "brace:traced_evidence", "value": "src/tools/payments.py:66"} in node["properties"]


def test_tools_map_config(tmp_path):
    repo = tmp_path / "hr-agent"
    shutil.copytree(ROOT / "evals/fixtures/hr-agent", repo)
    bom = topology.build(repo, None, repo / "config/agent.yaml", None, repo / "config/tools.yaml")
    assert topology.validate(bom) == []
    refs = {x["bom-ref"] for x in bom["services"]}
    assert {"tool:file_leave_request", "tool:escalate_to_human", "tool:search_policies"} <= refs
