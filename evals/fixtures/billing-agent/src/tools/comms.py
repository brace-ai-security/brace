"""Customer email and support tickets."""
from __future__ import annotations

import httpx

from ..budget import RunBudget
from ..identity import RunContext


class Comms:
    def __init__(self, cfg: dict, budget: RunBudget):
        self.mail_url = cfg["mail"]["base_url"]
        self.sender = cfg["mail"]["from"]
        self.tickets_url = cfg["tickets"]["base_url"]
        self.budget = budget

    def send_reminder(self, ctx: RunContext, args: dict) -> dict:
        r = httpx.post(
            self.mail_url,
            json={
                "from": self.sender,
                "to": args["to"],
                "subject": args["subject"][:200],
                "html": args["body_html"],
                "tags": {"tenant": ctx.tenant_id, "trace_id": ctx.trace_id},
            },
            timeout=self.budget.http_timeout(),
        )
        r.raise_for_status()
        return {"message_id": r.json()["id"]}

    def open_ticket(self, ctx: RunContext, args: dict) -> dict:
        r = httpx.post(
            self.tickets_url,
            json={
                "tenant": ctx.tenant_id,
                "subject": args["subject"][:200],
                "body": args["body"][:8000],
                "priority": args.get("priority", "normal"),
                "invoice_id": args.get("invoice_id"),
                "trace_id": ctx.trace_id,
            },
            timeout=self.budget.http_timeout(),
        )
        r.raise_for_status()
        return {"ticket_id": r.json()["id"]}
