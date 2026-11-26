"""The repository walk: which files are read, which folders are skipped, how text is decoded."""
import json
import os
import threading
import time

import pytest
from support import AGENT, FLAG, UNPINNED, config, report, result, rules, scan, write

from open_agent_security.collect.repo import is_script


def test_binary_fifo_and_symlink_are_skipped(tmp_path):
    (tmp_path / "a.json").write_bytes(b"\x00\x01\x02" * 100)
    os.mkfifo(tmp_path / "f.json")
    (tmp_path / "outside.sh").write_text("claude --dangerously-skip-permissions\n")
    sub = tmp_path / "repo"
    sub.mkdir()
    (sub / "link.sh").symlink_to(tmp_path / "outside.sh")
    start = time.process_time()
    assert rules(sub) == []
    assert rules(tmp_path) == ["AP01"]
    assert time.process_time() - start < 5


def test_hidden_ci_folders_are_scanned(tmp_path):
    write(tmp_path, ".circleci/config.yml", "run: claude --dangerously-skip-permissions\n")
    write(tmp_path, ".devcontainer/Dockerfile", "FROM python:3.12\n")
    write(tmp_path, ".mcp.json", AGENT)
    assert rules(tmp_path) == ["AP02", "AP10"]


def test_utf16_and_binary_notes(tmp_path):
    (tmp_path / "a.ps1").write_bytes("claude --dangerously-skip-permissions\n".encode("utf-16"))
    (tmp_path / "b.sh").write_bytes(b"\x00\x01binary")
    r = result(tmp_path)
    assert [f.rule for f in r.findings] == ["AP01"]
    assert any("binary" in n and "b.sh" in n for n in r.notes)


@pytest.mark.parametrize("data", [
    b"# c\r  - run: claude -p x --dangerously-skip-permissions\r",
    b"# c\r\n  - run: claude -p x --dangerously-skip-permissions\r\n",
])
def test_cr_line_endings(tmp_path, data):
    p = tmp_path / ".github/workflows/a.yml"
    p.parent.mkdir(parents=True)
    p.write_bytes(data)
    assert [(f.rule, f.line) for f in result(tmp_path).findings] == [("AP02", 2)]


@pytest.mark.parametrize("rel", ["src/pipeline/agent.py", "rag_pipeline.py", "data-pipeline/run.py", "ci_helpers/agent.py"])
def test_pipeline_named_paths_are_not_ci(tmp_path, rel):
    write(tmp_path, rel, 'ClaudeAgentOptions(permission_mode="bypassPermissions")\n')
    assert rules(tmp_path) == ["AP01"]


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="needs FIFOs")
def test_fifo_and_outside_symlink_are_not_opened(tmp_path):
    os.mkfifo(tmp_path / "pipe")
    outside = write(tmp_path.parent / f"{tmp_path.name}-out", "script", "#!/bin/sh\n")
    (tmp_path / "link").symlink_to(outside)
    results = {}
    t = threading.Thread(target=lambda: results.update(pipe=is_script(tmp_path / "pipe"),
                                                       link=is_script(tmp_path / "link")), daemon=True)
    t.start()
    t.join(5)
    assert not t.is_alive() and results == {"pipe": False, "link": False}


def test_a_nul_byte_in_a_comment_does_not_hide_a_script(tmp_path):
    write(tmp_path, "scripts/run.sh", f"#!/bin/sh\n# note \x00 here\nclaude -p hi {FLAG}\n".encode())
    assert rules(tmp_path) == ["AP01"]


def test_real_binary_files_are_still_skipped(tmp_path):
    write(tmp_path, "blob.json", bytes(range(256)) * 40)
    r = report(tmp_path)
    assert any("binary" in n for n in r["notes"]) and r["incomplete"] is False


@pytest.mark.parametrize("extra", ["", "x"])
def test_bytes_that_only_look_like_utf16_are_unreadable(tmp_path, extra):
    write(tmp_path, "scripts/run.sh", b"\xff\xfe\n" + f"claude -p hi{extra} {FLAG}\n".encode())
    r = report(tmp_path)
    assert r["incomplete"] is True and any("not valid UTF-16" in n for n in r["notes"])


def test_real_utf16_is_still_read(tmp_path):
    write(tmp_path, "run.sh", f"claude -p hi {FLAG}\n".encode("utf-16"))
    assert rules(tmp_path) == ["AP01"]


@pytest.mark.parametrize("folder", ["venv", ".cache", ".idea", ".next", ".terraform", ".tox", ".gradle"])
def test_tool_folders_are_scanned(tmp_path, folder):
    write(tmp_path, f"{folder}/.mcp.json", UNPINNED)
    write(tmp_path, f"{folder}/run.sh", f"claude -p hi {FLAG}\n")
    assert rules(tmp_path) == ["AP01", "AP04"]


def test_dependency_folders_are_skipped_and_counted(tmp_path):
    write(tmp_path, "node_modules/p/.mcp.json", UNPINNED)
    write(tmp_path, ".venv/pyvenv.cfg", "home = /usr\n")
    write(tmp_path, ".venv/lib/run.sh", f"claude -p hi {FLAG}\n")
    write(tmp_path, ".git/hooks/pre-commit.sh", f"claude -p hi {FLAG}\n")
    r = report(tmp_path)
    assert r["findings"] == [] and any("did not enter 2 dependency folders" in n for n in r["notes"])


def test_built_in_skipped_folders_are_counted(tmp_path):
    write(tmp_path, "tools/__pycache__/agent.sh", f"claude -p hi {FLAG}\n")
    write(tmp_path, ".svn/mcp.json", json.dumps({"mcpServers": {"s": {"command": "npx", "args": ["-y", "x"]}}}))
    write(tmp_path, ".hg/x.sh", "echo\n")
    write(tmp_path, ".git/hooks/pre-commit.sh", f"claude -p hi {FLAG}\n")  # no HEAD: not a real git folder
    notes = " ".join(report(tmp_path)["notes"])
    assert "did not enter 4 version-control or cache folders (.git, .hg, .svn, __pycache__)" in notes


def test_a_real_git_folder_is_skipped_silently(tmp_path):
    write(tmp_path, ".git/HEAD", "ref: refs/heads/main\n")
    write(tmp_path, "run.sh", "echo\n")
    r = report(tmp_path)
    assert r["notes"] == [] and "No known-dangerous" in scan(tmp_path)[1]


def test_one_list_of_agent_config_names():
    from open_agent_security import agents
    from open_agent_security.collect import repo
    assert not hasattr(repo, "AGENT_CONFIG_FILE")
    for name in (".gemini/settings.json", ".qwen/settings.json", "opencode.json", "opencode.jsonc",
                 "cline_mcp_settings.json", ".codex/config.toml", ".vscode/settings.json", ".cursor/mcp.json",
                 ".roo/mcp.json", ".mcp.json", ".claude/settings.json", "claude_desktop_config.json"):
        assert agents.CONFIG_FILE.search("sub/" + name), name


@pytest.mark.parametrize("name,text", [
    ("Justfile", f"run:\n    claude -p hi {FLAG}\n"), ("GNUmakefile", f"run:\n\tclaude -p hi {FLAG}\n"),
    ("makefile", f"run:\n\tclaude -p hi {FLAG}\n"), ("build.mk", f"run:\n\tclaude -p hi {FLAG}\n"),
    ("agent.bat", f"claude -p hi {FLAG}\r\n"), ("agent.cmd", f"claude -p hi {FLAG}\r\n"),
    ("agent.jsx", f'spawn("claude", ["-p", "hi", "{FLAG}"]);\n'), ("agent.mts", f'spawn("claude", ["{FLAG}"]);\n'),
    ("agent.cts", f'spawn("claude", ["{FLAG}"]);\n'), ("agent.fish", f"claude -p hi {FLAG}\n"),
])
def test_more_file_names_are_read(tmp_path, name, text):
    write(tmp_path, name, text)
    assert rules(tmp_path) == ["AP01"]


@pytest.mark.parametrize("name,rel", [("json", "reports/out.json"), ("sarif", "reports/out.sarif"),
                                      ("sarif", "reports/out.json"), ("gitlab-sast", "gl-sast-report.json")])
def test_the_scanners_own_reports_are_not_scanned(tmp_path, name, rel):
    write(tmp_path, "run.sh", f"claude {FLAG}\n")
    target = tmp_path.parent / "out"
    scan(tmp_path, "--fail-on", "none", "--output", f"{name}={target}")
    write(tmp_path, rel, target.read_text(encoding="utf-8"))
    if rel.endswith(".sarif"):
        config(tmp_path, {"include": ["**/*.sarif"]})
    r = report(tmp_path)
    assert [f["rule"] for f in r["findings"]] == ["AP01"]
    assert "skipped 1 open-agent-security report file" in r["notes"]


def test_a_junit_report_is_never_read(tmp_path):
    """The walk does not read .xml, so JUnit needs no skip, and JUnit-shaped text is never skipped."""
    write(tmp_path, "run.sh", f"claude {FLAG}\n")
    scan(tmp_path, "--fail-on", "none", "--output", f"junit={tmp_path / 'out.xml'}")
    r = report(tmp_path)
    assert [f["rule"] for f in r["findings"]] == ["AP01"] and not any("report file" in n for n in r["notes"])


JUNIT_HEAD = '<?xml\n{body}\n# ?><testsuites name="open-agent-security">\n'
SARIF_LIKE = json.dumps({"version": "2.1.0", "runs": [{"tool": {"driver": {"name": "open-agent-security"}}}]})


@pytest.mark.parametrize("rel,text", [
    ("run.sh", JUNIT_HEAD.format(body=f'claude {FLAG} -p "do it"')),
    ("run.bat", JUNIT_HEAD.format(body=f'claude {FLAG} -p "do it"')),
    ("Dockerfile", JUNIT_HEAD.format(body=f'RUN claude {FLAG} -p "do it"')),
    (".github/workflows/w.json", json.dumps({"version": "2.1.0", "runs": [
        {"tool": {"driver": {"name": "open-agent-security"}}, "x": f"claude {FLAG}"}]})),
    ("agent.py", f'# {SARIF_LIKE}\nimport os\nos.system("claude {FLAG} -p x")\n'),
    ("tool.json", json.dumps({"scanner": "open-agent-security", "findings": [], "version": "1",
                              "scripts": {"fix": f"claude {FLAG} -p fix"}})),
    ("tool.json", '{"scanner": "open-agent-security", "version": "1", "findings": []}\n'
                  + json.dumps({"scripts": {"fix": f"claude {FLAG} -p fix"}})),
])
def test_a_file_shaped_like_a_report_cannot_hide_a_bypass(tmp_path, rel, text):
    """Finding 1 (critical): only a whole, exact .json/.sarif report document is skipped."""
    write(tmp_path, rel, text)
    r = report(tmp_path)
    assert r["findings"] and not any("report file" in n for n in r["notes"])


def test_naming_the_scanner_in_agent_config_hides_nothing(tmp_path):
    write(tmp_path, ".mcp.json", json.dumps({"scanner": "open-agent-security", "findings": [],
                                             "mcpServers": {"s": {"command": "npx", "args": ["evil"]}}}))
    write(tmp_path, "x.json", json.dumps({"scanner": "open-agent-security", "findings": [], "args": [FLAG]}))
    assert rules(tmp_path) == ["AP01", "AP04"]


@pytest.mark.parametrize("name", [".zshrc", ".bashrc", ".bash_aliases", ".bash_profile", ".zprofile", ".profile",
                                  ".envrc", ".zshenv"])
def test_round9_shell_startup_files_are_read(tmp_path, name):
    write(tmp_path, name, "# alias c='claude --dangerously-skip-permissions'\n"
                          "alias c='claude --dangerously-skip-permissions'\n")
    assert [(f["rule"], f["line"]) for f in report(tmp_path)["findings"]] == [("AP01", 2)]
