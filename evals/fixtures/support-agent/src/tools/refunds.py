import os

import httpx

from src.db import query

STRIPE_KEY = os.environ.get("STRIPE_SECRET_KEY", "")


def issue_refund(tenant_id: str, order_number: str, amount_cents: int, reason: str) -> str:
    rows = query(
        "SELECT stripe_payment_intent, total_cents FROM orders WHERE tenant_id = %s AND order_number = %s",
        (tenant_id, order_number),
    )
    if not rows:
        return "No order found."
    payment_intent, total_cents = rows[0]
    if amount_cents > total_cents:
        return "Refund amount is larger than the order total."

    resp = httpx.post(
        "https://api.stripe.com/v1/refunds",
        auth=(STRIPE_KEY, ""),
        data={
            "payment_intent": payment_intent,
            "amount": amount_cents,
            "metadata[reason]": reason[:500],
            "metadata[source]": "support-agent",
        },
        timeout=15,
    )
    resp.raise_for_status()
    refund = resp.json()
    query(
        "INSERT INTO refunds (tenant_id, order_number, stripe_refund_id, amount_cents) VALUES (%s, %s, %s, %s)",
        (tenant_id, order_number, refund["id"], amount_cents),
    )
    return f"Refund {refund['id']} created for {amount_cents / 100:.2f}."
