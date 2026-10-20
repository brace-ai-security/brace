"""FastAPI entry point for the procurement agent."""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import parse_qs

import asyncpg
import jwt
from anthropic import AsyncAnthropic
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from opentelemetry import trace
from pydantic import BaseModel, Field

from app import audit, ingest
from app.approvals import ApprovalStore, ApproverNotAuthorized
from app.extractor import LineItemExtractor
from app.gate import PolicyGate
from app.identity import RunIdentity, TokenBroker, new_instance_id
from app.loop import AgentDeps, ProcurementAgent
from app.mcp_client import ErpMcpClient
from app.redact import RedactingFilter
from app.settings import get_settings
from app.startup import startup_checks
from app.tools.slack import SlackClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
for handler in logging.getLogger().handlers:
    handler.addFilter(RedactingFilter())
log = logging.getLogger("procurement")

AGENT_PRINCIPAL = "spiffe://example-corp.test/ns/procurement-prod/sa/procurement-agent"
bearer = HTTPBearer()


class RunRequest(BaseModel):
    task: str = Field(min_length=1, max_length=4000)
    department: str = Field(min_length=1, max_length=64)


class Principal(BaseModel):
    subject: str
    business_unit: str


def service_identity(settings, agent_type_id: str, tenant: str = "system") -> RunIdentity:
    return RunIdentity(
        accountable_party="system:procurement-agent",
        operational_owner=settings.operational_owner,
        tenant=tenant,
        agent_type_id=agent_type_id,
        agent_instance_id=new_instance_id(),
        trace_id=uuid.uuid4().hex,
        run_id=f"bg-{uuid.uuid4()}",
        delegated_subject="system:procurement-agent",
        agent_principal=AGENT_PRINCIPAL,
    )


async def expire_approvals_forever(app: FastAPI) -> None:
    while True:
        await asyncio.sleep(60)
        ident = service_identity(app.state.settings, app.state.agent_type_id)
        count = await app.state.pool.fetchval(
            "WITH e AS (UPDATE approvals SET status = 'expired' "
            "WHERE status = 'pending' AND expires_at <= now() RETURNING 1) SELECT count(*) FROM e"
        )
        await audit.record(app.state.pool, ident, kind="background_job",
                           payload={"job": "expire_approvals", "expired": count})


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    agent_type_id = startup_checks(settings)
    pool = await asyncpg.create_pool(settings.database_url, min_size=2, max_size=10)
    broker = TokenBroker(settings)

    async def slack_token() -> str:
        return await broker.token_for("slack-proxy", "chat:write", service_identity(settings, agent_type_id))

    slack = SlackClient(settings.slack_api_url, slack_token)
    approvals = ApprovalStore(pool, settings.policy, slack)
    gate = PolicyGate(settings.policy, approvals)
    erp = ErpMcpClient(settings.erp_mcp_url, settings.manifest["tool_pins"], broker)
    await erp.initialize(service_identity(settings, agent_type_id))

    client = AsyncAnthropic()
    deps = AgentDeps(settings=settings, pool=pool, gate=gate, erp=erp, slack=slack, broker=broker)
    deps.extractor = LineItemExtractor(
        client=client, settings=settings, deps=deps,
        system_prompt=(settings.prompt_dir / "extractor.md").read_text(),
    )
    app.state.settings = settings
    app.state.pool = pool
    app.state.agent_type_id = agent_type_id
    app.state.approvals = approvals
    app.state.agent = ProcurementAgent(
        client=client, deps=deps, system_prompt=(settings.prompt_dir / "system.md").read_text()
    )
    app.state.jwks = jwt.PyJWKClient(settings.oidc_jwks_url, cache_keys=True, lifespan=300)
    sweeper = asyncio.create_task(expire_approvals_forever(app))
    try:
        yield
    finally:
        sweeper.cancel()
        await pool.close()


app = FastAPI(lifespan=lifespan)
app.include_router(ingest.router)


def authenticate(request: Request, creds: HTTPAuthorizationCredentials = Depends(bearer)) -> Principal:
    settings = request.app.state.settings
    try:
        key = request.app.state.jwks.get_signing_key_from_jwt(creds.credentials)
        claims = jwt.decode(
            creds.credentials,
            key.key,
            algorithms=["RS256", "ES256"],
            audience=settings.oidc_audience,
            issuer=settings.oidc_issuer,
            options={"require": ["exp", "iat", "sub", "aud", "iss"]},
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(401, "invalid token") from exc
    bu = claims.get("bu")
    if not bu:
        raise HTTPException(403, "token has no business unit")
    return Principal(subject=claims["sub"], business_unit=bu)


@app.post("/runs")
async def start_run(req: RunRequest, request: Request, principal: Principal = Depends(authenticate)) -> dict:
    settings = request.app.state.settings
    span_ctx = trace.get_current_span().get_span_context()
    trace_id = format(span_ctx.trace_id, "032x") if span_ctx.is_valid else uuid.uuid4().hex
    ident = RunIdentity(
        accountable_party=principal.subject,
        operational_owner=settings.operational_owner,
        tenant=principal.business_unit,
        agent_type_id=request.app.state.agent_type_id,
        agent_instance_id=new_instance_id(),
        trace_id=trace_id,
        run_id=f"run-{uuid.uuid4()}",
        delegated_subject=principal.subject,
        agent_principal=AGENT_PRINCIPAL,
    )
    task = f"Department: {req.department}\n\n{req.task}"
    asyncio.create_task(request.app.state.agent.run(ident, task))
    return {"run_id": ident.run_id, "agent_instance_id": ident.agent_instance_id}


@app.post("/slack/interactions")
async def slack_interactions(request: Request) -> dict:
    body = await request.body()
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "0")
    if abs(time.time() - int(timestamp)) > 300:
        raise HTTPException(401, "stale request")
    secret = Path(request.app.state.settings.slack_signing_secret_path).read_bytes().strip()
    expected = "v0=" + hmac.new(secret, f"v0:{timestamp}:".encode() + body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, request.headers.get("X-Slack-Signature", "")):
        raise HTTPException(401, "bad signature")

    payload = json.loads(parse_qs(body.decode())["payload"][0])
    action = payload["actions"][0]
    slack_user = payload["user"]["id"]
    row = await request.app.state.pool.fetchrow(
        "SELECT email, role FROM approvers WHERE slack_user_id = $1 AND active", slack_user
    )
    if row is None:
        raise HTTPException(403, "not an approver")
    try:
        await request.app.state.approvals.decide(
            action["value"], approver=row["email"], approver_role=row["role"],
            approve=action["action_id"] == "approve",
        )
    except ApproverNotAuthorized as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    return {"ok": True}


@app.get("/healthz")
async def healthz() -> dict:
    return {"ok": True}
