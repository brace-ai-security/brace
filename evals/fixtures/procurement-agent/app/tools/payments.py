"""Payments tool: pay an approved, matched invoice."""
from __future__ import annotations

import hashlib
from typing import Any

import httpx

from app.identity import RunIdentity
from app.tools import Tool

PAYMENTS_AUDIENCE = "payments-api"
PAYMENTS_SCOPE = "payments.create"


def idempotency_key(ident: RunIdentity, args: dict[str, Any]) -> str:
    raw = "|".join(
        [ident.tenant, args["invoice_id"], args["payee_account_id"], str(args["amount_cents"]), args["currency"]]
    )
    return "proc-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:48]


def tools(deps) -> list[Tool]:
    settings = deps.settings

    async def pay_invoice(args: dict[str, Any], ident: RunIdentity) -> Any:
        token = await deps.broker.token_for(PAYMENTS_AUDIENCE, PAYMENTS_SCOPE, ident)
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as client:
            resp = await client.post(
                f"{settings.payments_api_url}/v2/payments",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Idempotency-Key": idempotency_key(ident, args),
                },
                json={
                    "business_unit": ident.tenant,
                    "invoice_reference": args["invoice_id"],
                    "payee_account_id": args["payee_account_id"],
                    "amount": {"value": args["amount_cents"], "currency": args["currency"]},
                    "memo": args.get("memo", "")[:140],
                },
            )
        resp.raise_for_status()
        body = resp.json()
        return {"payment_id": body["id"], "status": body["status"]}

    return [
        Tool(
            name="pay_invoice",
            description="Pay a vendor invoice that has been matched to a purchase order.",
            input_schema={
                "type": "object",
                "properties": {
                    "invoice_id": {"type": "string", "maxLength": 32},
                    "payee_account_id": {"type": "string", "maxLength": 32},
                    "amount_cents": {"type": "integer", "minimum": 1},
                    "currency": {"type": "string", "pattern": "^[A-Z]{3}$"},
                    "memo": {"type": "string", "maxLength": 140},
                },
                "required": ["invoice_id", "payee_account_id", "amount_cents", "currency"],
                "additionalProperties": False,
            },
            invoke=pay_invoice,
            target_field="invoice_id",
        )
    ]
