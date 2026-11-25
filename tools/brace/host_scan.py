"""Read MCP server settings from the machine where an agent runs, or import scanner output.

Used by `topology.py build --host-config ... --import-scan ...`. Nothing here starts a
server, contacts a network or scans tools: it only reads JSON files that already exist.

What is kept from each server entry: the client, the file, the JSON key that holds the
entry, the server name, the transport, the command name and arguments (secret-looking
argument values redacted), and the URL without user info, query or fragment. Never kept:
`env` values, header values, tokens. Only the *names* of `env` keys and headers are kept.

All file content is untrusted. Files over MAX_BYTES are refused, at most MAX_SERVERS
servers are read per file, and every string is cut to MAX_TEXT characters. Callers escape
the text when they show it.

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
import re
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

MAX_BYTES = 5 * 1024 * 1024
MAX_SERVERS = 500
MAX_TEXT = 300
SECRET_FLAG = re.compile(r"(token|secret|password|passwd|api[-_]?key|credential|auth)", re.I)
SECRET_VALUE = re.compile(r"^(sk-|ghp_|gho_|xox[abp]-|AKIA|lgr_pat_|eyJ)|[A-Za-z0-9_\-]{32,}")


def _cut(x) -> str:
    s = "" if x is None else str(x)
    s = "".join(ch for ch in s if ch.isprintable())
    return s if len(s) <= MAX_TEXT else s[: MAX_TEXT - 1] + "…"


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


def load_json(path: Path):
    """Read a JSON file as untrusted input. Returns (data, error)."""
    try:
        if path.stat().st_size > MAX_BYTES:
            return None, f"{path.name} is larger than {MAX_BYTES // (1024 * 1024)} MB; skipped"
        return json.loads(path.read_text(encoding="utf-8", errors="replace")), None
    except (OSError, ValueError) as e:
        return None, f"{path.name}: {type(e).__name__}"


def clean_url(url: str) -> str:
    try:
        u = urlsplit(str(url))
    except ValueError:
        return ""
    host = u.hostname or ""
    if u.port:
        host += f":{u.port}"
    return _cut(urlunsplit((u.scheme, host, u.path, "", "")))


def redact_args(args) -> list[str]:
    out, hide = [], False
    for a in map(str, args if isinstance(args, list) else []):
        if hide:
            out.append("<redacted>")
            hide = False
        elif "=" in a and SECRET_FLAG.search(a.split("=", 1)[0]):
            out.append(a.split("=", 1)[0] + "=<redacted>")
        elif SECRET_VALUE.search(a) and not a.startswith(("-", "/", ".", "@")):
            out.append("<redacted>")
        else:
            out.append(_cut(a))
            hide = a.startswith("-") and bool(SECRET_FLAG.search(a))
    return out


def server_record(name: str, entry: dict, client: str, file: str, key: str) -> dict:
    entry = entry if isinstance(entry, dict) else {}
    transport = entry.get("type") or entry.get("transport") or ("stdio" if entry.get("command") else
                                                                 "http" if entry.get("url") else "unknown")
    rec = {"name": _cut(name), "client": client, "file": _cut(file), "key": _cut(key), "transport": _cut(transport),
           "url": clean_url(entry["url"]) if entry.get("url") else "",
           "command": _cut(Path(str(entry.get("command"))).name) if entry.get("command") else "",
           "args": redact_args(entry.get("args"))[:40],
           "env_keys": sorted(_cut(k) for k in (entry.get("env") or {}) if isinstance(entry.get("env"), dict))[:50],
           "header_keys": sorted(_cut(k) for k in (entry.get("headers") or {}) if isinstance(entry.get("headers"), dict))[:50]}
    return rec


def servers_in(data, key: str):
    """Yield (json key, name, entry) for a key such as `mcpServers` or `projects.*.mcpServers`."""
    if not isinstance(data, dict):
        return
    head, _, rest = key.partition(".")
    if head == "*":
        for k, v in data.items():
            for jk, n, e in servers_in(v, rest):
                yield f"{json.dumps(k)}.{jk}", n, e
        return
    val = data.get(head)
    if rest:
        for jk, n, e in servers_in(val, rest):
            yield f"{head}.{jk}", n, e
    elif isinstance(val, dict):
        for n, e in val.items():
            yield f"{head}.{n}", n, e


def read_host(sources: list[dict]) -> tuple[list[dict], list[str]]:
    """Servers from every source file that exists. Returns (records, notes)."""
    records, notes = [], []
    for src in sources:
        path = Path(src["path"])
        if not path.is_file():
            continue
        data, err = load_json(path)
        if err:
            notes.append(err)
            continue
        n = 0
        for key in src["keys"]:
            for jk, name, entry in servers_in(data, key):
                if n >= MAX_SERVERS:
                    notes.append(f"{path.name}: more than {MAX_SERVERS} servers; the rest skipped")
                    break
                records.append(server_record(name, entry, src["client"], str(path), jk))
                n += 1
    return records, notes


# ------------------------------------------------------------------ scanner imports
def import_scan(path: Path) -> tuple[list[dict], list[str]]:
    """Import Snyk Agent Scan (`--json`, v0.5 path-keyed or v0.6 `scan_path_responses`)
    or Cisco mcp-scanner (`--format raw`) output. Returns (records, notes); each record is
    a server with `issues` [{tool, code, severity, message}]."""
    data, err = load_json(path)
    if err:
        return [], [err]
    if isinstance(data, dict) and "scan_results" in data and "server_url" in data:
        return _cisco([data], path), []
    if isinstance(data, list) and data and all(isinstance(x, dict) and "scan_results" in x for x in data):
        return _cisco(data, path), []
    if isinstance(data, dict) and isinstance(data.get("scan_path_responses"), list):
        return _snyk_v06(data["scan_path_responses"], path), []
    if isinstance(data, dict) and data and all(isinstance(v, dict) and "servers" in v for v in data.values()):
        return _snyk_v05(data, path), []
    return [], [f"{path.name}: not a recognised Snyk Agent Scan or Cisco mcp-scanner JSON file"]


def _scanner_record(name, client, file, key, server: dict | None, scanner: str) -> dict:
    rec = server_record(name, server or {}, client, file, key)
    rec["scanner"] = scanner
    rec["issues"] = []
    return rec


def _snyk_v05(data: dict, path: Path) -> list[dict]:
    out = []
    for scan_path, res in list(data.items())[:MAX_SERVERS]:
        servers = res.get("servers") or []
        recs = []
        for i, s in enumerate(servers[:MAX_SERVERS]):
            if not isinstance(s, dict):
                continue
            rec = _scanner_record(s.get("name") or f"server-{i}", _cut(res.get("client") or "unknown client"),
                                  str(path), f"{_cut(scan_path)}#servers[{i}]", s.get("server"), "Snyk Agent Scan")
            tools = ((s.get("signature") or {}).get("tools") or []) if isinstance(s.get("signature"), dict) else []
            rec["tools"] = [_cut(t.get("name")) for t in tools[:200] if isinstance(t, dict)]
            recs.append(rec)
            out.append(rec)
        for issue in (res.get("issues") or [])[:2000]:
            if not isinstance(issue, dict):
                continue
            ref = issue.get("reference") or [None, None]
            si = ref[0] if isinstance(ref, list) and ref and isinstance(ref[0], int) else None
            if si is None or not 0 <= si < len(recs):
                continue
            ti = ref[1] if len(ref) > 1 and isinstance(ref[1], int) else None
            tools = recs[si].get("tools", [])
            recs[si]["issues"].append({"tool": tools[ti] if ti is not None and 0 <= ti < len(tools) else "",
                                       "code": _cut(issue.get("code")), "severity": "",
                                       "message": _cut(issue.get("message"))})
    return out


def _snyk_v06(responses: list, path: Path) -> list[dict]:
    out = []
    for resp in responses[:MAX_SERVERS]:
        if not isinstance(resp, dict):
            continue
        for i, s in enumerate((resp.get("server_risks") or [])[:MAX_SERVERS]):
            if not isinstance(s, dict):
                continue
            rec = _scanner_record(s.get("name") or f"server-{i}", _cut(resp.get("client") or "unknown client"),
                                  str(path), f"{_cut(resp.get('path'))}#server_risks[{i}]", None, "Snyk Agent Scan")
            ents = [e for e in (s.get("entities") or []) if isinstance(e, dict)]
            rec["tools"] = [_cut(e.get("name")) for e in ents if e.get("type") == "tool"][:200]
            for risk, v in list((s.get("risk_indexes") or {}).items())[:200]:
                v = v if isinstance(v, dict) else {}
                hit = [ents[k].get("name") for k in v.get("affected_tools") or []
                       if isinstance(k, int) and 0 <= k < len(ents)]
                rec["issues"].append({"tool": _cut(", ".join(map(str, hit))), "code": _cut(risk),
                                      "severity": f"score {_cut(v.get('score'))}", "message": _cut(v.get("evidence"))})
            out.append(rec)
    return out


def _cisco(results: list, path: Path) -> list[dict]:
    out = []
    for k, r in enumerate(results[:MAX_SERVERS]):
        url = r.get("server_url") or ""
        items = [x for x in (r.get("scan_results") or []) if isinstance(x, dict)][:2000]
        name = next((x.get("server_name") for x in items if x.get("server_name")), None) or urlsplit(str(url)).hostname \
            or str(url) or f"server-{k}"
        server = {"url": url} if str(url).startswith(("http://", "https://")) else {"command": url}
        rec = _scanner_record(name, "Cisco mcp-scanner target", str(path), f"[{k}].server_url", server,
                              "Cisco mcp-scanner")
        rec["tools"] = [_cut(x.get("tool_name")) for x in items if x.get("tool_name")][:200]
        for x in items:
            for analyzer, f in (x.get("findings") or {}).items():
                if not isinstance(f, dict) or not f.get("total_findings"):
                    continue
                rec["issues"].append({"tool": _cut(x.get("tool_name") or x.get("prompt_name") or x.get("resource_name")),
                                      "code": _cut(", ".join(map(str, f.get("threat_names") or [])) or analyzer),
                                      "severity": _cut(f.get("severity")),
                                      "message": _cut(f.get("threat_summary"))})
        out.append(rec)
    return out
