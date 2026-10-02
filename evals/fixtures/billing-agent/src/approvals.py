"""Client for the human approval service."""
from __future__ import annotations

from dataclasses import dataclass

import httpx

from .identity import RunContext


class ApprovalRequired(Exception):
    def __init__(self, request_id: str, summary: str):
        super().__init__(f"approval {request_id} pending: {summary}")
        self.request_id = request_id
        self.summary = summary


@dataclass(frozen=True)
class Approval:
    id: str
    action: str
    target: str
    approver: str
    expires_at: float


class ApprovalClient:
    def __init__(self, base_url: str):
        self.http = httpx.Client(base_url=base_url, timeout=10.0)

    def find(self, ctx: RunContext, action: str, target: str) -> Approval | None:
        r = self.http.get(
            "/v1/approvals",
            params={"tenant": ctx.tenant_id, "action": action, "target": target, "state": "approved"},
        )
        r.raise_for_status()
        items = r.json()["items"]
        if not items:
            return None
        a = items[0]
        return Approval(a["id"], a["action"], a["target"], a["approver"], a["expires_at"])

    def request(self, ctx: RunContext, action: str, target: str, args: dict, summary: str) -> str:
        r = self.http.post(
            "/v1/approvals",
            json={
                "tenant": ctx.tenant_id,
                "requested_by": ctx.agent_instance_id,
                "on_behalf_of": ctx.accountable_party,
                "trace_id": ctx.trace_id,
                "action": action,
                "target": target,
                "args": args,
                "summary": summary,
            },
        )
        r.raise_for_status()
        return r.json()["id"]
