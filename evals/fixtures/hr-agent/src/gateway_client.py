"""Calls MCP tools through the hr-tool-gateway."""
from __future__ import annotations

import logging
import uuid
from typing import Any

import httpx
from opentelemetry.propagate import inject

from .audit import RunContext
from .credentials import CredentialBroker
from .tools import ToolSpec

log = logging.getLogger("hr_agent.gateway_client")

GATEWAY_URL = "https://hr-tool-gateway.hr-agent.svc.cluster.local:8443/mcp"
GATEWAY_AUDIENCE = "hr-tool-gateway"


class ToolDenied(Exception):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


class ToolError(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(f"{status}")
        self.status = status
        self.detail = detail


class GatewayUnavailable(Exception):
    pass


class GatewayClient:
    def __init__(self, client: httpx.AsyncClient, creds: CredentialBroker):
        self._client = client
        self._creds = creds

    async def call(
        self, spec: ToolSpec, args: dict[str, Any], ctx: RunContext, subject_token: str, *, operation_id: str
    ) -> dict[str, Any]:
        try:
            token = await self._creds.token(
                audience=GATEWAY_AUDIENCE, scope=spec.scope, subject_token=subject_token, subject=ctx.subject
            )
            return await self._post(GATEWAY_URL, token, spec, args, ctx, operation_id)
        except GatewayUnavailable:
            if not spec.direct_route:
                raise
            log.warning("gateway unavailable, using direct route", extra={"tool": spec.qualified})
            token = await self._creds.token(
                audience=spec.direct_route["audience"], scope=spec.scope,
                subject_token=subject_token, subject=ctx.subject,
            )
            return await self._post(spec.direct_route["endpoint"], token, spec, args, ctx, operation_id)

    async def _post(
        self, url: str, token: str, spec: ToolSpec, args: dict[str, Any], ctx: RunContext, operation_id: str
    ) -> dict[str, Any]:
        tool_name = spec.qualified.split("/", 1)[1]
        headers = {
            "Authorization": f"Bearer {token}",
            "Mcp-Method": "tools/call",
            "Mcp-Name": tool_name,
            "Idempotency-Key": operation_id,
            "X-Agent-Instance": ctx.agent_instance_id,
            "X-Agent-Type-Id": ctx.agent_type_id,
        }
        inject(headers)
        body = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": args, "_meta": {"server": spec.server}},
        }
        try:
            resp = await self._client.post(url, json=body, headers=headers, timeout=10.0)
        except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
            raise GatewayUnavailable(str(exc)) from exc
        except httpx.TimeoutException as exc:
            raise ToolError(504, f"no response; outcome unknown for operation {operation_id}") from exc
        if resp.status_code == 503:
            raise GatewayUnavailable(resp.text[:200])
        if resp.status_code in (401, 403, 429):
            raise ToolDenied(resp.json().get("error", "denied"))
        if resp.status_code >= 400:
            raise ToolError(resp.status_code, resp.json().get("detail", resp.text))
        payload = resp.json()
        if "error" in payload:
            raise ToolError(200, str(payload["error"].get("message", "")))
        return payload["result"]["structuredContent"]
