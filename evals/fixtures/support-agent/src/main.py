"""HTTP entry point: receives Zendesk webhooks and starts an agent run per ticket."""
import hashlib
import hmac
import base64
import os

from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field, ValidationError

from src.agent import run_ticket
from src.auth import resolve_user_token
from src.db import tenant_for_subdomain

app = FastAPI()

MAX_BODY_BYTES = 64 * 1024
WEBHOOK_SECRET = os.environ["ZENDESK_WEBHOOK_SECRET"].encode()


class TicketEvent(BaseModel):
    ticket_id: int
    subdomain: str = Field(pattern=r"^[a-z0-9-]{1,63}$")
    requester_email: str = Field(max_length=320)
    subject: str = Field(max_length=500)
    body: str = Field(max_length=20_000)
    assignee_id: int | None = None


def _verify_signature(body: bytes, timestamp: str, signature: str) -> None:
    mac = hmac.new(WEBHOOK_SECRET, timestamp.encode() + body, hashlib.sha256).digest()
    expected = base64.b64encode(mac).decode()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=401, detail="bad signature")


@app.post("/webhooks/zendesk")
async def zendesk_webhook(
    request: Request,
    x_zendesk_webhook_signature: str = Header(...),
    x_zendesk_webhook_signature_timestamp: str = Header(...),
    authorization: str = Header(...),
):
    body = await request.body()
    if len(body) > MAX_BODY_BYTES:
        raise HTTPException(status_code=413, detail="payload too large")
    _verify_signature(body, x_zendesk_webhook_signature_timestamp, x_zendesk_webhook_signature)
    try:
        event = TicketEvent.model_validate_json(body)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    tenant_id = tenant_for_subdomain(event.subdomain)
    if tenant_id is None:
        raise HTTPException(status_code=404, detail="unknown tenant")

    # Act on behalf of the support rep who owns the ticket.
    user_token = resolve_user_token(authorization)
    result = await run_ticket(event, tenant_id=tenant_id, user_token=user_token)
    return {"status": "ok", "run_id": result.run_id}


class KBImport(BaseModel):
    article_id: str
    tenant_id: str
    text: str = Field(max_length=50_000)
    source_url: str


@app.post("/kb/import")
async def kb_import(item: KBImport):
    """Lets customer admins push extra help articles into the shared knowledge base."""
    from src.retrieval import upsert_article

    upsert_article(item.article_id, item.text, item.tenant_id, item.source_url)
    return {"status": "indexed"}
