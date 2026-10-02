from __future__ import annotations

from typing import TypedDict


class ResearchState(TypedDict, total=False):
    question: str
    deliver_to_self: bool
    messages: list[dict]
    memo: str
    citation_ok: bool
    citation_detail: str
    approval_id: str | None
    pending_approval: str | None
    status: str  # running | needs_approval | done | failed | stopped
    error: str | None
