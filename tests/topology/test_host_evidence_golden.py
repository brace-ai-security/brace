"""Byte-for-byte snapshot of the host evidence topology.py reads: settings files and imported
scanner output. It pins what the map shows while the host reader shares the scanner's code.
Regenerate on purpose with OAS_UPDATE_GOLDEN=1 and review the diff."""
import json
import os
import re
from pathlib import Path

from brace_tools.topology import core as topology
from conftest import TOOL_DIR

HS = TOOL_DIR / "examples" / "host-scan"
GOLDEN = TOOL_DIR.parent.parent / "tests" / "fixtures" / "host_evidence.json"


def normalise_checkout(text: str) -> str:
    """Replace where this checkout lives with TOOL_DIR, however the path is written (absolute, or
    ~/ relative to whatever home folder the host reader resolved), so the snapshot is the same on
    every machine and in CI."""
    return re.sub(r'(?<=")[^"\n]*?(?=/examples/host-scan/)', "TOOL_DIR", text)


def test_host_evidence_golden(tmp_path):
    home = tmp_path / "home"
    (home / ".cursor").mkdir(parents=True)
    (home / ".cursor" / "mcp.json").write_text((HS / "claude_desktop_config.json").read_text(encoding="utf-8"))
    (home / ".claude.json").write_text(json.dumps({"mcpServers": {"shell": {
        "command": "bash", "args": ["-c", "npx -y some-mcp"], "env": {"K": {"nested": 1}}}}, "projects": {
        "/w/app": {"mcpServers": {"crm": {"type": "http", "url": "https://user:pw@crm.example/mcp?x=1#y",
                                          "headers": {"Authorization": "Bearer abc"}},
                                  "odd": {"serverUrl": "https://odd.example/sse", "args": ["--token", "short"]}}}}}))
    recs, notes = topology.host_evidence(Path("/w/app"), True, [HS / "claude_desktop_config.json"],
                                         sorted(HS.glob("*scan*.json")), home=home, system="Linux")
    text = json.dumps({"records": recs, "notes": notes}, indent=2, sort_keys=True).replace(str(tmp_path), "TMP")
    text = normalise_checkout(text) + "\n"
    if os.environ.get("OAS_UPDATE_GOLDEN"):
        GOLDEN.write_text(text, encoding="utf-8")
    assert text == GOLDEN.read_text(encoding="utf-8")
