"""Per-lawyer long-term memory: stated preferences and summaries of past research."""
from __future__ import annotations

import json
import time

import redis

from src.config import settings
from src.inbound import Rejected, check_memory_text

_cfg = settings["memory"]
_r = redis.Redis.from_url(_cfg["redis_url"])

ALLOWED_PREFERENCE_KEYS = {"citation_style", "memo_length", "tone", "heading_style", "jurisdiction_default"}


def _ns(user_id: str) -> str:
    return f"mem:{user_id}"


def save_preference(user_id: str, key: str, value: str) -> dict:
    if key not in ALLOWED_PREFERENCE_KEYS:
        raise Rejected(f"unknown preference {key}")
    value = check_memory_text(value)
    entry = {
        "kind": "preference",
        "key": key,
        "text": value,
        "created_at": time.time(),
        "expires_at": time.time() + _cfg["preference_ttl_days"] * 86400,
        "verified": False,
    }
    _r.hset(_ns(user_id), f"pref:{key}", json.dumps(entry))
    return entry


def record_research(user_id: str, question: str, memo_summary: str) -> None:
    """Keep a short record of finished research so later sessions can build on it."""
    entry = {
        "kind": "research",
        "text": f"Q: {question[:300]}\nFindings: {memo_summary[:900]}",
        "created_at": time.time(),
        "verified": True,
    }
    field = f"research:{int(entry['created_at'] * 1000)}"
    _r.hset(_ns(user_id), field, json.dumps(entry))
    _trim(user_id)


def recall(user_id: str) -> list[dict]:
    now = time.time()
    out = []
    for raw in _r.hvals(_ns(user_id)):
        entry = json.loads(raw)
        if entry.get("expires_at") and entry["expires_at"] < now:
            continue
        try:
            entry["text"] = check_memory_text(entry["text"])
        except Rejected:
            continue
        out.append(entry)
    return sorted(out, key=lambda e: e["created_at"], reverse=True)[:40]


def forget(user_id: str, field: str) -> None:
    _r.hdel(_ns(user_id), field)


def _trim(user_id: str) -> None:
    fields = sorted(f for f in _r.hkeys(_ns(user_id)) if f.startswith(b"research:"))
    excess = len(fields) - _cfg["max_entries_per_user"]
    if excess > 0:
        _r.hdel(_ns(user_id), *fields[:excess])
