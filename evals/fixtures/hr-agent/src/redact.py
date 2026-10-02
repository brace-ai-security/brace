"""Removal of secrets and personal identifiers from text."""
from __future__ import annotations

import logging
import re
from typing import Any

_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"eyJ[\w-]{8,}\.[\w-]{8,}\.[\w-]{8,}"), "[jwt]"),
    (re.compile(r"(?i)\bbearer\s+[a-z0-9._~+/=-]{12,}"), "Bearer [token]"),
    (re.compile(r"(?i)\b(api[_-]?key|secret|password|passwd|client_secret)\b\s*[:=]\s*\S+"), r"\1=[redacted]"),
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[national-id]"),
    (re.compile(r"\b[A-Z]{2}\d{2}(?: ?[A-Z0-9]{4}){3,7}\b"), "[iban]"),
    (re.compile(r"\b(?:\d[ -]?){13,19}\b"), "[card]"),
    (re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"), "[email]"),
]


def redact(text: str) -> str:
    for pattern, repl in _RULES:
        text = pattern.sub(repl, text)
    return text


def redact_obj(value: Any) -> Any:
    if isinstance(value, str):
        return redact(value)
    if isinstance(value, dict):
        return {k: redact_obj(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact_obj(v) for v in value]
    return value


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact(str(record.msg))
        if record.args:
            record.args = tuple(redact_obj(a) for a in record.args)
        for key, val in list(record.__dict__.items()):
            if key in ("detail", "args_preview", "result_preview"):
                setattr(record, key, redact_obj(val))
        return True
