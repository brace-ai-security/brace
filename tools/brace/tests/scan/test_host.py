"""The host scan (--host): agent settings on this machine."""
import json
import platform

from support import ROOT, host_result, write


def test_host_scan_reads_desktop_config_and_settings(tmp_path, monkeypatch):
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    monkeypatch.setenv("HOME", str(tmp_path))
    write(tmp_path, ".config/Claude/claude_desktop_config.json",
          json.dumps({"mcpServers": {"w": {"command": "npx", "args": ["web-mcp"]}}}))
    write(tmp_path, ".claude/settings.json",
          json.dumps({"permissions": {"defaultMode": "bypassPermissions", "allow": ["Bash(*)"]}}))
    r = host_result(tmp_path / "project")
    assert sorted(f.rule for f in r.findings) == ["AP01", "AP04", "AP06"]
    assert all(f.file.startswith("~/") for f in r.findings)


def test_host_follows_symlinks_and_large_files(tmp_path, monkeypatch):
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    monkeypatch.setenv("HOME", str(tmp_path))
    real = write(tmp_path, "dotfiles/claude.json", json.dumps({"mcpServers": {"w": {"command": "npx", "args": ["web-mcp"]}}}))
    (tmp_path / ".claude.json").symlink_to(real)
    write(tmp_path, ".claude/settings.json",
          json.dumps({"permissions": {"defaultMode": "bypassPermissions"}, "pad": " " * 1_100_000}))
    r = host_result(tmp_path / "project")
    assert sorted(f.rule for f in r.findings) == ["AP01", "AP04"] and all(f.host for f in r.findings)


def test_anti_patterns_lists_devin_desktop_for_host_scans():
    text = (ROOT / "ANTI-PATTERNS.md").read_text()
    assert "Devin Desktop" in text
