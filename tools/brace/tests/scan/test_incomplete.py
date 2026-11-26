"""An incomplete scan never reports clean: skipped, oversized, unreadable and unparseable files, crashes and caps."""
import json
import os
import platform
from pathlib import Path

import pytest
from support import (
    AGENT,
    EVIL,
    FLAG,
    UNPINNED,
    cli_run,
    config,
    limits,
    mcp,
    needs_symlinks,
    noise,
    report,
    result,
    run,
    scan,
    write,
)

from open_agent_security.catalog import RULES
from open_agent_security.model import Report
from open_agent_security.report import ReportOptions
from open_agent_security.report.markdown import Markdown


def small_limit(root: Path) -> None:
    config(root, {"limits": {"max-file-bytes": 1024}})


def test_unparseable_agent_config_is_a_note(tmp_path):
    write(tmp_path, ".mcp.json", '{"mcpServers": {')
    r = result(tmp_path)
    assert r.findings == [] and any("could not parse .mcp.json" in n for n in r.notes)


def test_truncated_scan_is_never_clean(tmp_path):
    for i in range(5):
        write(tmp_path, f"f{i}.sh", "echo hi\n")
    code, text = run(tmp_path, fail_on="high", args=limits(tmp_path, max_files=3))
    assert code == 1 and "No known-dangerous" not in text and "stopped after 3 files" in text


def test_oversized_files_are_noted(tmp_path):
    write(tmp_path, "big.sh", "claude --dangerously-skip-permissions\n")
    assert "skipped 1 file(s)" in run(tmp_path, args=limits(tmp_path, max_file_bytes=10))[1]


def test_oversized_or_broken_agent_config_is_incomplete(tmp_path):
    write(tmp_path, ".mcp.json", json.dumps({"mcpServers": {"s": {"command": "npx", "args": ["x"]}}}) + " " * 100)
    code, text = run(tmp_path, fail_on="high", args=limits(tmp_path, max_file_bytes=50))
    assert code == 1 and "No known-dangerous" not in text and "incomplete" in text
    write(tmp_path, ".mcp.json", '{"mcpServers": ')
    assert run(tmp_path, fail_on="high")[0] == 1
    assert run(tmp_path, fail_on="none")[0] == 0


def test_host_incomplete_fails_the_scan(tmp_path, monkeypatch):
    home, proj = tmp_path / "home", tmp_path / "proj"
    proj.mkdir()
    write(home, ".cursor/mcp.json", '{"mcpServers": {')
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    code, out, _ = cli_run(proj, "--host", "--fail-on", "high")
    assert code == 1 and "No known-dangerous" not in out


def test_unreadable_folder_is_noted(tmp_path):
    d = tmp_path / "locked"
    d.mkdir()
    write(tmp_path, "locked/.mcp.json", AGENT)
    d.chmod(0)
    try:
        r = result(tmp_path)
    finally:
        d.chmod(0o755)
    if os.geteuid() != 0:
        assert any("locked/" in n for n in r.notes)


def test_a_capped_file_makes_the_scan_incomplete_and_later_checks_still_run(tmp_path):
    write(tmp_path, ".mcp.json", json.dumps({"_note": noise(), "mcpServers": {"evil": EVIL}}, indent=2) + "\n")
    r = report(tmp_path)
    rules = [f["rule"] for f in r["findings"]]
    assert rules.count("AP01") == 100 and "AP04" in rules and "AP05" in rules
    assert r["incomplete"] and any("more than 100 findings" in n for n in r["notes"])


@needs_symlinks
def test_symlinked_agent_config_makes_the_scan_incomplete(tmp_path):
    write(tmp_path, "agent.txt", UNPINNED)
    write(tmp_path, "claude.txt", json.dumps({"permissions": {"defaultMode": "bypassPermissions"}}))
    (tmp_path / ".mcp.json").symlink_to("agent.txt")
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "settings.json").symlink_to("../claude.txt")
    r = report(tmp_path)
    assert r["incomplete"] is True
    assert any("symlink" in n and ".mcp.json" in n and ".claude/settings.json" in n for n in r["notes"])
    code, out = scan(tmp_path)
    assert code == 1 and "No known-dangerous" not in out


@needs_symlinks
def test_other_symlinks_are_counted_in_a_note_only(tmp_path):
    write(tmp_path, "README.md", "hi\n")
    (tmp_path / "CLAUDE.md").symlink_to("README.md")
    r = report(tmp_path)
    assert r["incomplete"] is False and any("1 symlink(s), not followed: CLAUDE.md" in n for n in r["notes"])
    assert "1 file could not be read" in scan(tmp_path)[1]  # review 6, finding 3: every symlink hedges the headline


@needs_symlinks
def test_symlinked_claude_folder_is_not_followed_and_makes_the_scan_incomplete(tmp_path):
    write(tmp_path, "shared/settings.json", json.dumps({"permissions": {"defaultMode": "bypassPermissions"}}))
    (tmp_path / ".claude").symlink_to("shared")
    assert report(tmp_path)["incomplete"] is True


def test_oversized_workflow_makes_the_scan_incomplete(tmp_path):
    pad = "# " + "x" * 100 + "\n"
    text = "on: pull_request_target\njobs:\n  a:\n    steps:\n      - run: claude -p hi " + FLAG + "\n"
    write(tmp_path, ".github/workflows/a.yml", text + pad * (1100 * 1024 // len(pad)))
    r = report(tmp_path)
    assert r["incomplete"] is True and scan(tmp_path)[0] == 1


def test_skipped_files_never_get_the_clean_headline(tmp_path):
    write(tmp_path, "data.py", "x = 1\n" * 300_000)  # oversized, not a file the rules require
    r = report(tmp_path)
    assert r["incomplete"] is False
    out = scan(tmp_path)[1]
    assert "No known-dangerous" not in out and "1 file could not be read" in out
    md = Markdown().render(Report(rules=RULES, skipped=2), ReportOptions())
    assert "no known-dangerous" not in md.lower() and "2 files could not be read" in md


@needs_symlinks
@pytest.mark.parametrize("rel", [".gemini/settings.json", "scripts/run.sh", "Dockerfile", ".github/workflows/ci.yml",
                                 ".gitlab-ci.yml"])
def test_a_symlinked_file_the_rules_need_makes_the_scan_incomplete(tmp_path, rel):
    write(tmp_path, "elsewhere.txt", "x\n")
    (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / rel).symlink_to(tmp_path / "elsewhere.txt")
    code, out = scan(tmp_path, "--fail-on", "none")
    assert report(tmp_path)["incomplete"] is True and "No known-dangerous" not in out


@needs_symlinks
def test_every_skipped_symlink_hedges_the_headline(tmp_path):
    write(tmp_path, "README.md", "hi\n")
    (tmp_path / "docs.md").symlink_to(tmp_path / "README.md")
    (tmp_path / "linked").symlink_to(tmp_path)
    out = scan(tmp_path)[1]
    assert "2 files could not be read" in out and "No known-dangerous" not in out


@pytest.mark.parametrize("rel", [".gemini/settings.json", ".qwen/settings.json", "opencode.json", "opencode.jsonc",
                                 "cline_mcp_settings.json", ".codex/config.toml", ".vscode/settings.json",
                                 ".cursor/mcp.json", ".roo/mcp.json"])
def test_an_oversized_agent_config_makes_the_scan_incomplete(tmp_path, rel):
    small_limit(tmp_path)
    write(tmp_path, rel, "{" + " " * 2000 + "}\n")
    assert report(tmp_path)["incomplete"] is True


def test_an_oversized_source_file_with_a_bypass_makes_the_scan_incomplete(tmp_path):
    small_limit(tmp_path)
    write(tmp_path, "agent.py", "# padding\n" * 300 + f'ARGS = ["claude", "{FLAG}"]\n')
    write(tmp_path, "bundle.js", "var a = 1;\n" * 300)
    r = report(tmp_path)
    assert r["incomplete"] is True and any("agent.py" in n for n in r["notes"])
    (tmp_path / "agent.py").unlink()
    assert report(tmp_path)["incomplete"] is False


@pytest.mark.skipif(os.name == "nt" or (hasattr(os, "geteuid") and os.geteuid() == 0), reason="needs chmod")
@pytest.mark.parametrize("folder", [".claude", ".github/workflows", ".gemini", ".circleci"])
def test_an_unreadable_agent_or_ci_folder_makes_the_scan_incomplete(tmp_path, folder):
    write(tmp_path, f"{folder}/x.yml", "x: 1\n")
    write(tmp_path, "plain/x.txt", "x\n")
    os.chmod(tmp_path / folder, 0)
    try:
        r = report(tmp_path)
        code = scan(tmp_path, "--fail-on", "high")[0]
    finally:
        os.chmod(tmp_path / folder, 0o755)
    assert r["incomplete"] is True and code == 1


@pytest.mark.skipif(os.name == "nt" or (hasattr(os, "geteuid") and os.geteuid() == 0), reason="needs chmod")
def test_an_unreadable_ordinary_folder_is_only_noted(tmp_path):
    write(tmp_path, "data/x.txt", "x\n")
    os.chmod(tmp_path / "data", 0)
    try:
        r = report(tmp_path)
    finally:
        os.chmod(tmp_path / "data", 0o755)
    assert r["incomplete"] is False and any("data/ (folder)" in n for n in r["notes"])


def test_findings_before_a_check_fails_are_kept(tmp_path, monkeypatch):
    from open_agent_security.checks.mcp_servers import McpServers
    original = McpServers.run

    def flaky(self, doc, ctx):
        yield from original(self, doc, ctx)
        raise RuntimeError("late failure")
    monkeypatch.setattr(McpServers, "run", flaky)
    mcp(tmp_path, {"command": "npx", "args": ["-y", "x"]})
    r = report(tmp_path)
    assert [f["rule"] for f in r["findings"]] == ["AP04"] and r["incomplete"] is True
