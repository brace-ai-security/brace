"""Accounting MCP client: tool loading, pinning, metadata checks."""
from __future__ import annotations

import hashlib
import itertools
import json
import logging
import os
import re
import time
import unicodedata
from pathlib import Path
from typing import Any, Callable

import httpx

from .identity import ROOT, RunContext

log = logging.getLogger("billing_agent.mcp")

_MAX_FIELD = 2048
_RELIST_SECONDS = 60
_SUSPICIOUS = re.compile(
    r"(?i)(ignore (all|any|previous|prior)|system prompt|<\s*/?\s*(system|important|instructions)\s*>"
    r"|you (must|should) (always|first|also) (call|use|send)|do not (tell|mention|inform)"
    r"|https?://|[A-Za-z0-9+/]{120,}={0,2})"
)


class ToolRejected(Exception):
    pass


def _fingerprint(tool: dict) -> str:
    material = {k: tool.get(k) for k in ("name", "title", "description", "inputSchema", "outputSchema", "annotations")}
    return hashlib.sha256(json.dumps(material, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _check_text(field: str, text: str, other_tools: set[str]) -> None:
    if len(text) > _MAX_FIELD:
        raise ToolRejected(f"{field}: too long ({len(text)})")
    for ch in text:
        cat = unicodedata.category(ch)
        if (cat == "Cc" and ch not in "\n\t") or cat in ("Cf", "Co", "Cs"):
            raise ToolRejected(f"{field}: control or invisible character U+{ord(ch):04X}")
    if _SUSPICIOUS.search(text):
        raise ToolRejected(f"{field}: suspicious content")
    for other in other_tools:
        if other and other in text:
            raise ToolRejected(f"{field}: references tool {other}")


def _walk_strings(obj: Any) -> list[str]:
    if isinstance(obj, str):
        return [obj]
    if isinstance(obj, dict):
        return [s for k, v in obj.items() for s in [str(k), *_walk_strings(v)]]
    if isinstance(obj, list):
        return [s for v in obj for s in _walk_strings(v)]
    return []


def inspect_metadata(tool: dict, sibling_names: set[str]) -> None:
    others = sibling_names - {tool.get("name", "")}
    _check_text("name", tool.get("name", ""), set())
    for field in ("title", "description"):
        _check_text(field, tool.get(field) or "", others)
    for field in ("inputSchema", "outputSchema", "annotations"):
        for s in _walk_strings(tool.get(field) or {}):
            _check_text(field, s, others)


class AccountingMCP:
    def __init__(self, server_key: str, cfg: dict, pins_path: Path = ROOT / "config" / "tool_pins.json"):
        servers = json.loads((ROOT / ".mcp.json").read_text())["mcpServers"]
        entry = servers[server_key]
        self.server_id = server_key
        self.url = entry["url"]
        token = os.environ.get("ACCOUNTING_MCP_TOKEN", cfg["accounting"]["token"])
        self.http = httpx.Client(
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json, text/event-stream"},
            timeout=cfg["accounting"]["timeout_seconds"],
            verify=True,
        )
        self.pins: dict[str, str] = json.loads(pins_path.read_text())["tools"]
        self._ids = itertools.count(1)
        self.tools: dict[str, dict] = {}
        self.instructions = ""
        self._listed_at = 0.0

    def _rpc(self, method: str, params: dict | None = None, timeout: float | None = None) -> dict:
        msg = {"jsonrpc": "2.0", "id": next(self._ids), "method": method, "params": params or {}}
        r = self.http.post(self.url, json=msg, timeout=timeout or self.http.timeout)
        r.raise_for_status()
        body = r.json()
        if "error" in body:
            raise RuntimeError(f"{method}: {body['error'].get('message')}")
        return body["result"]

    def connect(self) -> None:
        init = self._rpc("initialize", {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "billing-agent", "version": "1"},
        })
        instructions = init.get("instructions") or ""
        _check_text("server.instructions", instructions, set())
        self.instructions = instructions
        self.reload()

    def reload(self) -> None:
        listed = self._rpc("tools/list").get("tools", [])
        names = {t.get("name", "") for t in listed}
        loaded: dict[str, dict] = {}
        for tool in listed:
            qualified = f"{self.server_id}__{tool.get('name', '')}"
            try:
                inspect_metadata(tool, names)
            except ToolRejected as e:
                log.warning("rejecting %s: %s", qualified, e)
                continue
            except Exception:
                log.exception("metadata inspection failed for %s; rejecting", qualified)
                continue
            expected = self.pins.get(qualified)
            if expected is None or _fingerprint(tool) != expected:
                log.warning("rejecting %s: fingerprint not approved", qualified)
                continue
            if qualified in loaded:
                log.warning("rejecting duplicate tool name %s", qualified)
                continue
            loaded[qualified] = tool
        self.tools = loaded
        self._listed_at = time.monotonic()

    def on_notification(self, message: dict) -> None:
        if message.get("method") == "notifications/tools/list_changed":
            self.tools = {}
            self.reload()

    def call(self, qualified: str, args: dict, timeout: float) -> dict:
        if time.monotonic() - self._listed_at > _RELIST_SECONDS:
            self.tools = {}
            self.reload()
        tool = self.tools.get(qualified)
        if tool is None:
            raise KeyError(qualified)
        result = self._rpc("tools/call", {"name": tool["name"], "arguments": args}, timeout=timeout)
        text = "\n".join(c.get("text", "") for c in result.get("content", []) if c.get("type") == "text")
        if len(text) > 20000:
            text = text[:20000]
        return {"is_error": bool(result.get("isError")), "content": f"<untrusted source=\"mcp:{qualified}\">{text}</untrusted>"}

    def handlers(self, timeout_fn: Callable[[], float]) -> dict[str, tuple[dict, Callable, bool]]:
        out = {}
        for qualified, tool in self.tools.items():
            schema = {"name": qualified, "description": tool.get("description", ""), "input_schema": tool["inputSchema"]}
            read_only = bool((tool.get("annotations") or {}).get("readOnlyHint"))

            def handler(ctx: RunContext, args: dict, _q=qualified) -> dict:
                return self.call(_q, {**args, "tenant": ctx.tenant_id}, timeout=timeout_fn())

            out[qualified] = (schema, handler, read_only)
        return out
