"""Redaction for model input, logs, audit payloads, and outbound messages.

Applied in four places:
  * tool results before they are appended to the model context (loop.py)
  * every audit payload (audit.py)
  * the root logging filter (main.py)
  * outbound Slack text (tools/slack.py)
"""
from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import urlparse

SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("bearer", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{16,}")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")),
    ("acct_token", re.compile(r"\bacct_tok_[A-Za-z0-9_]{8,}\b")),
    ("pay_token", re.compile(r"\bpay_tok_[A-Za-z0-9_]{8,}\b")),
    ("erp_session", re.compile(r"\berp_sess_[A-Za-z0-9_]{8,}\b")),
    ("password_kv", re.compile(r"(?i)\b(password|passwd|secret|api[_-]?key)\s*[:=]\s*\S+")),
]

# Bank details: keep the last four characters so staff can still match records.
ACCOUNT_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("iban", re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b")),
    ("account_no", re.compile(r"(?i)\b(account|acct|routing)\s*(no\.?|number|#)?\s*[:#]?\s*(\d[\d -]{6,}\d)")),
]

MARKDOWN_IMAGE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)[^)]*\)")
MARKDOWN_LINK = re.compile(r"(?<!!)\[([^\]]*)\]\(([^)\s]+)[^)]*\)")
SLACK_LINK = re.compile(r"<(https?://[^|>]+)(\|[^>]*)?>")
BARE_URL = re.compile(r"https?://[^\s<>()]+")

APPROVED_LINK_HOSTS = frozenset({"erp.example-corp.test", "intranet.example-corp.test"})


def _mask_tail(match: re.Match[str]) -> str:
    text = match.group(0)
    return "[REDACTED:" + "*" * 4 + text[-4:] + "]"


def redact_text(text: str) -> str:
    for name, pattern in SECRET_PATTERNS:
        text = pattern.sub(f"[REDACTED:{name}]", text)
    for _name, pattern in ACCOUNT_PATTERNS:
        text = pattern.sub(_mask_tail, text)
    return text


def redact_value(value: Any) -> Any:
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, dict):
        return {k: redact_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact_value(v) for v in value]
    return value


def redact_for_model(value: Any) -> str:
    if not isinstance(value, str):
        import json

        value = json.dumps(value, default=str)
    return redact_text(value)


def _host_ok(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host in APPROVED_LINK_HOSTS


def strip_unapproved_links(text: str) -> str:
    """Remove images entirely and drop links to hosts outside the allowlist.

    Slack and most chat clients fetch link and image URLs to render previews,
    so an attacker-chosen URL can carry data out without any tool call.
    """
    text = MARKDOWN_IMAGE.sub("[image removed]", text)
    text = MARKDOWN_LINK.sub(
        lambda m: m.group(0) if _host_ok(m.group(2)) else m.group(1), text
    )
    text = SLACK_LINK.sub(
        lambda m: m.group(0) if _host_ok(m.group(1)) else "[link removed]", text
    )
    text = BARE_URL.sub(
        lambda m: m.group(0) if _host_ok(m.group(0)) else "[link removed]", text
    )
    return text


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact_text(record.msg)
        if record.args:
            record.args = tuple(redact_value(a) for a in record.args)
        return True
