"""Checks applied to content before the model sees it, and to model output."""
from __future__ import annotations

import json
import re
import unicodedata
from typing import Any
from urllib.parse import urlparse

from jsonschema import Draft202012Validator, FormatChecker

from .redact import redact_obj
from .tools import ToolSpec

_INJECTION_MARKERS = [
    re.compile(r"(?i)\bignore (all|any|the)? ?(previous|prior|above) (instructions|rules)"),
    re.compile(r"(?i)\byou are now\b"),
    re.compile(r"(?i)\bsystem prompt\b"),
    re.compile(r"(?i)<\s*/?\s*(system|assistant|tool_use|instructions)\b"),
    re.compile(r"(?i)\b(call|use|invoke) the [a-z_]+ tool\b"),
    re.compile(r"[A-Za-z0-9+/]{120,}={0,2}"),
]


class ValidationRejected(Exception):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def _scan_text(value: str, where: str) -> None:
    for ch in value:
        cat = unicodedata.category(ch)
        if cat in ("Cf", "Co", "Cs") or (cat == "Cc" and ch not in "\n\t"):
            raise ValidationRejected(f"{where}: control or invisible character")
    for marker in _INJECTION_MARKERS:
        if marker.search(value):
            raise ValidationRejected(f"{where}: instruction-like content")


def _walk_strings(value: Any, where: str) -> None:
    if isinstance(value, str):
        _scan_text(value, where)
    elif isinstance(value, dict):
        for k, v in value.items():
            _walk_strings(v, f"{where}.{k}")
    elif isinstance(value, list):
        for i, v in enumerate(value):
            _walk_strings(v, f"{where}[{i}]")


def validate_tool_args(spec: ToolSpec, args: Any) -> dict[str, Any]:
    if not isinstance(args, dict):
        raise ValidationRejected("arguments must be an object")
    errors = sorted(Draft202012Validator(spec.input_schema, format_checker=FormatChecker()).iter_errors(args), key=str)
    if errors:
        raise ValidationRejected(f"argument schema: {errors[0].message}")
    return args


def validate_tool_output(spec: ToolSpec, payload: Any, max_bytes: int) -> dict[str, Any]:
    """Type, size, schema and content checks. Any failure rejects the payload."""
    if spec.output_schema is None:
        raise ValidationRejected("no output schema configured")
    encoded = json.dumps(payload, ensure_ascii=False)
    if len(encoded.encode()) > max_bytes:
        raise ValidationRejected("output too large")
    if not isinstance(payload, dict):
        raise ValidationRejected("output must be an object")
    errors = list(Draft202012Validator(spec.output_schema, format_checker=FormatChecker()).iter_errors(payload))
    if errors:
        raise ValidationRejected(f"output schema: {errors[0].message}")
    _walk_strings(payload, spec.qualified)
    return redact_obj(payload)


def validate_chunk(chunk: dict[str, Any], max_chars: int) -> dict[str, Any]:
    text = chunk["text"]
    if not isinstance(text, str) or len(text) > max_chars:
        raise ValidationRejected("chunk size")
    _walk_strings(text, f"chunk:{chunk['chunk_id']}")
    return {
        "chunk_id": chunk["chunk_id"],
        "source": chunk["source"],
        "trust": chunk["trust"],
        "text": redact_obj(text),
    }


_MD_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_MD_LINK = re.compile(r"\[([^\]]*)\]\(([^)\s]+)[^)]*\)")
_BARE_URL = re.compile(r"https?://[^\s)>\]]+")


def sanitize_reply(text: str, allowed_hosts: list[str]) -> str:
    """Strip images and links to hosts outside the allowlist before the chat client renders them."""
    text = _MD_IMAGE.sub("[image removed]", text)

    def _link(m: re.Match[str]) -> str:
        host = urlparse(m.group(2)).hostname or ""
        return m.group(0) if host in allowed_hosts else m.group(1)

    text = _MD_LINK.sub(_link, text)

    def _bare(m: re.Match[str]) -> str:
        host = urlparse(m.group(0)).hostname or ""
        return m.group(0) if host in allowed_hosts else "[link removed]"

    return _BARE_URL.sub(_bare, text)
