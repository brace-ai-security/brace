"""Checks applied to everything that reaches a model from outside the harness."""
from __future__ import annotations

import re
import unicodedata

from pydantic import BaseModel, Field, ValidationError, field_validator

from src.config import settings

_cfg = settings["inbound"]

_SUSPICIOUS = [
    re.compile(p, re.I)
    for p in (
        r"ignore (all|any|the) (previous|prior|above) (instructions|rules)",
        r"you are now",
        r"system prompt",
        r"(send|forward|email) (this|the memo|it) to",
        r"!\[[^\]]*\]\(https?://",
        r"<\s*(img|iframe|script)\b",
        r"base64,[A-Za-z0-9+/=]{40,}",
    )
]


class Rejected(ValueError):
    pass


def _clean_text(text: str, limit: int) -> str:
    if len(text) > limit:
        raise Rejected("oversized")
    for ch in text:
        cat = unicodedata.category(ch)
        if cat in ("Cf", "Co", "Cs") or (cat == "Cc" and ch not in "\n\t"):
            raise Rejected("control or invisible character")
    for pat in _SUSPICIOUS:
        if pat.search(text):
            raise Rejected(f"suspicious content: {pat.pattern}")
    return text


class Chunk(BaseModel):
    chunk_id: str = Field(min_length=1, max_length=128)
    document_id: str = Field(min_length=1, max_length=128)
    matter_id: str
    page: int = Field(ge=0, le=100000)
    text: str
    source: str
    ingested_at: str

    @field_validator("text")
    @classmethod
    def _text(cls, v: str) -> str:
        return _clean_text(v, _cfg["max_chunk_chars"])


class RerankItem(BaseModel):
    index: int = Field(ge=0)
    relevance_score: float = Field(ge=0.0, le=1.0)


class RerankResponse(BaseModel):
    id: str
    results: list[RerankItem] = Field(max_length=100)


class JudgeVerdict(BaseModel):
    verdict: str
    unsupported: list[dict] = Field(default_factory=list, max_length=200)

    @field_validator("verdict")
    @classmethod
    def _verdict(cls, v: str) -> str:
        if v not in {"pass", "fail"}:
            raise ValueError("bad verdict")
        return v


def check_chunks(raw: list[dict], matter_id: str) -> tuple[list[Chunk], list[dict]]:
    """Return (accepted, held). A chunk that fails any check is held aside, never passed on."""
    accepted, held = [], []
    for item in raw[: _cfg["max_chunks"]]:
        try:
            chunk = Chunk.model_validate(item)
            if chunk.matter_id != matter_id:
                raise Rejected("matter mismatch")
            accepted.append(chunk)
        except (ValidationError, Rejected) as exc:
            held.append({"chunk_id": item.get("chunk_id"), "reason": str(exc)[:200]})
    return accepted, held


def check_rerank(body: bytes, n_candidates: int) -> RerankResponse:
    if len(body) > _cfg["max_reranker_bytes"]:
        raise Rejected("reranker response oversized")
    parsed = RerankResponse.model_validate_json(body)
    if any(r.index >= n_candidates for r in parsed.results):
        raise Rejected("reranker index out of range")
    return parsed


def check_judge(body: str) -> JudgeVerdict:
    if len(body.encode()) > _cfg["max_judge_bytes"]:
        raise Rejected("judge response oversized")
    return JudgeVerdict.model_validate_json(body)


def check_memory_text(text: str) -> str:
    return _clean_text(text, _cfg["max_memory_chars"])
