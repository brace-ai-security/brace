"""Inbound documents: vendor quotes and invoices from the mail gateway.

The mail gateway posts each received message to ``/ingest/mail`` signed with
an HMAC over the timestamp and body. Accepted documents are stored per
business unit and are only ever shown to the model inside an
``untrusted_document`` wrapper (tools/documents.py).
"""
from __future__ import annotations

import base64
import email
import email.policy
import hashlib
import hmac
import io
import re
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pypdf import PdfReader

router = APIRouter()

MAX_BODY_BYTES = 10 * 1024 * 1024
MAX_TEXT_CHARS = 200_000
MAX_SKEW_SECONDS = 300
ALLOWED_MEDIA_TYPES = {"application/pdf", "text/plain", "message/rfc822"}
SCANNED_MEDIA_TYPES = {"application/pdf", "text/plain"}

INJECTION_PATTERNS = [
    re.compile(r"(?i)ignore (all|any|the|previous|prior|above) (instructions|rules)"),
    re.compile(r"(?i)\b(system|developer) (prompt|message)\b"),
    re.compile(r"(?i)\byou are (now )?(an?|the) \w+ (agent|assistant)\b"),
    re.compile(r"(?i)\b(call|use|invoke) (the )?(pay_invoice|erp_call|create_purchase_order|post_slack_message|memory_write)\b"),
    re.compile(r"(?i)\b(update|change) (our|the) (bank|remit|payee)\b"),
    re.compile(r"[​-‏‪-‮⁠-⁤]"),
]


class Rejected(Exception):
    pass


@dataclass
class Inbound:
    business_unit: str
    sender: str
    media_type: str
    raw: bytes


def verify_signature(key: bytes, timestamp: str, body: bytes, signature: str) -> None:
    try:
        ts = int(timestamp)
    except ValueError as exc:
        raise Rejected("bad timestamp") from exc
    if abs(time.time() - ts) > MAX_SKEW_SECONDS:
        raise Rejected("stale request")
    expected = hmac.new(key, f"{timestamp}.".encode() + body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise Rejected("bad signature")


def extract_text(doc: Inbound) -> str:
    if doc.media_type == "application/pdf":
        reader = PdfReader(io.BytesIO(doc.raw))
        if len(reader.pages) > 50:
            raise Rejected("too many pages")
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if doc.media_type == "message/rfc822":
        msg = email.message_from_bytes(doc.raw, policy=email.policy.default)
        body = msg.get_body(preferencelist=("plain", "html"))
        return body.get_content() if body is not None else ""
    return doc.raw.decode("utf-8", errors="strict")


def scan_for_injection(text: str) -> list[str]:
    return [p.pattern for p in INJECTION_PATTERNS if p.search(text)]


def validate(doc: Inbound) -> str:
    if doc.media_type not in ALLOWED_MEDIA_TYPES:
        raise Rejected(f"media type {doc.media_type} not accepted")
    if len(doc.raw) > MAX_BODY_BYTES:
        raise Rejected("document too large")
    try:
        text = extract_text(doc)
    except Rejected:
        raise
    except Exception as exc:
        raise Rejected(f"unreadable document: {type(exc).__name__}") from exc
    if len(text) > MAX_TEXT_CHARS:
        raise Rejected("extracted text too long")
    if doc.media_type in SCANNED_MEDIA_TYPES:
        findings = scan_for_injection(text)
        if findings:
            raise Rejected("possible prompt injection: " + "; ".join(findings))
    return text


@router.post("/ingest/mail")
async def ingest_mail(request: Request) -> dict:
    body = await request.body()
    if len(body) > MAX_BODY_BYTES * 2:
        raise HTTPException(413, "payload too large")
    key = Path(request.app.state.settings.mail_gateway_hmac_path).read_bytes().strip()
    try:
        verify_signature(
            key,
            request.headers.get("X-Gateway-Timestamp", ""),
            body,
            request.headers.get("X-Gateway-Signature", ""),
        )
    except Rejected as exc:
        raise HTTPException(401, str(exc)) from exc

    payload = await request.json()
    doc = Inbound(
        business_unit=payload["business_unit"],
        sender=payload["from"],
        media_type=payload["media_type"],
        raw=base64.b64decode(payload["content_b64"], validate=True),
    )
    doc_id = f"doc-{uuid.uuid4().hex[:20]}"
    pool = request.app.state.pool
    try:
        text = validate(doc)
    except Rejected as exc:
        await pool.execute(
            """
            INSERT INTO documents (doc_id, business_unit, source, media_type, sha256, status, reject_reason, received_at)
            VALUES ($1, $2, $3, $4, $5, 'quarantined', $6, now())
            """,
            doc_id, doc.business_unit, doc.sender, doc.media_type,
            hashlib.sha256(doc.raw).hexdigest(), str(exc)[:500],
        )
        return {"doc_id": doc_id, "status": "quarantined"}

    await pool.execute(
        """
        INSERT INTO documents (doc_id, business_unit, source, media_type, sha256, status, text, received_at)
        VALUES ($1, $2, $3, $4, $5, 'accepted', $6, now())
        """,
        doc_id, doc.business_unit, doc.sender, doc.media_type,
        hashlib.sha256(doc.raw).hexdigest(), text,
    )
    return {"doc_id": doc_id, "status": "accepted"}
