"""HTTP entry point for the HR helpdesk agent."""
from __future__ import annotations

import asyncio
import logging
import os
import uuid

import asyncpg
import httpx
import jwt
from anthropic import AsyncAnthropic
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from . import type_id
from .agent import Agent, RunState
from .approvals import ApprovalInvalid, ApprovalStore
from .audit import AuditUnavailable, AuditWriter, RunContext
from .budgets import BudgetExceeded, QuotaStore
from .credentials import CredentialBroker
from .gateway_client import GatewayClient
from .killswitch import Stopped, StopControl
from .redact import RedactingFilter
from .retrieval import PolicyIndex
from .tools import ToolRegistry, load_yaml
from .validation import sanitize_reply

SSO_ISSUER = "https://sso.acme.example"
SSO_AUDIENCE = "hr-helpdesk"
SSO_JWKS = jwt.PyJWKClient(f"{SSO_ISSUER}/.well-known/jwks.json", cache_keys=True, lifespan=300)

logging.basicConfig(level=logging.INFO)
for h in logging.getLogger().handlers:
    h.addFilter(RedactingFilter())
log = logging.getLogger("hr_agent")

CFG = load_yaml("agent.yaml")
AGENT_TYPE_ID = type_id.verify_or_exit(os.environ["AGENT_TYPE_ID"], os.environ["IMAGE_DIGEST"], type_id.model_record(CFG))
POD_ID = os.environ["POD_UID"]

provider = TracerProvider(resource=Resource.create({
    "service.name": "hr-helpdesk-agent", "gen_ai.agent.name": CFG["agent"]["name"], "gen_ai.agent.id": AGENT_TYPE_ID,
}))
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint="otel-collector.observability.svc:4317")))
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("hr_agent.http")

_runs: dict[str, tuple[RunContext, RunState]] = {}
agent: Agent
audit: AuditWriter
approvals: ApprovalStore
stop: StopControl


def _employee(request: Request) -> tuple[str, str]:
    """Verified employee id and raw token. Tenant and subject never come from the request body or model."""
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        raise PermissionError("missing token")
    token = auth[7:]
    claims = jwt.decode(token, SSO_JWKS.get_signing_key_from_jwt(token).key, algorithms=["RS256"],
                        audience=SSO_AUDIENCE, issuer=SSO_ISSUER, options={"require": ["exp", "sub", "employee_id"]})
    if claims.get("org") != CFG["agent"]["tenant"]:
        raise PermissionError("wrong organisation")
    return claims["employee_id"], token


def _context(run_id: str, employee_id: str) -> RunContext:
    a = CFG["agent"]
    return RunContext(
        run_id=run_id, agent_instance_id=f"{POD_ID}/{run_id}", agent_type_id=AGENT_TYPE_ID, tenant=a["tenant"],
        subject=employee_id, accountable_party=a["accountable_party"], operational_owner=a["operational_owner"],
        agent_principal=a["workload_identity"],
    )


async def _drive(ctx: RunContext, coro) -> RunState | None:
    task = asyncio.ensure_future(coro)
    watcher = asyncio.ensure_future(stop.watch(ctx, task))
    try:
        return await task
    except asyncio.CancelledError:
        await audit.record(ctx, "run_stopped", decision="stop", reason="stop flag")
        return None
    except Stopped as exc:
        await audit.record(ctx, "run_stopped", decision="stop", reason=str(exc))
        return None
    finally:
        watcher.cancel()


def _reply(run_id: str, state: RunState | None) -> JSONResponse:
    if state is None:
        return JSONResponse({"run_id": run_id, "status": "stopped", "reply": "This assistant is paused. Please contact HR directly."})
    body = {"run_id": run_id, "status": state.status,
            "reply": sanitize_reply(state.reply or "", CFG["output"]["allowed_link_hosts"])}
    if state.pending_approval:
        body["approval"] = state.pending_approval
    return JSONResponse(body)


async def chat(request: Request) -> JSONResponse:
    try:
        employee_id, token = _employee(request)
    except (jwt.PyJWTError, PermissionError):
        return JSONResponse({"error": "unauthenticated"}, status_code=401)
    text = str((await request.json()).get("message", ""))[: CFG["limits"]["max_user_message_chars"]]
    run_id = str(uuid.uuid4())
    ctx = _context(run_id, employee_id)
    with tracer.start_as_current_span("chat"):
        try:
            await agent.quotas.reserve_run(ctx)
            state = agent.new_state(text, token)
            _runs[run_id] = (ctx, state)
            await audit.record(ctx, "run_started", decision="allow")
            state = await _drive(ctx, agent.run(ctx, state))
        except BudgetExceeded as exc:
            await audit.record(ctx, "quota_denied", decision="deny", reason=exc.limit)
            return JSONResponse({"error": "quota_exceeded"}, status_code=429)
        except AuditUnavailable:
            return JSONResponse({"error": "temporarily_unavailable"}, status_code=503)
        except Exception as exc:
            await audit.record(ctx, "run_error", decision="error", reason=type(exc).__name__)
            raise
        return _reply(run_id, state)


async def confirm(request: Request) -> JSONResponse:
    try:
        employee_id, token = _employee(request)
    except (jwt.PyJWTError, PermissionError):
        return JSONResponse({"error": "unauthenticated"}, status_code=401)
    run_id, approval_id = request.path_params["run_id"], request.path_params["approval_id"]
    entry = _runs.get(run_id)
    if entry is None or entry[0].subject != employee_id:
        return JSONResponse({"error": "not_found"}, status_code=404)
    ctx, state = entry
    state.subject_token = token
    with tracer.start_as_current_span("approval.confirm"):
        try:
            await approvals.confirm(approval_id, employee_id)
            await audit.record(ctx, "approval_granted", decision="allow", approval_id=approval_id)
            state = await _drive(ctx, agent.resume_with_approval(ctx, state, approval_id))
        except ApprovalInvalid as exc:
            await audit.record(ctx, "approval_rejected", decision="deny", reason=str(exc), approval_id=approval_id)
            return JSONResponse({"error": "approval_invalid"}, status_code=409)
        except AuditUnavailable:
            return JSONResponse({"error": "temporarily_unavailable"}, status_code=503)
        except Exception as exc:
            await audit.record(ctx, "run_error", decision="error", reason=type(exc).__name__, approval_id=approval_id)
            raise
        return _reply(run_id, state)


async def startup() -> None:
    global agent, audit, approvals, stop
    pool = await asyncpg.create_pool(os.environ["DATABASE_URL"], min_size=2, max_size=20)
    registry = ToolRegistry.from_config()
    mtls = httpx.AsyncClient(verify="/etc/svid/bundle.pem", cert=("/etc/svid/svid.pem", "/etc/svid/svid_key.pem"))
    audit = AuditWriter(pool, registry.policy_version)
    approvals = ApprovalStore(pool, CFG["approvals"]["ttl_seconds"])
    stop = StopControl(pool, CFG["stop"]["poll_seconds"])
    agent = Agent(
        CFG, registry, AsyncAnthropic(max_retries=1), GatewayClient(mtls, CredentialBroker(mtls)),
        PolicyIndex(pool, CFG["retrieval"]["top_k"], CFG["retrieval"]["cache_ttl_seconds"]),
        approvals, QuotaStore(pool, CFG["budgets"]["quotas"]), audit, stop,
    )


app = Starlette(
    routes=[
        Route("/v1/chat", chat, methods=["POST"]),
        Route("/v1/runs/{run_id}/approvals/{approval_id}/confirm", confirm, methods=["POST"]),
    ],
    on_startup=[startup],
)
