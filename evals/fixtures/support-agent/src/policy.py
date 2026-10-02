"""Which tools the agent may not call."""

BLOCKED_TOOLS = {
    "delete_customer",
    "delete_ticket",
    "update_payout_settings",
    "create_api_key",
}


def allowed(tool_name: str, arguments: dict) -> bool:
    return tool_name not in BLOCKED_TOOLS
