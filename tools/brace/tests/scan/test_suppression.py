"""Every suppression is reported: ignore entries, inline marks and rules turned off."""
import json

import pytest
from support import EVIL, all_outputs, config, found, noise, report, scan, six_servers, write

from open_agent_security.ignore import IGNORE_FILE


@pytest.mark.parametrize("hide", ["mark", "ignore-file", "rule-off"])
def test_suppressed_findings_do_not_use_up_the_cap(tmp_path, hide):
    note = noise(" open-agent-security: ignore" if hide == "mark" else "")
    write(tmp_path, ".mcp.json", json.dumps({"_note": note, "mcpServers": {"evil": EVIL}}, indent=2) + "\n")
    if hide == "ignore-file":
        write(tmp_path, IGNORE_FILE, "AP01 .mcp.json\n")
    if hide == "rule-off":
        config(tmp_path, {"rules": {"AP01": "off"}})
    rules = {r for r, _ in found(tmp_path)}
    assert {"AP04", "AP05"} <= rules and "AP01" not in rules
    assert scan(tmp_path)[0] == 1


def test_ignore_file_star_is_reported(tmp_path):
    root = tmp_path / "r"
    six_servers(root)
    write(root, IGNORE_FILE, "*\n")
    for out in all_outputs(root):
        assert f"{IGNORE_FILE}: 1 entry" in out and "1 file not scanned because of ignore entries" in out


def test_rule_scoped_ignore_entry_is_reported_in_text(tmp_path):
    root = tmp_path / "r"
    six_servers(root)
    write(root, IGNORE_FILE, "AP04 .mcp.json\n")
    for out in all_outputs(root):
        assert "6 findings suppressed" in out


def test_config_path_ignores_count_skipped_files(tmp_path):
    six_servers(tmp_path)
    write(tmp_path, ".github/workflows/a.yml", "on: push\njobs: {a: {steps: [{run: claude -p x --dangerously-skip-permissions}]}}\n")
    write(tmp_path, ".github/workflows/b.yml", "on: push\n")
    config(tmp_path, {"ignore": [{"path": ".github/"}, {"path": ".mcp.json"}]})
    notes = report(tmp_path)["notes"]
    assert any("0 findings suppressed; 1 file and 1 folder not scanned because of ignore entries" in n for n in notes)


def test_inline_marks_are_reported(tmp_path):
    write(tmp_path, "run.sh", "claude --dangerously-skip-permissions  # open-agent-security: ignore\n")
    notes = report(tmp_path)["notes"]
    assert any("inline ignore marks: 1 finding; 1 finding suppressed" in n for n in notes)
