"""Found-on-host evidence: client settings files and imported scanner output."""
import json
import sys
from pathlib import Path

import pytest

TOOL_DIR = Path(__file__).resolve().parents[2] / "tools" / "brace"
from open_agent_security import host_scan
from brace_tools.imports import scanners as scan_import
from brace_tools.topology import core as topology
from brace_tools.report import map_html as tr

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
    recs, notes = host_scan.read_host(host_scan.host_sources(home, "Linux"), project=Path("/w/app"))
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
    monkeypatch.setattr(scan_import, "MAX_BYTES", 1)
    assert scan_import.import_scan(big)[0] == [] and "larger" in scan_import.import_scan(big)[1][0]
    monkeypatch.undo()
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    assert scan_import.import_scan(bad) == ([], ["bad.json: JSONDecodeError"])
    other = tmp_path / "other.json"
    other.write_text('{"hello": 1}')
    assert "not a recognised" in scan_import.import_scan(other)[1][0]


@pytest.mark.parametrize("name,server,tool,code", [
    ("snyk-agent-scan-v05.json", "web-fetch", "fetch_url", "W001"),
    ("snyk-agent-scan-v06.json", "web-fetch", "fetch_url", "untrusted_content"),
    ("cisco-mcp-scanner.json", "travel-docs", "get_advisories", "PROMPT INJECTION"),
])
def test_scanner_formats(name, server, tool, code):
    recs, notes = scan_import.import_scan(HS / name)
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


def test_redacts_home_folders_in_scan_import(tmp_path):
    pytest.importorskip("jsonschema")
    repo = EX / "repo"
    host, _ = topology.host_evidence(repo, False, [], [HS / "snyk-agent-scan-v05.json"], home=Path("/Users/bob"))
    bom = topology.build(repo, repo / "brace-inventory.json", repo / "config/agent.yaml",
                         EX / "brace-topology.overlay.json", host=host)
    text = json.dumps(host) + json.dumps(bom)
    assert "/home/sample" not in text and "sample/" not in text and "~/.cursor/mcp.json" in text


def test_redact_home_only_leading_prefix():
    home = Path("/srv/bob")
    assert topology.redact_home("/srv/bob/x.json", home) == "~/x.json"
    assert topology.redact_home("/srv/bobby/x.json", home) == "/srv/bobby/x.json"
    assert topology.redact_home("/opt/srv/bob/x", home) == "/opt/srv/bob/x"
    assert topology.redact_home("c: /Users/alice/a.json#/home/carol/b", None) == "c: ~/a.json#~/b"


def test_claude_json_reads_only_this_project(tmp_path):
    proj, other = tmp_path / "proj", tmp_path / "other"
    proj.mkdir()
    (tmp_path / ".claude.json").write_text(json.dumps({"mcpServers": {"user": {"command": "u"}}, "projects": {
        str(proj.resolve()): {"mcpServers": {"mine": {"command": "m"}}},
        str(other): {"mcpServers": {"theirs": {"command": "t"}}}}}))
    recs, _ = topology.host_evidence(proj, True, [], [], home=tmp_path, system="Linux")
    names = {r["name"] for r in recs}
    assert "mine" in names and "user" in names and "theirs" not in names


def test_host_config_reads_project_files(tmp_path):
    proj = tmp_path / "proj"
    for rel, key, name in ((".cursor/mcp.json", "mcpServers", "cur"), (".vscode/mcp.json", "servers", "vsc"),
                           (".devin/mcp_config.json", "mcpServers", "dev")):
        (proj / rel).parent.mkdir(parents=True, exist_ok=True)
        (proj / rel).write_text(json.dumps({key: {name: {"command": "x"}}}))
    recs, _ = topology.host_evidence(proj, True, [], [], home=tmp_path / "home", system="Linux")
    assert {"cur", "vsc", "dev"} <= {r["name"] for r in recs}


def test_clean_url_bad_port():
    assert host_scan.clean_url("http://h:abc/p?q=1") == "http://h/p"


@pytest.mark.parametrize("data", [
    {"/p": {"servers": "nope"}},
    {"/p": {"servers": [{"name": "s", "signature": {"tools": "x"}}], "issues": {"a": 1}}},
    {"scan_path_responses": [{"server_risks": {"a": 1}}]},
    {"scan_path_responses": [{"server_risks": [{"name": "s", "entities": "x", "risk_indexes": [1]}]}]},
    {"scan_path_responses": [{"server_risks": [{"name": "s", "risk_indexes": {"r": {"affected_tools": 3}}}]}]},
    {"server_url": "http://h", "scan_results": "x"},
    {"server_url": "http://h", "scan_results": [{"tool_name": "t", "findings": ["x"]}]},
])
def test_scanner_wrong_types_noted_not_crash(tmp_path, data):
    f = tmp_path / "scan.json"
    f.write_text(json.dumps(data))
    recs, notes = scan_import.import_scan(f)
    assert notes and all("skipped" in n for n in notes)


GHP = "ghp_" + "Ab1" * 12


def test_host_records_redact_names_and_command_strings():
    rec = host_scan.server_record(f"gh {GHP}", {"command": f"npx -y server-x@1.0.0 --api-key={GHP}"}, "Cursor",
                                  "/home/u/.cursor/mcp.json", "mcpServers.gh")
    assert rec["command"] == "npx" and rec["args"][:2] == ["-y", "server-x@1.0.0"]
    assert GHP not in json.dumps(rec) and "<redacted>" in rec["name"]


def test_scan_import_redacts_messages_and_names(tmp_path):
    data = {"/home/u/.cursor/mcp.json": {"client": "cursor", "servers": [
        {"name": f"srv {GHP}", "server": {"command": "npx", "args": ["x"]}, "signature": {"tools": [{"name": "t"}]}}],
        "issues": [{"code": "W001", "message": f"token {GHP} leaked", "reference": [0, 0]}]}}
    path = tmp_path / "snyk.json"
    path.write_text(json.dumps(data))
    recs, notes = scan_import.import_scan(path)
    text = json.dumps(recs)
    assert notes == [] and GHP not in text and recs[0]["issues"][0]["message"] == "token <redacted> leaked"
    assert recs[0]["file"] == str(path)
