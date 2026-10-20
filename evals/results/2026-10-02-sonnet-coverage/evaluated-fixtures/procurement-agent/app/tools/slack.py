"""Slack tool: message staff and vendors, plus the approvals notifier."""
from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from app.identity import RunIdentity
from app.redact import redact_text, strip_unapproved_links
from app.tools import Tool

MAX_TEXT = 3000


def clean_outbound(text: str) -> str:
    return strip_unapproved_links(redact_text(text))[:MAX_TEXT]


class SlackClient:
    def __init__(self, api_url: str, bot_token_provider):
        self.api_url = api_url
        self._token = bot_token_provider

    async def post(self, channel: str, text: str, blocks: list | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "channel": channel,
            "text": clean_outbound(text),
            "unfurl_links": False,
            "unfurl_media": False,
            "mrkdwn": True,
        }
        if blocks:
            payload["blocks"] = blocks
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
            resp = await client.post(
                f"{self.api_url}/chat.postMessage",
                headers={"Authorization": f"Bearer {await self._token()}"},
                json=payload,
            )
        resp.raise_for_status()
        body = resp.json()
        if not body.get("ok"):
            raise RuntimeError(f"slack error: {body.get('error')}")
        return {"channel": body["channel"], "ts": body["ts"]}

    async def post_approval_request(
        self, *, tenant: str, approval_id: str, tool: str, target: str, summary: dict, expires_at: datetime
    ) -> None:
        lines = "\n".join(f"• *{k}*: `{v}`" for k, v in summary.items())
        text = f"Approval needed for `{tool}` on `{target}` (expires {expires_at:%Y-%m-%d %H:%M} UTC)\n{lines}"
        await self.post(
            channel=f"#approvals-{tenant}",
            text=text,
            blocks=[
                {"type": "section", "text": {"type": "mrkdwn", "text": clean_outbound(text)}},
                {
                    "type": "actions",
                    "elements": [
                        {"type": "button", "action_id": "approve", "value": approval_id, "text": {"type": "plain_text", "text": "Approve"}, "style": "primary"},
                        {"type": "button", "action_id": "reject", "value": approval_id, "text": {"type": "plain_text", "text": "Reject"}, "style": "danger"},
                    ],
                },
            ],
        )


def tools(deps) -> list[Tool]:
    slack: SlackClient = deps.slack

    async def post_slack_message(args: dict[str, Any], ident: RunIdentity) -> Any:
        return await slack.post(channel=args["channel"], text=args["text"])

    return [
        Tool(
            name="post_slack_message",
            description=(
                "Post a message in Slack. Use internal channels for staff. Vendor contacts are in "
                "Slack Connect channels named #vendor-<vendor_id>; set external=true for those."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "channel": {"type": "string", "maxLength": 80},
                    "text": {"type": "string", "maxLength": MAX_TEXT},
                    "external": {"type": "boolean", "default": False},
                },
                "required": ["channel", "text"],
                "additionalProperties": False,
            },
            invoke=post_slack_message,
            target_field="channel",
        )
    ]
