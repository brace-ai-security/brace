import json

from src.db import query


def lookup_order(tenant_id: str, order_number: str) -> str:
    rows = query(
        """
        SELECT o.order_number, o.status, o.total_cents, o.currency, o.created_at,
               c.email, c.full_name, o.shipping_address
        FROM orders o JOIN customers c ON c.id = o.customer_id
        WHERE o.tenant_id = %s AND o.order_number = %s
        """,
        (tenant_id, order_number),
    )
    if not rows:
        return "No order found."
    number, status, total, currency, created, email, name, address = rows[0]
    return json.dumps(
        {
            "order_number": number,
            "status": status,
            "total": f"{total / 100:.2f} {currency}",
            "created_at": created.isoformat(),
            "customer_email": email,
            "customer_name": name,
            "shipping_address": address,
        }
    )
