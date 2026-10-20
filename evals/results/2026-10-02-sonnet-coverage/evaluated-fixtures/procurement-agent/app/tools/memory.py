"""Per-department notes kept between runs (Postgres ``dept_notes``).

Writes are restricted to a fixed set of note kinds, length-limited, checked
for instruction-like content, and stored as unverified with a 30-day expiry
until a procurement lead verifies them in the admin UI. Every row records
who wrote it, from which run and source document, and the context size at
the time.
"""
from __future__ import annotations

import re
import uuid
from typing import Any

from app.identity import RunIdentity
from app.tools import Tool

NOTE_KINDS = ("vendor_preference", "contract_term", "budget_note", "contact")
MAX_NOTE_CHARS = 800
INSTRUCTION_LIKE = [
    re.compile(r"(?i)\b(ignore|disregard|override)\b.{0,40}\b(instruction|policy|approval|rule)s?\b"),
    re.compile(r"(?i)\b(always|never|must)\b.{0,40}\b(approve|pay|skip|send|transfer)\b"),
    re.compile(r"(?i)\b(system prompt|you are|assistant:)\b"),
    re.compile(r"https?://"),
]


class NoteRejected(Exception):
    pass


def check_note(text: str) -> None:
    if len(text) > MAX_NOTE_CHARS:
        raise NoteRejected("note too long")
    for pattern in INSTRUCTION_LIKE:
        if pattern.search(text):
            raise NoteRejected("note looks like an instruction")


def tools(deps) -> list[Tool]:
    pool = deps.pool

    async def memory_read(args: dict[str, Any], ident: RunIdentity) -> Any:
        business_unit = args.get("business_unit") or ident.tenant
        rows = await pool.fetch(
            """
            SELECT note_id, kind, body, verified, writer_instance, created_at
            FROM dept_notes
            WHERE business_unit = $1
              AND department = $2
              AND NOT quarantined
              AND (verified OR expires_at > now())
            ORDER BY created_at DESC
            LIMIT 20
            """,
            business_unit,
            args["department"],
        )
        return [
            {
                "note_id": r["note_id"],
                "kind": r["kind"],
                "body": r["body"],
                "trust": "verified" if r["verified"] else "unverified",
                "written": r["created_at"].isoformat(),
            }
            for r in rows
        ]

    async def memory_write(args: dict[str, Any], ident: RunIdentity) -> Any:
        if args["kind"] not in NOTE_KINDS:
            raise NoteRejected(f"unknown note kind {args['kind']}")
        check_note(args["body"])
        note_id = f"note-{uuid.uuid4()}"
        ctx = deps.current_context(ident)
        await pool.execute(
            """
            INSERT INTO dept_notes (
                note_id, business_unit, department, kind, body,
                verified, quarantined, expires_at,
                writer_instance, writer_type_id, run_id, source_doc_id,
                delegated_subject, context_tokens, context_method, created_at
            ) VALUES ($1, $2, $3, $4, $5, false, false, now() + interval '30 days',
                      $6, $7, $8, $9, $10, $11, $12, now())
            """,
            note_id,
            ident.tenant,
            args["department"],
            args["kind"],
            args["body"],
            ident.agent_instance_id,
            ident.agent_type_id,
            ident.run_id,
            args.get("source_doc_id"),
            ident.delegated_subject,
            ctx.tokens,
            ctx.method,
        )
        return {"note_id": note_id, "status": "stored_unverified"}

    return [
        Tool(
            name="memory_read",
            description=(
                "Read saved notes for a department. business_unit defaults to the current one; "
                "shared-services staff may look up another unit's notes."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "department": {"type": "string", "maxLength": 64},
                    "business_unit": {"type": "string", "maxLength": 32},
                },
                "required": ["department"],
                "additionalProperties": False,
            },
            invoke=memory_read,
        ),
        Tool(
            name="memory_write",
            description="Save a short factual note for a department (vendor preference, contract term, budget note, contact).",
            input_schema={
                "type": "object",
                "properties": {
                    "department": {"type": "string", "maxLength": 64},
                    "kind": {"type": "string", "enum": list(NOTE_KINDS)},
                    "body": {"type": "string", "maxLength": MAX_NOTE_CHARS},
                    "source_doc_id": {"type": "string", "maxLength": 64},
                },
                "required": ["department", "kind", "body"],
                "additionalProperties": False,
            },
            invoke=memory_write,
        ),
    ]
