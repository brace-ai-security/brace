"""Output cannot carry terminal controls, workflow commands or links from scanned names."""
import json
import os
import re

from support import FLAG, ROOT, cli_run, config, mcp, run, scan, write

from open_agent_security.catalog import RULES
from open_agent_security.model import Finding, Report
from open_agent_security.output import inert
from open_agent_security.report import ReportOptions
from open_agent_security.report.text import Text


def test_file_names_are_sanitised(tmp_path):
    name = "a\x1b[2Jb`[x](https:evil)`.sh"
    write(tmp_path, name, "claude --dangerously-skip-permissions\n")
    sf, md = tmp_path / "r.sarif", tmp_path / "s.md"
    _, text = run(tmp_path, sarif_path=str(sf), md_path=str(md))
    assert "\x1b" not in text
    uri = json.loads(sf.read_text())["runs"][0]["results"][0]["locations"][0]["physicalLocation"]["artifactLocation"]["uri"]
    assert "\x1b" not in uri and " " not in uri and "`" not in uri
    row = [ln for ln in md.read_text().splitlines() if ln.startswith("| high")][0]
    assert "](https:evil)" not in row and "`" not in row.replace("\\`", "")


def test_text_output_cannot_issue_workflow_commands(tmp_path, monkeypatch):
    write(tmp_path, "::error file=src%2Fapp.py,line=1::Injected annotation/run.sh", f"claude -p x {FLAG}\n")
    mcp(tmp_path, {"command": "npx", "args": ["-y", "x"]})
    data = json.loads((tmp_path / ".mcp.json").read_text())
    data["mcpServers"]["##[error]pwned ::warning::x"] = data["mcpServers"].pop("s0")
    write(tmp_path, ".mcp.json", json.dumps(data))
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    out = scan(tmp_path, "--fail-on", "none")[1]
    assert "Injected annotation" in out and "pwned" in out
    assert not re.search(r"^\s*::", out, re.M) and "##[" not in out
    monkeypatch.delenv("GITHUB_ACTIONS")
    assert "##[" in scan(tmp_path, "--fail-on", "none")[1]


def test_defuse_covers_colour_codes_and_indentation():
    r = Report(findings=[Finding("AP01", "::add-mask::x", 1, "::stop-commands::y", severity="high")],
               rules=RULES, notes=["  ::error::z"])
    out = inert(Text().render(r, ReportOptions(color=True)), Text.media)  # as the CLI writes it to a log
    plain = re.sub(r"\x1b\[[0-9;]*m", "", out)
    assert not re.search(r"^\s*::", plain, re.M)


def test_action_stops_workflow_commands_with_a_random_token():
    text = (ROOT / "action.yml").read_text()
    assert "secrets.token_hex(16)" in text and 'echo "::stop-commands::$TOKEN"' in text
    assert text.index("stop-commands") < text.index('"$PY" -I "$SCANNER"') < text.index('echo "::$TOKEN::"')
    assert "github.action_path" not in text and "$GITHUB_ACTION_PATH/tools/brace/scan.py" in text


def test_json_and_errors_cannot_issue_workflow_commands(tmp_path, monkeypatch):
    mcp(tmp_path, {"command": "npx", "args": ["-y", "x"]}, rel="##[error]pwned/.mcp.json")
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    out = scan(tmp_path, "--json", "--fail-on", "none")[1]
    assert "##[" not in out and json.loads(out)["findings"][0]["file"].startswith("##[error]pwned")
    config(tmp_path, {"##[error]bad": 1})
    code, out = scan(tmp_path)
    assert code == 2 and "##[" not in out and not re.search(r"^\s*::", out, re.M)


def test_markdown_names_are_not_autolinked(tmp_path):
    mcp(tmp_path, {"command": "npx", "args": ["-y", "x"]}, rel="www.evil.example/.mcp.json")
    md = tmp_path.parent / (tmp_path.name + ".md")
    cli_run(tmp_path, "--fail-on", "none", "--markdown", str(md))
    assert "www\\.evil\\.example" in md.read_text(encoding="utf-8")


def test_markdown_names_and_notes_do_not_mention_anyone(tmp_path):
    write(tmp_path, "@octocat.sh", f"claude {FLAG}\n")
    write(tmp_path, ".mcp.json", "{}")
    os.symlink("/etc/hosts", tmp_path / "@hubot.sh")
    md = tmp_path.parent / (tmp_path.name + ".md")
    cli_run(tmp_path, "--fail-on", "none", "--markdown", str(md))
    text = md.read_text(encoding="utf-8")
    assert "\\@octocat" in text and "\\@hubot" in text
    assert re.search(r"(?<!\\)@\w", text) is None
