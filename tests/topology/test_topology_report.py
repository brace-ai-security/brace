"""Topology web report: classification, findings mapping, escaping and the shipped example."""
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

import pytest

TOOL_DIR = Path(__file__).resolve().parents[2] / "tools" / "brace"
from brace_tools.topology import core as topology
from brace_tools.report import map_html as tr

EX = TOOL_DIR / "examples" / "travel-agent"


@pytest.fixture(scope="module")
def built():
    pytest.importorskip("jsonschema")
    repo = EX / "repo"
    bom = topology.build(repo, repo / "brace-inventory.json", repo / "config/agent.yaml",
                         EX / "brace-topology.overlay.json")
    return bom, json.loads((EX / "sample-findings.json").read_text())


def test_example_bom_is_current_and_valid(built):
    bom, _ = built
    assert topology.validate(bom) == [] and topology.stale_entries(bom) == []
    shipped = json.loads((EX / "topology.cdx.json").read_text())
    assert topology.compare(shipped, bom) == [], "regenerate examples/travel-agent (see its README)"


def test_declared_detected_undeclared(built):
    m = tr.build_model(*built)
    p, e = m["parts"], {(x["from"], x["to"]): x for x in m["edges"]}
    assert p["api:analytics"]["status"] == "undeclared"
    assert p["api:fx"]["status"] == "declared" and p["tool:convert_currency"]["status"] == "declared"
    assert p["api:fares"]["status"] == "confirmed" and p["data:profiles"]["status"] == "confirmed"
    assert p["model:claude-sonnet-4-5"]["status"] == "confirmed"
    assert e[("tool:book_flight", "api:analytics")]["status"] == "undeclared"
    assert e[("unit:src/itinerary_writer.py", "tool:book_flight")]["status"] == "undeclared"
    assert e[("tool:convert_currency", "api:fx")]["status"] == "declared"
    assert e[("mcp:travel-docs", "api:advisories")]["status"] == "confirmed"
    assert p["api:analytics"]["zone"] == "unknown" and p["mcp:travel-docs"]["zone"] == "company network"
    assert e[("tool:book_flight", "api:fares")]["found_in"][0]["quote"].startswith("r = httpx.post")


def test_reply_from_service_is_part_of_declared_connection(built):
    m = tr.build_model(*built)
    e = {(x["from"], x["to"]): x for x in m["edges"]}
    reply = e[("mcp:travel-docs", "unit:src/agent.py")]
    assert reply["reply"] and reply["status"] == "confirmed"
    assert not e[("unit:src/itinerary_writer.py", "tool:book_flight")]["reply"]
    assert m["summary"]["undeclared"] == 3


def test_no_people_in_report_or_fixtures(built):
    page = tr.render(tr.build_model(*built))
    assert "Assigned to" not in page and "nobody assigned" not in page and "Lead role" in page
    for name in ("travel-agent", "billing-agent"):
        assert "assignee" not in (TOOL_DIR / "examples" / name / "sample-findings.json").read_text()


def test_findings_go_on_connections_or_parts(built):
    m = tr.build_model(*built)
    items = {f["item"]: f for f in m["findings"]}
    e = {(x["from"], x["to"]): x for x in m["edges"]}
    assert [m["findings"][i]["item"] for i in e[("tool:book_flight", "api:analytics")]["findings"]] == ["B09"]
    assert [m["findings"][i]["item"] for i in m["parts"]["mcp:travel-docs"]["badge"]] == ["B03"]
    assert items["E08"]["gate"] == "Blocker" and items["R08"]["gate"] == "Detection"
    assert items["E08"]["lead"] == "Agent team" and items["B03"]["lead"] == "Infrastructure"
    assert not any("assignee" in f for f in m["findings"])
    assert m["summary"]["findings"] == {"Blocker": 5, "Required": 2, "Detection": 1}
    assert not any(re.search(r"\bG[123]\b", json.dumps(f)) for f in m["findings"])


class Collect(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags, self.scripts, self.attrs = [], [], []
        self._in = None

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        self.attrs += [(tag, k, v) for k, v in attrs]
        self._in = tag

    def handle_data(self, data):
        if self._in == "script":
            self.scripts.append(data)


def test_page_structure_is_self_contained(built):
    page = tr.render(tr.build_model(*built))
    c = Collect()
    c.feed(page)
    for tag in ("svg", "table", "aside", "form", "main"):
        assert tag in c.tags
    assert "<link" not in page and " src=" not in page and "github.com" not in page.lower()
    assert "@media print" in page and "prefers-color-scheme:dark" in page
    data = json.loads(page.split("id=topology-data>")[1].split("</script>")[0])
    assert len(data["parts"]) == 18 and len(data["edges"]) == 19
    assert page.count("role=button") == 18 + 19


def test_untrusted_text_is_escaped(built, tmp_path):
    bom, findings = built
    bom = json.loads(json.dumps(bom))
    evil = "<script>alert(1)</script>\"'&"
    bom["services"][0]["name"] = evil
    for p in bom["components"]:
        p["properties"].append({"name": "brace:quote", "value": json.dumps(["src/x.py:1", evil])})
        p["properties"].append({"name": "brace:traced_evidence", "value": "src/x.py:1"})
    findings = json.loads(json.dumps(findings))
    findings["findings"][0]["fix"]["steps"][0] = evil
    findings["findings"][0]["fix"]["done_when"] = evil
    page = tr.render(tr.build_model(bom, findings))
    assert "<script>alert" not in page
    assert page.count("<script") == 2  # the data block and the page script only
    blob = page.split("id=topology-data>")[1].split("</script>")[0]
    assert "<" not in blob and ">" not in blob and evil in json.loads(blob)["findings"][0]["steps"][0] + "".join(
        x["name"] for x in json.loads(blob)["parts"])
    assert "innerHTML" not in tr.JS


def test_cli_writes_report(tmp_path):
    out = tmp_path / "r.html"
    assert topology.main(["report", str(EX / "topology.cdx.json"), "--findings",
                          str(EX / "sample-findings.json"), "-o", str(out)]) == 0
    assert out.read_text().startswith("<!doctype html>")


@pytest.mark.parametrize("name", ["travel-agent", "billing-agent"])
def test_shipped_reports_are_current(name):
    ex = TOOL_DIR / "examples" / name
    m = tr.build_model(json.loads((ex / "topology.cdx.json").read_text()),
                       json.loads((ex / "sample-findings.json").read_text()))
    assert (ex / "topology-report.html").read_text() == tr.render(m), f"regenerate examples/{name}/topology-report.html"


def test_layout_has_no_overlapping_parts(built):
    m = tr.build_model(*built)
    L = tr.layout(m)
    boxes = [L["pos"][r] for r, p in m["parts"].items() if not p["parent"]]
    for i, a in enumerate(boxes):
        for b in boxes[i + 1:]:
            assert a[0] + a[2] <= b[0] or b[0] + b[2] <= a[0] or a[1] + a[3] <= b[1] or b[1] + b[3] <= a[1]
