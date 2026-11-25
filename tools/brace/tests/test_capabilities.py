"""Capability tags and dangerous combinations (BRACE B05) in the topology and its report."""
import json
import sys
from pathlib import Path

import pytest

TOOL_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TOOL_DIR))
import topology  # noqa: E402
import topology_report as tr  # noqa: E402

EX = TOOL_DIR / "examples" / "travel-agent"


def P(name, value):
    return {"name": f"brace:{name}", "value": value}


def node(ref, kind, *tags):
    props = [P("kind", kind)] + [p for t in tags for p in topology.tag_props(t, "reviewer", "x.py:1")]
    return {"bom-ref": ref, "name": ref, "properties": props}


def bom_of(components, services, deps, provides=None):
    d = {a: {"ref": a, "dependsOn": b} for a, b in deps.items()}
    for a, b in (provides or {}).items():
        d.setdefault(a, {"ref": a})["provides"] = b
    return {"metadata": {"component": node("agent", "agent"), "properties": []},
            "components": components, "services": services, "dependencies": list(d.values())}


@pytest.fixture(scope="module")
def travel():
    pytest.importorskip("jsonschema")
    repo = EX / "repo"
    return topology.build(repo, repo / "brace-inventory.json", repo / "config/agent.yaml",
                          EX / "brace-topology.overlay.json")


def test_tags_carry_their_source(travel):
    nodes = topology.all_nodes(travel)
    src = {(r, t["tag"]): t["source"] for r, n in nodes.items() for t in topology.node_tags(n)}
    assert src[("tool:send_itinerary", "external_send")] == "declared"
    assert src[("api:analytics", "external_send")] == "reviewer"
    assert src[("data:profiles", "private_data")] == "inferred"
    assert src[("api:fares", "destructive")] == "inferred"  # the connection moves money
    assert ("api:fx", "external_send") not in src  # no obvious reason: stays unknown


def test_travel_agent_has_both_combinations(travel):
    combos = {c["type"]: c for c in topology.combinations(travel)}
    assert combos["leak"]["status"] == "present" and combos["harm"]["status"] == "present"
    assert combos["leak"]["pick"]["external_send"] == "api:analytics"
    assert combos["leak"]["pick"]["untrusted_input"] == "api:advisories"
    assert "api:fx" in combos["leak"]["unknown"]
    stored = {p["name"]: p["value"] for p in travel["metadata"]["properties"] if p["name"].startswith("brace:combination:")}
    assert stored["brace:combination:leak:agent"] == "present" and stored["brace:combination:harm:agent"] == "present"
    assert stored["brace:combination:leak:agent:external_send"] == "api:analytics"
    assert all("|" not in v and not v.startswith(("[", "{")) for v in stored.values())
    assert topology.validate(travel) == []


def test_reachability_goes_through_sub_agents_and_mcp_tools():
    bom = bom_of(
        [node("unit:sub", "agent_unit"), node("data:crm", "data_store")],
        [node("mcp:web", "mcp_server"), node("mcp:web/fetch", "mcp_tool", "untrusted_input"),
         node("tool:post", "tool"), node("api:out", "external_api", "external_send"), node("tool:crm", "tool")],
        {"agent": ["unit:sub"], "unit:sub": ["mcp:web", "tool:crm", "tool:post"], "tool:crm": ["data:crm"],
         "tool:post": ["api:out"]}, provides={"mcp:web": ["mcp:web/fetch"]})
    topology.infer_tags(bom)
    combos = topology.combinations(bom)
    sub = [c for c in combos if c["type"] == "leak"]
    assert sub and sub[0]["status"] == "present"
    assert sub[0]["pick"] == {"untrusted_input": "mcp:web/fetch", "private_data": "data:crm",
                              "external_send": "api:out"}
    assert sub[0]["paths"]["untrusted_input"] == ["agent", "unit:sub", "mcp:web", "mcp:web/fetch"]
    # The root's combination is the same, so the sub-agent's copy is not repeated.
    assert len(sub) == 1


def test_reply_into_agent_does_not_spread_reach():
    bom = bom_of([node("unit:a", "agent_unit"), node("unit:b", "agent_unit")],
                 [node("mcp:web", "mcp_server", "untrusted_input"), node("api:pay", "external_api", "destructive")],
                 {"unit:a": ["mcp:web"], "mcp:web": ["unit:b"], "unit:b": ["api:pay"]})
    assert "api:pay" not in topology.reach(bom, "unit:a")
    assert "api:pay" in topology.reach(bom, "unit:b")


def test_harm_and_unknown_is_possible_not_safe():
    bom = bom_of([], [node("api:web", "external_api", "untrusted_input"), node("tool:mystery", "tool")],
                 {"agent": ["api:web", "tool:mystery"]})
    combos = {c["type"]: c for c in topology.combinations(bom)}
    assert combos["harm"]["status"] == "possible" and combos["harm"]["missing"] == ["destructive"]
    assert combos["harm"]["unknown"] == ["tool:mystery"]
    assert "leak" not in combos  # two of three missing: not flagged
    bom["services"][1]["properties"] += topology.tag_props("none", "reviewer", "x.py:1")
    assert topology.combinations(bom) == []


def test_overlay_tags_are_verified(tmp_path):
    repo = tmp_path / "r"
    (repo / "src").mkdir(parents=True)
    (repo / "src/a.py").write_text("requests.post(URL)\n")
    (repo / "agent.yaml").write_text("agent: {name: a}\ntools:\n  allowlist:\n    - post\n"
                                     "capabilities:\n  tool:post: [external_send, flies]\n")
    ov = repo / "o.json"
    assert topology.main(["add-tag", str(repo), "--overlay", str(ov), "--ref", "tool:post", "--tag", "external_send",
                          "--evidence", "src/a.py:1", "--quote", "requests.post"]) == 0
    assert topology.main(["add-tag", str(repo), "--overlay", str(ov), "--ref", "tool:post", "--tag", "destructive",
                          "--evidence", "src/a.py:1", "--quote", "not there"]) == 1
    data = json.loads(ov.read_text())
    data["tags"].append({"ref": "tool:ghost", "tag": "destructive", "evidence": "src/a.py:1", "quote": "requests"})
    ov.write_text(json.dumps(data))
    bom = topology.build(repo, None, repo / "agent.yaml", ov)
    stale = topology.stale_entries(bom)
    assert any("flies" in s for s in stale) and any("tool:ghost" in s for s in stale)
    tags = topology.node_tags(topology.all_nodes(bom)["tool:post"])
    assert {(t["tag"], t["source"]) for t in tags} == {("external_send", "declared"), ("external_send", "reviewer")}


def test_report_section_and_escaping(travel):
    findings = json.loads((EX / "sample-findings.json").read_text())
    m = tr.build_model(travel, findings)
    assert m["summary"]["combos"] == 2
    page = tr.render(m)
    assert page.index("Dangerous combinations") < page.index("id=map-h")
    assert "B05 · Destructive-action interception" in page and "github" not in page.lower()
    assert page.count("class=combo-btn") == 2 and "Can be tricked into leaking data" in page
    c = m["combos"][0]
    assert all(i in {p["id"] for p in m["parts"].values()} | {e["id"] for e in m["edges"]} for i in c["highlight"])
    evil = json.loads(json.dumps(travel))
    for s in evil["services"]:
        if s["bom-ref"] == "api:analytics":
            s["name"] = "<img src=x onerror=alert(1)>"
    page = tr.render(tr.build_model(evil, findings))
    assert "<img src=x" not in page and "&lt;img src=x" in page


def test_findings_ranked_by_gate_then_reach(travel):
    findings = json.loads((EX / "sample-findings.json").read_text())
    findings = json.loads(json.dumps(findings))
    findings["findings"][0]["aivss"] = {"score": 8.1, "version": "0.8"}
    m = tr.build_model(travel, findings)
    order = tr.ranked(m["findings"])
    gates = [tr.GATES.index(f["gate"]) for f in order]
    assert gates == sorted(gates)
    for a, b in zip(order, order[1:]):
        if a["gate"] == b["gate"]:
            assert (a["reach_combos"], a["reach_edges"]) >= (b["reach_combos"], b["reach_edges"]) or \
                (a["reach_combos"] > b["reach_combos"])
    assert any(f["reach_combos"] for f in m["findings"])
    f = next(f for f in m["findings"] if f["reach_combos"])
    assert f["reach_text"].startswith("Affects ") and "dangerous combination" in f["reach_text"]
    assert tr.reach_text(1, 0) == "Affects 1 connection."
    page = tr.render(m)
    assert "AIVSS 8.1 (v0.8)" in page


def test_cyclonedx_shape(travel):
    """Data flows, data classifications and simple properties (no packed values)."""
    svc = {s["bom-ref"]: s for s in travel["services"]}
    flows = svc["mcp:travel-docs"]["data"]
    reply = next(f for f in flows if f["destination"] == ["unit:src/agent.py"])
    assert reply["flow"] == "outbound" and reply["classification"] == "untrusted_input"
    assert not any("unit:src/agent.py" in d.get("dependsOn", []) for d in travel["dependencies"]
                   if d["ref"] == "mcp:travel-docs")  # dependsOn is call direction only
    analytics = next(f for f in svc["api:analytics"]["data"] if f["classification"] == "personal_data")
    assert analytics["source"] == ["tool:book_flight"] and analytics["flow"] == "inbound"
    store = next(c for c in travel["components"] if c["bom-ref"] == "data:profiles")
    assert store["data"] == [{"type": "dataset", "name": "traveler profiles database", "classification": "private_data"}]
    for n in [*travel["components"], *travel["services"], travel["metadata"]["component"]]:
        for p in n.get("properties", []):
            assert p["name"] not in ("brace:edge", "brace:quote", "brace:declared_edge")
            assert not (p["name"].startswith("brace:edge") and "|" in p["value"])
    names = [p["name"] for n in travel["services"] for p in n.get("properties", [])]
    assert "brace:quote:file" in names and "brace:quote:text" in names
