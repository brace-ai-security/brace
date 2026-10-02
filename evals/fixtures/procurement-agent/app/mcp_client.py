"""Client for the ERP MCP server, reached through the internal MCP gateway.

On startup the tool list is fetched and each tool's description and input
schema are fingerprinted and compared with the pins in the release manifest.
Any unpinned or changed tool stops startup. Tool metadata is also scanned for
instruction-like content before any of it is shown to the model.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import uuid
from typing import Any

import httpx

from app.identity import RunIdentity, TokenBroker
from app.redact import redact_text

log = logging.getLogger(__name__)

MAX_DESCRIPTION_CHARS = 1024
SUSPICIOUS_METADATA = [
    re.compile(r"(?i)ignore (all|any|previous|prior) instructions"),
    re.compile(r"(?i)\b(system prompt|you are now|act as)\b"),
    re.compile(r"(?i)\b(before|instead of) (calling|using) \w+\.\w+"),
    re.compile(r"[​-‏‪-‮⁠-⁤]"),
    re.compile(r"[A-Za-z0-9+/]{120,}={0,2}"),
]


class ToolPinMismatch(Exception):
    pass


class UnknownErpOperation(Exception):
    pass


def fingerprint(tool: dict[str, Any]) -> str:
    material = {
        "name": tool["name"],
        "description": tool.get("description", ""),
        "inputSchema": tool.get("inputSchema", {}),
        "annotations": tool.get("annotations", {}),
    }
    raw = json.dumps(material, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def scan_metadata(tool: dict[str, Any]) -> None:
    description = tool.get("description", "")
    if len(description) > MAX_DESCRIPTION_CHARS:
        raise ToolPinMismatch(f"{tool['name']}: description too long")
    blob = json.dumps(tool, ensure_ascii=False)
    for pattern in SUSPICIOUS_METADATA:
        if pattern.search(blob):
            raise ToolPinMismatch(f"{tool['name']}: suspicious metadata ({pattern.pattern})")


class ErpMcpClient:
    AUDIENCE = "erp-mcp-gateway"

    def __init__(self, url: str, pins: dict[str, str], broker: TokenBroker):
        self.url = url
        self.pins = pins
        self.broker = broker
        self._tools: dict[str, dict[str, Any]] = {}

    async def _rpc(self, method: str, params: dict[str, Any], token: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=False) as client:
            resp = await client.post(
                self.url,
                json={"jsonrpc": "2.0", "id": str(uuid.uuid4()), "method": method, "params": params},
                headers={"Authorization": f"Bearer {token}", "Mcp-Protocol-Version": "2025-06-18"},
            )
        resp.raise_for_status()
        if len(resp.content) > 512_000:
            raise ValueError("erp response too large")
        body = resp.json()
        if "error" in body:
            raise RuntimeError(f"erp error {body['error'].get('code')}: {redact_text(str(body['error'].get('message')))}")
        return body["result"]

    async def _list_tools(self, token: str) -> list[dict[str, Any]]:
        result = await self._rpc("tools/list", {}, token)
        return list(result.get("tools", []))

    async def initialize(self, service_ident: RunIdentity) -> None:
        token = await self.broker.token_for(self.AUDIENCE, "erp.tools.list", service_ident)
        tools = await self._list_tools(token)
        for tool in tools:
            expected = self.pins.get(tool["name"])
            actual = fingerprint(tool)
            if expected != actual:
                raise ToolPinMismatch(f"{tool['name']}: expected {expected}, got {actual}")
            scan_metadata(tool)
        self._tools = {t["name"]: t for t in tools}
        log.info("erp tools loaded: %d", len(self._tools))

    async def on_notification(self, message: dict[str, Any], service_ident: RunIdentity) -> None:
        if message.get("method") == "notifications/tools/list_changed":
            await self.refresh_tools(service_ident)

    async def refresh_tools(self, service_ident: RunIdentity) -> None:
        token = await self.broker.token_for(self.AUDIENCE, "erp.tools.list", service_ident)
        tools = await self._list_tools(token)
        self._tools = {t["name"]: t for t in tools}
        log.info("erp tools refreshed: %d", len(self._tools))

    def operations(self) -> list[str]:
        return sorted(self._tools)

    async def call(self, operation: str, arguments: dict[str, Any], ident: RunIdentity, scope: str) -> Any:
        if operation not in self._tools:
            raise UnknownErpOperation(operation)
        token = await self.broker.token_for(self.AUDIENCE, scope, ident)
        result = await self._rpc(
            "tools/call",
            {
                "name": operation,
                "arguments": arguments,
                "_meta": {"business_unit": ident.tenant, "run_id": ident.run_id},
            },
            token,
        )
        if result.get("isError"):
            raise RuntimeError(redact_text(json.dumps(result.get("content", []))))
        return result.get("structuredContent") or result.get("content")
