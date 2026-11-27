"""--output cyclonedx=FILE: the agent config and MCP server inventory, as CycloneDX 1.7 JSON.

Validated offline against the bundled CycloneDX schema (schemas/cyclonedx-1.7) with
topology.validate, which also checks bom-refs and dependencies.
"""
import json
import sys

import pytest
from support import TOKEN, TOOL_DIR, cli_run, write

from brace_tools.topology import core as topology

from open_agent_security.report.cyclonedx import purl, split_spec  # noqa: E402

DIGEST = "sha256:" + "a" * 64


def mcp(root, *servers, rel=".mcp.json"):
    write(root, rel, json.dumps({"mcpServers": {s.pop("name"): s for s in map(dict, servers)}}, indent=2))


def bom_of(root, *args):
    out = root / "inv.cdx.json"
    code, _, err = cli_run(root, "--fail-on", "none", "--output", f"cyclonedx={out}", *args)
    assert code == 0, err
    return json.loads(out.read_text()), out.read_text()


def props(node):
    out = {}
    for p in node.get("properties", []):
        out.setdefault(p["name"].removeprefix("brace:"), []).append(p["value"])
    return out


@pytest.fixture
def repo(tmp_path):
    mcp(tmp_path,
        {"name": "gh", "command": "npx", "args": ["-y", "@modelcontextprotocol/server-github@1.2.3"],
         "env": {"GITHUB_TOKEN": TOKEN}},
        {"name": "loose", "command": "uvx", "args": ["mcp-server-fetch"]},
        {"name": "box", "command": "docker", "args": ["run", "-i", "--rm", f"ghcr.io/acme/mcp@{DIGEST}"]},
        {"name": "remote", "type": "http", "url": f"https://user:{TOKEN}@mcp.example.com:8443/v1?key={TOKEN}",
         "headers": {"Authorization": f"Bearer {TOKEN}"}})
    write(tmp_path, ".cursor/mcp.json", json.dumps({"mcpServers": {"local": {"command": "node", "args": ["s.js"]}}}))
    return tmp_path


def by_name(bom):
    return {s["name"]: s for s in bom["services"]}


def test_valid_against_bundled_schema(repo):
    bom, _ = bom_of(repo)
    assert bom["specVersion"] == topology.SPEC_VERSION == "1.7"
    assert topology.validate(bom) == []


def test_lists_configs_servers_and_packages(repo):
    bom, _ = bom_of(repo)
    files = {c["name"]: props(c) for c in bom["components"] if c["type"] == "file"}
    assert files[".mcp.json"]["client"] == ["Claude Code"]
    assert files[".cursor/mcp.json"]["client"] == ["Cursor"]
    s = by_name(bom)
    gh = props(s["gh"])
    assert gh["transport"] == ["stdio"] and gh["runner"] == ["npx"] and gh["config_file"] == [".mcp.json"]
    assert gh["line"][0].isdigit() and gh["env_key"] == ["GITHUB_TOKEN"]
    assert any(f.startswith("AP05 ") for f in gh["finding"])
    pkgs = {c["name"]: c for c in bom["components"] if c["type"] == "library"}
    pinned = pkgs["@modelcontextprotocol/server-github"]
    assert pinned["version"] == "1.2.3" and pinned["purl"] == "pkg:npm/%40modelcontextprotocol/server-github@1.2.3"
    assert props(pkgs["mcp-server-fetch"])["pinned"] == ["false"] and "version" not in pkgs["mcp-server-fetch"]
    assert any(f.startswith("AP04 ") for f in props(s["loose"])["finding"])
    image = next(c for c in bom["components"] if c["type"] == "container")
    assert image["name"] == "ghcr.io/acme/mcp" and image["hashes"][0]["content"] == "a" * 64
    deps = {d["ref"]: d.get("dependsOn", []) for d in bom["dependencies"]}
    assert deps[s["box"]["bom-ref"]] == [image["bom-ref"]]
    assert props(s["remote"])["url_host"] == ["mcp.example.com:8443"]
    assert s["remote"]["endpoints"] == ["https://mcp.example.com:8443"]
    assert props(s["remote"])["header_key"] == ["Authorization"]


def test_no_secrets_or_env_values(repo):
    _, text = bom_of(repo)
    assert TOKEN not in text and "Bearer" not in text and "user:" not in text and "/v1" not in text


def test_secret_where_a_package_goes_is_redacted(tmp_path):
    mcp(tmp_path, {"name": "x", "command": "npx", "args": ["-y", TOKEN]})
    bom, text = bom_of(tmp_path)
    assert TOKEN not in text
    assert topology.validate(bom) == []


def test_empty_folder_is_a_valid_empty_bom(tmp_path):
    bom, _ = bom_of(tmp_path)
    assert bom["components"] == [] and bom["services"] == [] and topology.validate(bom) == []


def test_codex_toml_and_agent_workflow(tmp_path):
    write(tmp_path, ".codex/config.toml", '[mcp_servers.docs]\ncommand = "npx"\nargs = ["-y", "docs-mcp@2.0.0"]\n')
    write(tmp_path, ".github/workflows/agent.yml",
          "on: pull_request\njobs:\n  a:\n    runs-on: ubuntu-latest\n    steps:\n"
          "      - uses: anthropics/claude-code-action@v1\n")
    bom, _ = bom_of(tmp_path)
    assert props(by_name(bom)["docs"])["client"] == ["Codex"]
    assert topology.validate(bom) == []


def test_hostile_names_stay_json_and_valid(tmp_path):
    mcp(tmp_path, {"name": "</script><b>\u202e\x1b[31m", "command": "npx", "args": ["-y", "a@1.0.0"]})
    bom, text = bom_of(tmp_path)
    assert "\x1b" not in text and topology.validate(bom) == []


def test_serial_number_is_stable(repo):
    a, _ = bom_of(repo)
    b, _ = bom_of(repo)
    assert a["serialNumber"] == b["serialNumber"]


@pytest.mark.parametrize("eco,spec,want", [
    ("npm", "@s/p@1.0.0", ("@s/p", "1.0.0")), ("npm", "p", ("p", "")), ("pypi", "Foo==1.2", ("Foo", "1.2")),
    ("pypi", "foo[x]@2", ("foo", "2")), ("npm", "<redacted>", ("", "")), ("deno", "x", ("", ""))])
def test_split_spec(eco, spec, want):
    assert split_spec(eco, spec) == want


def test_purl():
    assert purl("pypi", "Foo", "1.2") == "pkg:pypi/foo@1.2"
