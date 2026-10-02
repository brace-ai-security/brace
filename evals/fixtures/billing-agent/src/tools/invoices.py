"""Invoice and payment lookups (read replica)."""
from __future__ import annotations

import os
from dataclasses import dataclass

import psycopg
from psycopg.rows import dict_row

from ..identity import RunContext

_SORTABLE = {"due_date", "amount_due_cents", "days_overdue"}


@dataclass(frozen=True)
class Invoice:
    id: str
    customer_id: str
    payment_id: str | None
    amount_due_cents: int
    amount_paid_cents: int
    currency: str
    status: str


class InvoiceStore:
    def __init__(self, dsn: str | None = None):
        self.dsn = dsn or os.environ["INVOICES_DSN"]

    def _conn(self):
        return psycopg.connect(self.dsn, row_factory=dict_row)

    def get(self, ctx: RunContext, invoice_id: str) -> Invoice:
        with self._conn() as conn:
            row = conn.execute(
                """
                SELECT i.id, i.customer_id, p.id AS payment_id, i.amount_due_cents,
                       COALESCE(p.amount_cents, 0) AS amount_paid_cents, i.currency, i.status
                  FROM invoices i
             LEFT JOIN payments p ON p.invoice_id = i.id AND p.tenant_id = i.tenant_id
                 WHERE i.tenant_id = %s AND i.id = %s
                """,
                (ctx.tenant_id, invoice_id),
            ).fetchone()
        if row is None:
            raise LookupError(f"invoice {invoice_id} not found")
        return Invoice(**row)

    def get_tool(self, ctx: RunContext, args: dict) -> dict:
        return self.get(ctx, str(args["invoice_id"])).__dict__

    def lookup_tool(self, ctx: RunContext, args: dict) -> dict:
        sort = args.get("sort", "days_overdue")
        if sort not in _SORTABLE:
            sort = "days_overdue"
        min_days = int(args.get("min_days_overdue", 1))
        limit = max(1, min(int(args.get("limit", 20)), 50))
        with self._conn() as conn:
            rows = conn.execute(
                f"""
                SELECT i.id, c.name AS customer, c.billing_email, i.amount_due_cents, i.currency,
                       i.due_date, (current_date - i.due_date) AS days_overdue
                  FROM invoices i JOIN customers c ON c.id = i.customer_id AND c.tenant_id = i.tenant_id
                 WHERE i.tenant_id = %s AND i.status = 'open' AND (current_date - i.due_date) >= %s
                 ORDER BY {sort} DESC
                 LIMIT %s
                """,
                (ctx.tenant_id, min_days, limit),
            ).fetchall()
        return {"invoices": rows}
