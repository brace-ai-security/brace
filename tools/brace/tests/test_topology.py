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
    assert "services" not in mcp  # MCP tools are top-level services, linked with `provides`
    dep = next(d for d in bom["dependencies"] if d["ref"] == "mcp:accounting")
    assert set(dep["provides"]) == {"mcp:accounting/get_customer", "mcp:accounting/list_payments"}
    assert {"mcp:accounting/get_customer", "mcp:accounting/list_payments"} <= set(svc)
    assert "tool:issue_refund" in svc
    refs = {c["bom-ref"] for c in bom["components"]}
    assert {"unit:src/agent.py", "unit:src/drafter.py", "data:audit-log"} <= refs


def test_marked_incomplete_and_zone_unknown(bom):
    assert bom["compositions"][0]["aggregate"] == "incomplete"
    assert "agent" not in bom["compositions"][0]["assemblies"]
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


def test_provides_is_checked(bom):
    bad = json.loads(json.dumps(bom))
    bad["dependencies"].append({"ref": "tool:issue_refund", "provides": ["mcp:accounting/get_customer"]})
    assert any("only an MCP server provides" in e for e in topology.validate(bad))
    bad["dependencies"].append({"ref": "mcp:accounting", "provides": ["mcp:nope"]})
    assert any("unknown bom-ref mcp:nope" in e for e in topology.validate(bad))


def _working_bom(nodes: dict, edges: list, calls: dict) -> dict:
    """A pre-finalize topology: nodes {ref: (kind, is_service)}, edges [(from, to, label, risks)]."""
    P = topology.prop
    comps, svcs = [], []
    agent = {"bom-ref": "agent", "name": "agent", "type": "application", "properties": [P("kind", "agent")]}
    for ref, (kind, is_svc) in nodes.items():
        n = {"bom-ref": ref, "name": ref, "properties": [P("kind", kind)]}
        (svcs if is_svc else comps).append(n if is_svc else {**n, "type": "data" if kind == "data_store" else "application"})
    by = {"agent": agent, **{n["bom-ref"]: n for n in comps + svcs}}
    for a, b, label, risks in edges:
        by[a]["properties"].append(P("edge", f"{b}|{label}|traced|x.py:1|{','.join(risks)}"))
    bom = {"metadata": {"component": agent, "properties": []}, "components": comps, "services": svcs,
           "dependencies": [{"ref": r, "dependsOn": calls.get(r, [])} for r in by], "compositions": []}
    topology.finalize(bom)
    return bom


def test_component_to_component_edge_keeps_label_and_risks():
    bom = _working_bom({"unit:app.py": ("agent_unit", False), "data:customers": ("data_store", False)},
                       [("unit:app.py", "data:customers", "reads customer notes", ["personal_data", "untrusted_input"])],
                       {"agent": ["unit:app.py"], "unit:app.py": ["data:customers"]})
    c = next(c for c in topology.connections(bom) if (c["from"], c["to"]) == ("unit:app.py", "data:customers"))
    assert c["label"] == "reads customer notes" and {"personal_data", "untrusted_input"} <= set(c["risks"])
    topology.infer_tags(bom)
    tags = topology.node_tags(next(c for c in bom["components"] if c["bom-ref"] == "data:customers"))
    # untrusted_input can only come from the edge's risks, so this proves they survived finalize.
    assert any(t["tag"] == "untrusted_input" and "unit:app.py -> data:customers" in t["reason"] for t in tags)

def test_reply_edge_stays_distinct_from_call():
    bom = _working_bom({"unit:app.py": ("agent_unit", False), "api:search": ("external_api", True)},
                       [("unit:app.py", "api:search", "sends query", ["writes"]),
                        ("api:search", "unit:app.py", "returns web results", ["untrusted_input"])],
                       {"agent": ["unit:app.py"], "unit:app.py": ["api:search"], "api:search": ["unit:app.py"]})
    conns = {(c["from"], c["to"]): c for c in topology.connections(bom)}
    call, reply = conns[("unit:app.py", "api:search")], conns[("api:search", "unit:app.py")]
    assert call["label"] == "sends query" and "writes" in call["risks"] and "untrusted_input" not in call["risks"]
    assert reply["label"] == "returns web results" and reply["risks"] == ["untrusted_input"]


def test_return_way_flow_folds_back_onto_its_call():
    bom = _working_bom({"tool:get": ("tool", True), "api:fx": ("external_api", True)},
                       [("tool:get", "api:fx", "gets exchange rates", [])],
                       {"agent": ["tool:get"], "tool:get": ["api:fx"]})
    conns = {(c["from"], c["to"]): c for c in topology.connections(bom)}
    assert conns[("tool:get", "api:fx")]["label"] == "gets exchange rates" and ("api:fx", "tool:get") not in conns


def test_flow_direction_whole_words():
    assert topology.flow_direction([], "budget review") == "both"   # no 'get' inside 'budget'
    assert topology.flow_direction([], "spread sheet") == "both"    # no 'read' inside 'spread'
    assert topology.flow_direction([], "returns web results") == "return"
    assert topology.flow_direction([], "sends query") == "call"
