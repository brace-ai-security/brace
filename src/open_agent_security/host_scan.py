"""Read MCP server settings from the machine where an agent runs.

The scanner's --host reads the files host_sources() lists; `topology.py build --host-config`
also turns them into records with read_host(). Nothing here starts a server, contacts a
network or scans tools: it only reads JSON files that already exist. What counts as a server
and where its URL and environment are come from parse/mcp_json.py, the scanner's own reader,
so the scan and the map cannot disagree.

What is kept from each server entry: the client, the file, the JSON key that holds the
entry, the server name, the transport, the command name and arguments (a command written
as one string is split first; secret-looking argument values redacted), and the URL without
user info, query or fragment. Every kept string except file paths is redacted. Never kept:
`env` values, header values, tokens. Only the *names* of `env` keys and headers are kept.

All file content is untrusted. Files over MAX_BYTES are refused, at most MAX_SERVERS
servers are read per file, and every string is cut to MAX_TEXT characters. Arguments go
through the scanner's redactor (secrets.redact_command). Callers escape the text when they
show it.

Host config locations (checked against vendor documentation, November 2026):

- Claude Desktop: `claude_desktop_config.json`, key `mcpServers`. macOS
  `~/Library/Application Support/Claude/`, Windows `%APPDATA%\\Claude\\`, Linux
  `~/.config/Claude/` (modelcontextprotocol.io, "Connect to local MCP servers").
- Claude Code: `~/.claude.json` (user scope `mcpServers`; local scope
  `projects["<path>"].mcpServers`), project `.mcp.json` (`mcpServers`), and
  `managed-mcp.json` at `/Library/Application Support/ClaudeCode/` (macOS),
  `/etc/claude-code/` (Linux, WSL), `C:\\Program Files\\ClaudeCode\\` (Windows)
  (code.claude.com/docs/en/mcp and /managed-mcp).
- Cursor: `~/.cursor/mcp.json` and project `.cursor/mcp.json`, key `mcpServers`
  (cursor.com/docs/context/mcp).
- VS Code: Copilot user file `~/.copilot/mcp-config.json` (or `$COPILOT_HOME`) and
  workspace `.mcp.json`, key `mcpServers`; the older editor-managed files
  `.vscode/mcp.json` and the profile `mcp.json` (in the VS Code user folder), key
  `servers` (code.visualstudio.com/docs/agents/reference/mcp-configuration).
- Windsurf: `~/.codeium/windsurf/mcp_config.json`, key `mcpServers` (older Windsurf
  documentation); its successor Devin Desktop uses `~/.config/devin/mcp_config.json`
  and project `.devin/mcp_config.json` (docs.devin.ai/desktop/cascade/mcp).
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from .fsio import ReadFailure, read
from .jsonc import load_json_text
from .limits import HOST_FILE_BYTES, MAX_VALUE
from .output import clean
from .parse.mcp_json import common_shape, entry_url, servers_at, split_words
from .secrets import redact_command

MAX_BYTES = HOST_FILE_BYTES
MAX_SERVERS = 500
MAX_TEXT = 300


def cut(x, redact: bool = True) -> str:
    """Printable, secret-redacted text of at most MAX_TEXT characters ('' for None). Only file
    paths pass redact=False: a path is shown as it is on disk."""
    return "" if x is None else clean(x, MAX_TEXT, redact=redact)


def host_sources(home: Path, system: str, project: Path | None = None, env: dict | None = None) -> list[dict]:
    """Known config files for this OS: [{client, path, keys}] where keys are JSON paths to server maps."""
    env = env if env is not None else os.environ
    appdata = Path(env.get("APPDATA") or home / "AppData" / "Roaming")
    copilot = Path(env.get("COPILOT_HOME") or home / ".copilot")
    if system == "Darwin":
        desktop = home / "Library/Application Support/Claude/claude_desktop_config.json"
        managed = Path("/Library/Application Support/ClaudeCode/managed-mcp.json")
        code_user = home / "Library/Application Support/Code/User/mcp.json"
    elif system == "Windows":
        desktop = appdata / "Claude" / "claude_desktop_config.json"
        managed = Path("C:/Program Files/ClaudeCode/managed-mcp.json")
        code_user = appdata / "Code" / "User" / "mcp.json"
    else:
        desktop = home / ".config/Claude/claude_desktop_config.json"
        managed = Path("/etc/claude-code/managed-mcp.json")
        code_user = home / ".config/Code/User/mcp.json"
    out = [
        {"client": "Claude Desktop", "path": desktop, "keys": ["mcpServers"]},
        {"client": "Claude Code", "path": home / ".claude.json", "keys": ["mcpServers", "projects.*.mcpServers"]},
        {"client": "Claude Code (managed)", "path": managed, "keys": ["mcpServers"]},
        {"client": "Cursor", "path": home / ".cursor/mcp.json", "keys": ["mcpServers"]},
        {"client": "VS Code (Copilot)", "path": copilot / "mcp-config.json", "keys": ["mcpServers"]},
        {"client": "VS Code (profile)", "path": code_user, "keys": ["servers"]},
        {"client": "Windsurf", "path": home / ".codeium/windsurf/mcp_config.json", "keys": ["mcpServers"]},
        {"client": "Devin Desktop", "path": home / ".config/devin/mcp_config.json", "keys": ["mcpServers"]},
    ]
    if project:
        out += [
            {"client": "Claude Code (project)", "path": project / ".mcp.json", "keys": ["mcpServers"]},
            {"client": "Cursor (project)", "path": project / ".cursor/mcp.json", "keys": ["mcpServers"]},
            {"client": "VS Code (workspace)", "path": project / ".vscode/mcp.json", "keys": ["servers"]},
            {"client": "Devin Desktop (project)", "path": project / ".devin/mcp_config.json", "keys": ["mcpServers"]},
        ]
    return out


def load_json(path: Path, limit: int | None = None):
    """Read a JSON (or JSONC) file as untrusted input. Returns (data, error)."""
    limit = MAX_BYTES if limit is None else limit
    text = read(path, follow=True, limit=limit)
    if isinstance(text, ReadFailure):
        if text.reason == "oversized":
            return None, f"{path.name} is larger than {limit // (1024 * 1024)} MB; skipped"
        return None, f"{path.name}: {text.reason}"
    data, err = load_json_text(text)
    return (None, f"{path.name}: {err}") if err else (data, None)


def clean_url(url: str) -> str:
    try:
        u = urlsplit(str(url))
    except ValueError:
        return ""
    host = u.hostname or ""
    try:
        port = u.port
    except ValueError:  # e.g. http://h:abc/ - keep the host, drop the bad port
        port = None
    if port:
        host += f":{port}"
    return cut(urlunsplit((u.scheme, host, u.path, "", "")))


def server_record(name: str, entry: dict, client: str, file: str, key: str) -> dict:
    entry = common_shape(entry if isinstance(entry, dict) else {})
    url = entry_url(entry)
    transport = entry.get("type") or entry.get("transport") or ("stdio" if entry.get("command") else
                                                                 "http" if url else "unknown")
    env, headers = entry.get("env"), entry.get("headers")
    command = entry.get("command")
    command = str(command) if isinstance(command, (str, int, float)) else ""
    args = entry.get("args")
    args = [a for a in args if isinstance(a, (str, int, float))] if isinstance(args, list) else []
    if not args and len(command.split()) > 1:  # `"command": "npx --api-key=... pkg"`
        command, *args = split_words(command[:MAX_VALUE])
    return {"name": cut(name), "client": client, "file": cut(file, redact=False), "key": cut(key),
            "transport": cut(transport), "url": clean_url(url) if url else "",
            "command": cut(Path(command.replace("\\", "/")).name) if command else "",
            "args": [cut(a) for a in redact_command(args[:40])],
            "env_keys": sorted(cut(k) for k in env)[:50] if isinstance(env, dict) else [],
            "header_keys": sorted(cut(k) for k in headers)[:50] if isinstance(headers, dict) else []}


def json_key(path: tuple) -> str:
    """A server's JSON path as shown: `mcpServers.name`, or `projects."/path".mcpServers.name`."""
    return ".".join(json.dumps(p) if i == 1 and path[0] == "projects" else str(p) for i, p in enumerate(path))


def read_host(sources: list[dict], project: Path | None = None) -> tuple[list[dict], list[str]]:
    """Servers from every source file that exists. Returns (records, notes).

    `projects.*.mcpServers` reads only the entry for `project` (the repository being built)."""
    records, notes = [], []
    for src in sources:
        path = Path(src["path"])
        if not path.is_file():
            continue
        data, err = load_json(path)
        if err:
            notes.append(err)
            continue
        # `projects.*.mcpServers` is read only for the project being mapped, never for others.
        keys = [k for k in src["keys"] if project is not None or k != "projects.*.mcpServers"]
        found = servers_at(data, keys, project)
        if len(found) > MAX_SERVERS:
            notes.append(f"{path.name}: more than {MAX_SERVERS} servers; the rest skipped")
        for jpath, name, entry in found[:MAX_SERVERS]:
            records.append(server_record(name, entry, src["client"], str(path), json_key(jpath)))
    return records, notes
