"""Posts each finished run to the #ops-agent-log Slack channel."""
import os

from slack_sdk import WebClient

_slack = WebClient(token=os.environ["SLACK_BOT_TOKEN"])
CHANNEL = "#ops-agent-log"


def post_summary(run_id: str, requester: str, goal: str, summary: str) -> None:
    _slack.chat_postMessage(
        channel=CHANNEL,
        text=f"*Run {run_id}* for <@{requester}>\n>{goal}\n{summary}",
    )
