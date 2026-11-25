"""Found-on-host evidence: client settings files and imported scanner output."""
import json
import sys
from pathlib import Path

import pytest

TOOL_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TOOL_DIR))
import host_scan  # noqa: E402
import topology  # noqa: E402
import topology_report as tr  # noqa: E402

HS = TOOL_DIR / "examples" / "host-scan"
EX = TOOL_DIR / "examples" / "travel-agent"
SECRETS = ["should-not-be-copied", "sk-sample-not-a-real-key", "tok_sample_value_never_copied", "info"]


def test_sources_per_os(tmp_path):
    mac = {s["client"]: s["path"] for s in host_scan.host_sources(tmp_path, "Darwin")}
    assert mac["Claude Desktop"] == tmp_path / "Library/Application Support/Claude/claude_desktop_config.json"
    assert str(mac["Claude Code (managed)"]) == "/Library/Application Support/ClaudeCode/managed-mcp.json"
    win = {s["client"]: s["path"] for s in host_scan.host_sources(tmp_path, "Windows", env={"APPDATA": "C:/AD"})}
    assert win["Claude Desktop"] == Path("C:/AD/Claude/claude_desktop_config.json")
    lin = {s["client"]: s["path"] for s in host_scan.host_sources(tmp_path, "Linux", project=tmp_path / "p")}
    assert lin["Cursor"] == tmp_path / ".cursor/mcp.json" and lin["VS Code (workspace)"] == tmp_path / "p/.vscode/mcp.json"


def test_reads_host_files_without_secret_values(tmp_path):
    home = tmp_path
    (home / ".cursor").mkdir()
    (home / ".cursor/mcp.json").write_text((HS / "claude_desktop_config.json").read_text())
    (home / ".claude.json").write_text(json.dumps({"projects": {"/w/app": {"mcpServers": {
        "crm": {"type": "http", "url": "https://user:pw@crm.example/mcp#x", "headers": {"Authorization": "Bearer abc"}}}}}}))
    recs, notes = host_scan.read_host(host_scan.host_sources(home, "Linux"))
    assert notes == []
    by = {r["name"]: r for r in recs}
    assert by["travel-docs"]["url"] == "https://travel-docs.internal.example/mcp"
    assert by["web-fetch"]["command"] == "npx" and by["web-fetch"]["env_keys"] == ["FETCH_TOKEN", "LOG_LEVEL"]
    assert "<redacted>" in by["web-fetch"]["args"]
    assert by["crm"]["key"] == 'projects."/w/app".mcpServers.crm' and by["crm"]["url"] == "https://crm.example/mcp"
    assert by["crm"]["header_keys"] == ["Authorization"]
    text = json.dumps(recs)
    for s in SECRETS + ["Bearer abc", "user:pw"]:
        assert s not in text.replace('"LOG_LEVEL"', "")


def test_size_limit_and_bad_json(tmp_path, monkeypatch):
    big = tmp_path / "big.json"
    big.write_text("{}")
    monkeypatch.setattr(host_scan, "MAX_BYTES", 1)
    assert host_scan.import_scan(big)[0] == [] and "larger" in host_scan.import_scan(big)[1][0]
    monkeypatch.undo()
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    assert host_scan.import_scan(bad) == ([], ["bad.json: JSONDecodeError"])
    other = tmp_path / "other.json"
    other.write_text('{"hello": 1}')
    assert "not a recognised" in host_scan.import_scan(other)[1][0]


@pytest.mark.parametrize("name,server,tool,code", [
    ("snyk-agent-scan-v05.json", "web-fetch", "fetch_url", "W001"),
    ("snyk-agent-scan-v06.json", "web-fetch", "fetch_url", "untrusted_content"),
    ("cisco-mcp-scanner.json", "travel-docs", "get_advisories", "PROMPT INJECTION"),
])
def test_scanner_formats(name, server, tool, code):
    recs, notes = host_scan.import_scan(HS / name)
    assert notes == [] and recs[0]["name"] == server and tool in recs[0]["tools"]
    assert [i["code"] for i in recs[0]["issues"]] == [code] and recs[0]["issues"][0]["tool"] == tool


def test_host_evidence_in_map_and_report(tmp_path):
    pytest.importorskip("jsonschema")
    repo = EX / "repo"
    host, notes = topology.host_evidence(repo, False, [HS / "claude_desktop_config.json"],
                                         [HS / "cisco-mcp-scanner.json", HS / "snyk-agent-scan-v05.json"])
    bom = topology.build(repo, repo / "brace-inventory.json", repo / "config/agent.yaml",
                         EX / "brace-topology.overlay.json", host=host)
    assert topology.validate(bom) == []
    nodes = topology.all_nodes(bom)
    assert topology.node_props(nodes["mcp:travel-docs"])["host_evidence"]  # declared server, also on host
    assert topology.node_props(nodes["mcp:web-fetch"])["source"] == ["host"]  # only on host
    assert "mcp:web-fetch/fetch_url" in nodes
    m = tr.build_model(bom, None)
    assert m["parts"]["mcp:web-fetch"]["status"] == "undeclared"
    assert m["parts"]["mcp:travel-docs"]["status"] == "confirmed"
    edge = next(e for e in m["edges"] if e["to"] == "mcp:web-fetch")
    assert edge["status"] == "undeclared"
    page = tr.render(m)
    assert "<b>instructions</b>" not in page
    blob = json.loads(page.split("id=topology-data>")[1].split("</script>")[0])
    assert any("<b>instructions</b>" in x["quote"] for p in blob["parts"] for x in p["on_host"])
    text = json.dumps(bom) + page
    for s in SECRETS[:3]:
        assert s not in text
