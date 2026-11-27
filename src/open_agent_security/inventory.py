"""What a scan saw, as an inventory: each agent config file and each MCP server in it.

The CycloneDX reporter (report/cyclonedx.py) renders it. Everything kept is what host_scan
keeps for the host map: names, the transport, the program and redacted arguments, the URL's
scheme and host only, and the *names* of env keys and headers, never their values. Packages
and images are kept only in the shape a finding would show them (shown_package, shown_image),
so a credential passed where a package was expected becomes <redacted>.

The inventory is bounded (MAX_INVENTORY entries); past it, the scan notes that it stopped
listing, and the BOM says so.
"""
from __future__ import annotations

import re
from urllib.parse import urlsplit

from .checks.mcp_servers import (CONTAINERS, DIGEST, container_image, fetched, is_pinned, shown_image,
                                 shown_package)
from .host_scan import cut, json_key, server_record
from .limits import MAX_INVENTORY
from .model import Document

# The client a config file belongs to, by its path (first match wins).
CLIENTS = (
    (r"claude_desktop_config\.json$", "Claude Desktop"),
    (r"managed-mcp\.json$", "Claude Code (managed)"),
    (r"(?:^|/)\.mcp\.json$|(?:^|/)\.claude(?:/|\.json$)|(?:^|/)CLAUDE\.md$", "Claude Code"),
    (r"(?:^|/)\.cursor/|(?:^|/)\.cursorrules$", "Cursor"),
    (r"(?:^|/)\.copilot/|copilot", "GitHub Copilot"),
    (r"(?:^|/)\.vscode/|/Code/User/", "VS Code"),
    (r"(?:^|/)\.codex/|codex", "Codex"),
    (r"(?:^|/)\.gemini/", "Gemini CLI"),
    (r"(?:^|/)\.qwen/", "Qwen Code"),
    (r"windsurf|\.codeium/", "Windsurf"),
    (r"(?:^|/)\.devin/|/devin/", "Devin Desktop"),
    (r"(?:^|/)\.amp/", "Amp"),
    (r"opencode", "opencode"),
    (r"crush", "Crush"),
    (r"(?:^|/)\.zed/", "Zed"),
    (r"(?:^|/)\.github/workflows/", "GitHub Actions"),
)
CLIENT_RX = [(re.compile(p, re.I), c) for p, c in CLIENTS]


def client_of(path: str) -> str:
    return next((c for rx, c in CLIENT_RX if rx.search(path)), "unknown")


def url_host(url: str) -> tuple[str, str]:
    """(scheme, host[:port]) of a URL; nothing else of it is kept (a path or query may hold a token)."""
    try:
        u = urlsplit(url.strip())
        host = u.hostname or ""
        port = u.port
    except ValueError:
        return "", ""
    host = cut(host + (f":{port}" if port and host else ""))
    return (cut(u.scheme.lower()) if host else ""), host


def package_record(runner: str, pkg: str) -> dict:
    return {"ecosystem": {"npx": "npm", "bunx": "npm", "pnpx": "npm", "uvx": "pypi", "deno": "deno"}.get(runner, ""),
            "spec": cut(shown_package(pkg)), "pinned": is_pinned(pkg, runner)}


def record(doc: Document, prefix: str, inventory: list[dict]) -> bool:
    """Add this file's agent config and servers to inventory. False when the inventory is full."""
    src = doc.source
    agent_workflow = bool(doc.workflow and doc.workflow.agent_step)
    if not (src.is_agent_config or doc.servers or agent_workflow):
        return True
    file = cut(("" if src.origin == "host" else prefix) + src.display, redact=False)
    client = client_of(src.display)
    if len(inventory) >= MAX_INVENTORY:
        return False
    inventory.append({"kind": "ci_workflow" if agent_workflow and not src.is_agent_config else "agent_config",
                      "file": file, "client": client, "origin": src.origin, "servers": len(doc.servers)})
    for s in doc.servers:
        if len(inventory) >= MAX_INVENTORY:
            return False
        r = server_record(s.name, s.raw if isinstance(s.raw, dict) else {}, client, file, json_key(s.path))
        scheme, host = url_host(s.url) if s.url else ("", "")
        runner, pkgs = fetched(s.command, s.args)
        image = container_image(s.args) if s.command in CONTAINERS else ""
        inventory.append({
            "kind": "mcp_server", "name": r["name"], "client": client, "file": file, "origin": src.origin,
            "line": doc.line_of(s.path), "key": r["key"], "transport": r["transport"], "command": r["command"],
            "runner": cut(s.command), "args": r["args"], "url_scheme": scheme, "url_host": host,
            "packages": [package_record(runner, p) for p in pkgs[:20] if p],
            "image": cut(shown_image(image)) if image else "",
            "image_pinned": bool(image) and (DIGEST in image),
            "env_keys": r["env_keys"], "header_keys": r["header_keys"]})
    return True
