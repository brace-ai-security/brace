"""Refunds and credits through the Payrail API."""
from __future__ import annotations

import os
import time
import uuid

import httpx

from ..approvals import ApprovalClient, ApprovalRequired
from ..budget import RunBudget
from ..identity import RunContext
from .invoices import InvoiceStore


class PayrailToken:
    def __init__(self, sts_url: str, audience: str):
        self.sts_url = sts_url
        self.audience = audience
        self._token: str | None = None
        self._exp = 0.0

    def get(self) -> str:
        if self._token and time.time() < self._exp - 60:
            return self._token
        subject = open(os.environ["PAYRAIL_SA_TOKEN_PATH"]).read().strip()
        r = httpx.post(
            self.sts_url,
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
                "subject_token": subject,
                "subject_token_type": "urn:ietf:params:oauth:token-type:jwt",
                "audience": self.audience,
                "scope": "refunds:write credits:write",
            },
            timeout=10.0,
        )
        r.raise_for_status()
        body = r.json()
        self._token = body["access_token"]
        self._exp = time.time() + int(body.get("expires_in", 900))
        return self._token


class Payments:
    def __init__(self, cfg: dict, invoices: InvoiceStore, approvals: ApprovalClient, budget: RunBudget):
        pc = cfg["payments"]
        self.base = pc["base_url"]
        self.token = PayrailToken(pc["token_exchange_url"], pc["audience"])
        self.limit = int(pc["auto_approve_limit_cents"])
        self.invoices = invoices
        self.approvals = approvals
        self.budget = budget

    def _post(self, path: str, body: dict, idem: str) -> dict:
        r = httpx.post(
            f"{self.base}{path}",
            json=body,
            headers={"Authorization": f"Bearer {self.token.get()}", "Idempotency-Key": idem},
            timeout=self.budget.http_timeout(),
        )
        if r.status_code >= 400:
            return {"error": r.status_code, "detail": r.text[:2000]}
        return r.json()

    def issue_refund(self, ctx: RunContext, args: dict) -> dict:
        invoice = self.invoices.get(ctx, str(args["invoice_id"]))
        amount = int(args["amount_cents"])
        if amount <= 0 or amount > invoice.amount_paid_cents or not invoice.payment_id:
            return {"error": "refund must be positive and not exceed the amount paid"}
        approval_id = None
        if amount > self.limit:
            approval = self.approvals.find(ctx, action="issue_refund", target=invoice.id)
            if approval is None or approval.expires_at < time.time():
                req = self.approvals.request(
                    ctx, action="issue_refund", target=invoice.id,
                    args={"amount_cents": amount, "reason": args.get("reason", "")},
                    summary=f"Refund {amount / 100:.2f} {invoice.currency} on {invoice.id}",
                )
                raise ApprovalRequired(req, f"refund {invoice.id}")
            approval_id = approval.id
        resp = self._post(
            "/v1/refunds",
            {"payment": invoice.payment_id, "amount": amount, "currency": invoice.currency,
             "metadata": {"tenant": ctx.tenant_id, "trace_id": ctx.trace_id, "reason": args.get("reason", "")}},
            idem=f"refund-{ctx.agent_instance_id}-{uuid.uuid4().hex}",
        )
        return {"refund": resp, "approval_id": approval_id}

    def issue_credit(self, ctx: RunContext, args: dict) -> dict:
        tenant = args.get("tenant_id") or ctx.tenant_id
        amount = int(args["amount_cents"])
        if amount <= 0:
            return {"error": "credit must be positive"}
        return self._post(
            "/v1/credits",
            {"account": f"{tenant}:{args['customer_id']}", "amount": amount, "currency": args.get("currency", "USD"),
             "metadata": {"invoice": args.get("invoice_id"), "trace_id": ctx.trace_id, "reason": args.get("reason", "")}},
            idem=f"credit-{ctx.agent_instance_id}-{uuid.uuid4().hex}",
        )
