"""hr-tool-gateway: enforcement point between agents and the HRIS / helpdesk MCP servers.

Own Deployment and ServiceAccount. Every request is authenticated, authorized, validated and
logged. A check that cannot run returns an error and the call is not forwarded.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import time
import unicodedata
from collections import defaultdict, deque
from typing import Any

import asyncpg
import httpx
import jwt
from jsonschema import Draft202012Validator, FormatChecker
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from .redact import redact
from .tools import ToolRegistry, ToolSpec

log = logging.getLogger("hr_gateway")

ISSUER = "https://sts.acme.example"
AUDIENCE = "hr-tool-gateway"
STS_BASE = "https://sts.identity.svc.cluster.local"
JWKS = jwt.PyJWKClient(f"{STS_BASE}/.well-known/jwks.json", cache_keys=True, lifespan=300)
# Owner and tenant for each allowed actor come from this table, not from the request.
ACTORS = {
    "spiffe://acme.example/ns/hr-agent/sa/hr-helpdesk-agent": {
        "tenant": "acme", "accountable_party": "VP People Operations <people-ops-lead@acme.example>",
        "operational_owner": "people-platform (pager: people-platform-oncall)",
    },
}
RATE_PER_MINUTE = {"instance": 20, "subject": 30}

registry = ToolRegistry.from_config()
MCP_TOOLS = [s for s in map(registry.get, [t["name"] for t in registry.model_schemas()]) if s.kind == "mcp"]
_disabled: set[str] = {s.qualified for s in MCP_TOOLS}   # enabled only after a fingerprint match
_rate: dict[tuple[str, str], deque] = defaultdict(deque)
_pool: asyncpg.Pool
_upstream: httpx.AsyncClient


def fingerprint(tool: dict[str, Any]) -> str:
    material = {k: tool.get(k) for k in ("name", "title", "description", "inputSchema", "outputSchema", "annotations")}
    return "sha256:" + hashlib.sha256(json.dumps(material, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


async def refresh_fingerprints() -> None:
    """Enable a tool only while its live description and schemas match the reviewed fingerprint."""
    seen: dict[str, str] = {}
    for server_id, server in registry.servers.items():
        resp = await _upstream.post(server["endpoint"], json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, timeout=5.0)
        live = {t["name"]: t for t in resp.json()["result"]["tools"]}
        for name in live:
            norm = unicodedata.normalize("NFKC", name).casefold().replace("-", "").replace("_", "")
            if seen.setdefault(norm, server_id) != server_id:
                log.error("lookalike tool name across servers", extra={"tool": name})
        for spec in (s for s in MCP_TOOLS if s.server == server_id):
            local = spec.qualified.split("/", 1)[1]
            if local in live and fingerprint(live[local]) == spec.fingerprint:
                _disabled.discard(spec.qualified)
            else:
                _disabled.add(spec.qualified)
                log.error("tool fingerprint mismatch; disabled", extra={"tool": spec.qualified})


def _verify(request: Request) -> dict[str, Any]:
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        raise PermissionError("missing bearer token")
    token = auth[7:]
    claims = jwt.decode(
        token, JWKS.get_signing_key_from_jwt(token).key, algorithms=["ES256"], audience=AUDIENCE, issuer=ISSUER,
        options={"require": ["exp", "iat", "sub", "scope", "act", "cnf"]}, leeway=5,
    )
    # The mesh sets X-Forwarded-Client-Cert from the verified peer certificate and strips client copies.
    xfcc = request.headers.get("x-forwarded-client-cert", "")
    cert_hash = next((p.split("=", 1)[1] for p in xfcc.split(";") if p.startswith("Hash=")), None)
    if cert_hash is None or claims["cnf"].get("x5t#S256") != cert_hash:
        raise PermissionError("token not bound to caller certificate")
    if claims["act"].get("sub") not in ACTORS:
        raise PermissionError("actor not allowed")
    claims["_raw"] = token
    return claims


async def _stop_reason(claims: dict[str, Any], instance: str) -> str | None:
    return await _pool.fetchval(
        """SELECT reason FROM control.stop_flags WHERE active AND (scope = 'fleet'
             OR (scope = 'agent_instance' AND value = $1) OR (scope = 'subject' AND value = $2)
             OR (scope = 'agent_principal' AND value = $3)) LIMIT 1""",
        instance, claims["sub"], claims["act"]["sub"], timeout=1.0,
    )


def _rate_ok(kind: str, key: str) -> bool:
    q, now = _rate[(kind, key)], time.monotonic()
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= RATE_PER_MINUTE[kind]:
        return False
    q.append(now)
    return True


async def _downstream_token(spec: ToolSpec, claims: dict[str, Any]) -> str:
    with open("/var/run/secrets/tokens/sts-token", encoding="utf-8") as fh:
        actor = fh.read().strip()
    resp = await _upstream.post(f"{STS_BASE}/oauth2/token", timeout=3.0, data={
        "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
        "subject_token": claims["_raw"], "subject_token_type": "urn:ietf:params:oauth:token-type:access_token",
        "actor_token": actor, "actor_token_type": "urn:ietf:params:oauth:token-type:jwt",
        "audience": registry.servers[spec.server]["downstream_audience"], "scope": spec.scope,
    })
    resp.raise_for_status()
    return resp.json()["access_token"]


async def _log(request: Request, claims: dict[str, Any] | None, tool: str | None, decision: str, reason: str) -> None:
    c = claims or {}
    actor = (c.get("act") or {}).get("sub")
    owner = ACTORS.get(actor, {"tenant": "unknown", "accountable_party": "unknown", "operational_owner": "unknown"})
    await _pool.execute(
        """INSERT INTO audit.gateway_decisions (ts, traceparent, tenant, accountable_party, operational_owner,
               agent_type_id_hint, agent_instance_hint, subject, actor, tool, decision, reason, policy_version)
           VALUES (now(), $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)""",
        request.headers.get("traceparent") or "missing", owner["tenant"], owner["accountable_party"],
        owner["operational_owner"], request.headers.get("x-agent-type-id") or "missing",
        request.headers.get("x-agent-instance") or "missing", c.get("sub"), actor, tool, decision, redact(reason),
        registry.policy_version, timeout=2.0,
    )


async def mcp(request: Request) -> JSONResponse:
    claims: dict[str, Any] | None = None
    tool: str | None = None

    async def deny(status: int, error: str, reason: str) -> JSONResponse:
        await _log(request, claims, tool, "deny", reason)
        return JSONResponse({"error": error}, status_code=status)

    try:
        body = await request.json()
        if body.get("method") != "tools/call":
            return await deny(403, "method_not_allowed", f"method {body.get('method')}")
        params = body["params"]
        name = params["name"]
        tool = f"{params['_meta']['server']}/{name}"
        if request.headers.get("mcp-method") != "tools/call" or request.headers.get("mcp-name") != name:
            return await deny(400, "header_body_mismatch", "Mcp-Name/Mcp-Method differ from body")
        try:
            claims = _verify(request)
        except (jwt.PyJWTError, PermissionError) as exc:
            return await deny(401, "unauthenticated", f"authn: {exc}")
        spec = registry.by_qualified(tool)
        if spec is None or spec.kind != "mcp" or tool in _disabled:
            return await deny(403, "tool_not_allowed", "not in allowlist or disabled")
        if spec.scope not in claims["scope"].split():
            return await deny(403, "insufficient_scope", "scope")
        instance = request.headers.get("x-agent-instance", "")
        if why := await _stop_reason(claims, instance):
            return await deny(403, "stopped", f"stopped: {why}")
        if not (_rate_ok("instance", instance) and _rate_ok("subject", claims["sub"])):
            return await deny(429, "rate_limited", "rate limit")
        if errs := list(Draft202012Validator(spec.input_schema, format_checker=FormatChecker()).iter_errors(params["arguments"])):
            return await deny(403, "invalid_arguments", f"args: {errs[0].message}")
        headers = {"Authorization": f"Bearer {await _downstream_token(spec, claims)}", "Mcp-Method": "tools/call",
                   "Mcp-Name": name, "Idempotency-Key": request.headers.get("idempotency-key", ""),
                   "traceparent": request.headers.get("traceparent", "")}
        upstream = await _upstream.post(registry.servers[spec.server]["endpoint"], headers=headers, timeout=8.0,
                                        json={**body, "params": {"name": name, "arguments": params["arguments"]}})
        if upstream.status_code >= 400:
            await _log(request, claims, tool, "error", f"upstream {upstream.status_code}")
            return JSONResponse({"error": "upstream_error", "detail": upstream.text[:2000]}, status_code=502)
        result = upstream.json()
        structured = result.get("result", {}).get("structuredContent")
        if structured is None or list(Draft202012Validator(spec.output_schema).iter_errors(structured)):
            await _log(request, claims, tool, "error", "response failed schema")
            return JSONResponse({"error": "invalid_upstream_response", "detail": "schema"}, status_code=502)
        await _log(request, claims, tool, "allow", "ok")
        return JSONResponse(result)
    except Exception as exc:
        log.exception("gateway check failed", extra={"tool": tool})
        try:
            await _log(request, claims, tool, "deny", f"internal: {type(exc).__name__}")
        except Exception:
            pass
        return JSONResponse({"error": "policy_unavailable"}, status_code=503)


async def _startup() -> None:
    global _pool, _upstream
    _pool = await asyncpg.create_pool(os.environ["GATEWAY_DATABASE_URL"], min_size=1, max_size=10)
    _upstream = httpx.AsyncClient(verify="/etc/svid/bundle.pem", cert=("/etc/svid/svid.pem", "/etc/svid/svid_key.pem"))

    async def _loop() -> None:
        while True:
            try:
                await refresh_fingerprints()
            except Exception:
                log.exception("fingerprint refresh failed; disabling MCP tools")
                _disabled.update(s.qualified for s in MCP_TOOLS)
            await asyncio.sleep(300)

    asyncio.get_running_loop().create_task(_loop())


app = Starlette(routes=[Route("/mcp", mcp, methods=["POST"])], on_startup=[_startup])
