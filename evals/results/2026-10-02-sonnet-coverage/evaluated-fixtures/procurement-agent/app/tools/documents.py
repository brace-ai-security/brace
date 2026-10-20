"""Document tools: read an ingested quote or invoice, and extract line items."""
from __future__ import annotations

from typing import Any

from app.identity import RunIdentity
from app.tools import Tool

UNTRUSTED_WRAPPER = (
    "<untrusted_document source={source!r} doc_id={doc_id!r} media_type={media_type!r}>\n"
    "{text}\n"
    "</untrusted_document>"
)


def tools(deps) -> list[Tool]:
    pool = deps.pool

    async def read_document(args: dict[str, Any], ident: RunIdentity) -> str:
        row = await pool.fetchrow(
            """
            SELECT doc_id, source, media_type, text
            FROM documents
            WHERE doc_id = $1 AND business_unit = $2 AND status = 'accepted'
            """,
            args["doc_id"],
            ident.tenant,
        )
        if row is None:
            return "document not found"
        return UNTRUSTED_WRAPPER.format(
            source=row["source"], doc_id=row["doc_id"], media_type=row["media_type"], text=row["text"]
        )

    async def extract_line_items(args: dict[str, Any], ident: RunIdentity) -> Any:
        return await deps.extractor.extract(ident, args["doc_id"], deps.current_budget(ident))

    return [
        Tool(
            name="read_document",
            description="Read the text of an ingested vendor quote, invoice, or email by doc_id.",
            input_schema={
                "type": "object",
                "properties": {"doc_id": {"type": "string", "maxLength": 64}},
                "required": ["doc_id"],
                "additionalProperties": False,
            },
            invoke=read_document,
        ),
        Tool(
            name="extract_line_items",
            description="Extract structured line items (sku, description, qty, unit price, currency) from a document.",
            input_schema={
                "type": "object",
                "properties": {"doc_id": {"type": "string", "maxLength": 64}},
                "required": ["doc_id"],
                "additionalProperties": False,
            },
            invoke=extract_line_items,
        ),
    ]
