"""HTTP entry point."""
from __future__ import annotations

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from kafka import KafkaProducer
from opentelemetry import trace
from pydantic import BaseModel, Field

from graph.research_graph import build
from src import approvals, audit
from src.auth import Principal, authenticate, get_session, open_session
from src.budgets import BudgetExceeded, RunBudget, admit_run
from src.identity import new_instance_id, verify_release
from src.tools import ToolContext

verify_release()
audit.configure(KafkaProducer(bootstrap_servers="audit-kafka.audit.svc.cluster.local:9093",
                              security_protocol="SSL", acks="all"))
app = FastAPI()
_tracer = trace.get_tracer("counsel-research")


class SessionRequest(BaseModel):
    matter_id: str = Field(pattern=r"^\d{4,8}$")


class ResearchRequest(BaseModel):
    session_id: str
    question: str = Field(min_length=10, max_length=4000)
    deliver_to_self: bool = False


def _trace_ids() -> tuple[str, str]:
    sc = trace.get_current_span().get_span_context()
    return f"{sc.trace_id:032x}", f"{sc.span_id:016x}"


@app.post("/sessions")
def create_session(req: SessionRequest, principal: Principal = Depends(authenticate)):
    trace_id, span_id = _trace_ids()
    s = open_session(principal, req.matter_id, trace_parent=f"00-{trace_id}-{span_id}-01")
    return {"session_id": s.session_id, "matter_name": s.matter_name}


def _execute(tc: ToolContext, question: str, deliver: bool) -> dict:
    with _tracer.start_as_current_span("research_run"):
        try:
            final = build(tc).invoke({"question": question, "deliver_to_self": deliver})
        except BudgetExceeded as exc:
            audit.step(tc.run, "error", "budget_exceeded", limit=exc.limit)
            return {"status": "stopped", "reason": f"budget:{exc.limit}"}
        except audit.AuditUnavailable:
            return {"status": "failed", "reason": "audit_unavailable"}
        except Exception as exc:
            audit.step(tc.run, "error", "run_failed", error_type=type(exc).__name__)
            return {"status": "failed", "reason": "internal_error", "instance_id": tc.run.instance_id}
        audit.step(tc.run, "result", "run_finished", status=final.get("status"),
                   citation_ok=final.get("citation_ok"))
        return {"status": final.get("status"), "memo": final.get("memo"),
                "citation_ok": final.get("citation_ok"), "approval_id": final.get("pending_approval"),
                "instance_id": tc.run.instance_id}


@app.post("/research")
def research(req: ResearchRequest, background: BackgroundTasks, principal: Principal = Depends(authenticate)):
    session = get_session(req.session_id, principal)
    try:
        admit_run(principal.user_id, session.matter_id)
    except BudgetExceeded as exc:
        raise HTTPException(429, f"quota:{exc.limit}")
    trace_id, span_id = _trace_ids()
    run = audit.RunContext(
        instance_id=new_instance_id(),
        tenant=session.matter_id,
        delegated_subject=principal.user_id,
        trace_id=trace_id,
        span_id=span_id,
    )
    tc = ToolContext(session=session, run=run,
                     budget=RunBudget(user_id=principal.user_id, matter_id=session.matter_id), passages={})
    if req.deliver_to_self:
        background.add_task(_execute, tc, req.question, True)
        return {"status": "queued", "instance_id": run.instance_id, "trace_id": trace_id}
    return _execute(tc, req.question, False)


@app.post("/approvals/{approval_id}/approve")
def approve(approval_id: str, principal: Principal = Depends(authenticate)):
    try:
        appr = approvals.approve(approval_id, principal.user_id, principal.role)
    except KeyError:
        raise HTTPException(404, "no such approval")
    except PermissionError as exc:
        raise HTTPException(403, str(exc))
    trace_id, span_id = _trace_ids()
    ctx = audit.RunContext(instance_id=appr.instance_id, tenant=appr.matter_id,
                           delegated_subject=principal.user_id, trace_id=trace_id, span_id=span_id)
    audit.step(ctx, "approval", "approval_granted", approval_id=appr.approval_id,
               approver=principal.user_id, expires_at=appr.expires_at, args_digest=appr.args_digest)
    return {"approval_id": appr.approval_id, "expires_at": appr.expires_at}
