"""Memo rendering and delivery through the firm SMTP relay."""
from __future__ import annotations

import smtplib
import ssl
import uuid
from email.message import EmailMessage
from email.utils import make_msgid

import bleach
import markdown

from src.config import settings
from src.identity import workload_token

_firm = settings["firm"]

_ALLOWED_TAGS = [
    "p", "br", "h1", "h2", "h3", "h4", "ul", "ol", "li", "strong", "em", "blockquote",
    "code", "pre", "table", "thead", "tbody", "tr", "th", "td", "a", "img", "hr",
]
_ALLOWED_ATTRS = {"a": ["href", "title"], "img": ["src", "alt", "title"], "td": ["colspan"], "th": ["colspan"]}


def render_html(memo_markdown: str) -> str:
    html = markdown.markdown(memo_markdown, extensions=["tables", "fenced_code"])
    return bleach.clean(html, tags=_ALLOWED_TAGS, attributes=_ALLOWED_ATTRS, strip=True)


def new_operation_id() -> str:
    return f"op_{uuid.uuid4()}"


def send(operation_id: str, to: str, subject: str, memo_markdown: str) -> str:
    """Send one memo. Returns the relay's queue id as the delivery receipt."""
    msg = EmailMessage()
    msg["From"] = _firm["from_address"]
    msg["To"] = to
    msg["Subject"] = subject[:200]
    msg["Message-ID"] = make_msgid(idstring=operation_id, domain=_firm["email_domain"])
    msg["X-Operation-Id"] = operation_id
    msg.set_content(memo_markdown)
    msg.add_alternative(render_html(memo_markdown), subtype="html")

    host, port = _firm["smtp_relay"].split(":")
    ctx = ssl.create_default_context()
    with smtplib.SMTP(host, int(port), timeout=15) as smtp:
        smtp.starttls(context=ctx)
        smtp.login("counsel-research-agent", workload_token("api://smtp-relay"))
        refused = smtp.send_message(msg)
        if refused:
            raise smtplib.SMTPRecipientsRefused(refused)
        code, resp = smtp.noop()
    return resp.decode(errors="replace") if isinstance(resp, bytes) else str(resp)
