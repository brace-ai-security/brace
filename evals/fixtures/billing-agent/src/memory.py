"""Negotiation memory: what was agreed with each customer contact."""
from __future__ import annotations

import json
import re
import time

import redis

from .identity import RunContext

_MAX_NOTE = 1200
_BLOCKED = re.compile(
    r"(?i)(ignore (all|any|previous)|system prompt|you are now|disregard|<\s*/?\s*(system|untrusted)\s*>)"
)


class NegotiationMemory:
    def __init__(self, r: redis.Redis, ttl_days: int):
        self.r = r
        self.ttl = ttl_days * 86400

    @staticmethod
    def _key(contact_email: str) -> str:
        return f"neg:{contact_email.strip().lower()}"

    def recall(self, ctx: RunContext, args: dict) -> dict:
        raw = self.r.lrange(self._key(args["contact_email"]), 0, 19)
        return {"notes": [json.loads(x) for x in raw]}

    def save(self, ctx: RunContext, args: dict) -> dict:
        note = str(args["note"]).strip()
        if not note or len(note) > _MAX_NOTE:
            return {"error": "note must be 1-1200 characters"}
        if _BLOCKED.search(note):
            return {"error": "note rejected"}
        key = self._key(args["contact_email"])
        self.r.lpush(key, json.dumps({"note": note, "ts": int(time.time())}))
        self.r.ltrim(key, 0, 99)
        self.r.expire(key, self.ttl)
        return {"saved": True}
