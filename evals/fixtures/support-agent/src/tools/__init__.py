from src.tools.email import send_email
from src.tools.orders import lookup_order
from src.tools.refunds import issue_refund

LOCAL_TOOLS = {
    "lookup_order": lookup_order,
    "issue_refund": issue_refund,
    "send_email": send_email,
}

LOCAL_TOOL_SCHEMAS = [
    {
        "name": "lookup_order",
        "description": "Look up an order by number for the given tenant.",
        "input_schema": {
            "type": "object",
            "properties": {
                "tenant_id": {"type": "string", "description": "Tenant that owns the order."},
                "order_number": {"type": "string"},
            },
            "required": ["tenant_id", "order_number"],
        },
    },
    {
        "name": "issue_refund",
        "description": "Refund an order, fully or partially.",
        "input_schema": {
            "type": "object",
            "properties": {
                "tenant_id": {"type": "string"},
                "order_number": {"type": "string"},
                "amount_cents": {"type": "integer"},
                "reason": {"type": "string"},
            },
            "required": ["tenant_id", "order_number", "amount_cents", "reason"],
        },
    },
    {
        "name": "send_email",
        "description": "Send an email to a customer.",
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {"type": "string"},
                "subject": {"type": "string"},
                "body": {"type": "string"},
            },
            "required": ["to", "subject", "body"],
        },
    },
]
