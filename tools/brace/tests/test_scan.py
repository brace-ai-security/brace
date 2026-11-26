import json
import sys
from pathlib import Path

TOOL_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TOOL_DIR))

import scan  # noqa: E402


def write(root: Path, rel: str, text: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def rules(root: Path) -> list[str]:
    return sorted(f.rule for f in scan.dedupe(scan.scan_repo(root)))


def test_clean_repo_has_no_findings(tmp_path):
    write(tmp_path, ".mcp.json", json.dumps({"mcpServers": {"docs": {"command": "npx", "args": ["-y", "docs-mcp@1.2.3"]}}}))
    write(tmp_path, "Dockerfile", "FROM python@sha256:abc AS base\nFROM base\n")
    assert rules(tmp_path) == []
    assert scan.run(str(tmp_path), False, True, "low", out=open(tmp_path / "o.json", "w")) == 0


def test_skip_permissions_local_vs_ci(tmp_path):
    write(tmp_path, "run.sh", "claude -p 'fix' --dangerously-skip-permissions\n")
    write(tmp_path, ".github/workflows/agent.yml", "steps:\n  - run: claude -p x --dangerously-skip-permissions\n")
    assert rules(tmp_path) == ["AP01", "AP02"]


def test_pull_request_target_with_agent(tmp_path):
    write(tmp_path, ".github/workflows/a.yml",
          "on:\n  pull_request_target:\njobs:\n  r:\n    steps:\n      - uses: anthropics/claude-code-action@v1\n")
    write(tmp_path, ".github/workflows/b.yml", "on:\n  pull_request_target:\njobs:\n  r:\n    steps:\n      - run: make\n")
    assert rules(tmp_path) == ["AP03"]


def test_mcp_server_rules(tmp_path):
    cfg = {"mcpServers": {
        "a": {"command": "npx", "args": ["-y", "@scope/thing"]},
        "b": {"command": "uvx", "args": ["tool@latest"]},
        "c": {"command": "docker", "args": ["run", "-v", "/var/run/docker.sock:/var/run/docker.sock", "img"]},
        "d": {"url": "http://tools.example.com/mcp"},
        "e": {"url": "http://localhost:3000/mcp"},
        "f": {"command": "node", "args": ["x.js"], "env": {"TOKEN": "ghp_" + "a" * 36}},
    }}
    write(tmp_path, ".mcp.json", json.dumps(cfg, indent=2))
    assert rules(tmp_path) == ["AP04", "AP04", "AP05", "AP07", "AP08"]


def test_secret_is_never_printed(tmp_path):
    secret = "sk-ant-" + "x" * 40
    write(tmp_path, ".mcp.json", json.dumps({"mcpServers": {"s": {"command": "node", "env": {"KEY": secret}}}}))
    out = tmp_path / "out.txt"
    with open(out, "w") as fh:
        scan.run(str(tmp_path), False, False, "none", out=fh)
    with open(out, "w") as fh:
        scan.run(str(tmp_path), False, True, "none", out=fh)
    assert secret not in out.read_text()


def test_lethal_combination(tmp_path):
    cfg = {"mcpServers": {"fetch": {"command": "uvx", "args": ["mcp-server-fetch==1.0"]},
                          "postgres": {"command": "node", "args": ["pg.js"]}}}
    write(tmp_path, ".mcp.json", json.dumps(cfg))
    assert rules(tmp_path) == ["AP09"]


def test_broad_shell_allow(tmp_path):
    write(tmp_path, ".claude/settings.json", json.dumps({"permissions": {"allow": ["Bash(*)", "Bash(npm test)"]}}))
    assert rules(tmp_path) == ["AP06"]


def test_ignores(tmp_path):
    write(tmp_path, "a.sh", "claude --dangerously-skip-permissions  # open-agent-security: ignore\n")
    write(tmp_path, "fixtures/b.sh", "claude --dangerously-skip-permissions\n")
    write(tmp_path, ".open-agent-security-ignore", "fixtures/\n")
    assert rules(tmp_path) == []


def test_docs_do_not_trigger_permission_rule(tmp_path):
    write(tmp_path, "README.md", "Never use --dangerously-skip-permissions.\n")
    assert rules(tmp_path) == []


def test_fail_on_threshold(tmp_path):
    write(tmp_path, "Dockerfile", "FROM python:3.12\n")
    with open(tmp_path / "o", "w") as fh:
        assert scan.run(str(tmp_path), False, True, "high", out=fh) == 0
        assert scan.run(str(tmp_path), False, True, "low", out=fh) == 1


def test_host_scan_reads_desktop_config(tmp_path, monkeypatch):
    monkeypatch.setattr(scan.platform, "system", lambda: "Linux")
    write(tmp_path, ".config/Claude/claude_desktop_config.json",
          json.dumps({"mcpServers": {"w": {"command": "npx", "args": ["web-mcp"]}}}))
    found, notes = scan.scan_host(None, home=tmp_path)
    assert [f.rule for f in found] == ["AP04"]
    assert found[0].file.startswith("~/")


def test_sarif_and_markdown(tmp_path):
    write(tmp_path, "run.sh", "claude --dangerously-skip-permissions\n")
    sf, md = tmp_path / "r.sarif", tmp_path / "s.md"
    with open(tmp_path / "o", "w") as fh:
        scan.run(str(tmp_path), False, True, "none", out=fh, sarif_path=str(sf), md_path=str(md))
    res = json.loads(sf.read_text())["runs"][0]["results"]
    assert res[0]["ruleId"] == "AP01" and res[0]["locations"][0]["physicalLocation"]["region"]["startLine"] == 1
    assert "permission checks turned off" in md.read_text()


def test_rules_match_anti_patterns_doc():
    doc = (TOOL_DIR.parent.parent / "ANTI-PATTERNS.md").read_text(encoding="utf-8")
    for rid, rule in scan.RULES.items():
        assert f"### {rid}: {rule[1]}\n" in doc, rid
        assert f"(#{scan.anchor(rid)})" in doc, rid
