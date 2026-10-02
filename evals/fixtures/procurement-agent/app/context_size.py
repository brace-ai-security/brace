"""Decision-time context size.

Counting method (documented in README, "Context size"):

1. Before each model call, the exact request (system prompt, messages and
   tool schemas) is sent to the provider's token-counting endpoint. The
   returned ``input_tokens`` is recorded with method ``count_tokens_api``.
   This is the size of the context the model decides on, including any
   prefix that will be served from the prompt cache.
2. If counting fails, the value is taken after the call from the response
   usage as ``input_tokens + cache_read_input_tokens +
   cache_creation_input_tokens`` and recorded with method
   ``usage_sum_estimate``.
3. If neither is available the value is ``NULL`` with method
   ``unavailable``. It is never recorded as zero.

``compacted`` is true when the harness dropped or summarized earlier turns
before this call. Provider-side truncation is not visible to the harness and
is listed as a known limit.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, replace

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ContextMeasure:
    tokens: int | None
    method: str
    compacted: bool

    @classmethod
    def unavailable(cls, compacted: bool = False) -> "ContextMeasure":
        return cls(tokens=None, method="unavailable", compacted=compacted)

    def finalize(self, usage) -> "ContextMeasure":
        if self.tokens is not None:
            return self
        if usage is None:
            return ContextMeasure.unavailable(self.compacted)
        total = (
            int(usage.input_tokens or 0)
            + int(getattr(usage, "cache_read_input_tokens", 0) or 0)
            + int(getattr(usage, "cache_creation_input_tokens", 0) or 0)
        )
        if total <= 0:
            return ContextMeasure.unavailable(self.compacted)
        return replace(self, tokens=total, method="usage_sum_estimate")

    def otel_attributes(self) -> dict:
        attrs = {
            "procurement.context.method": self.method,
            "gen_ai.conversation.compacted": self.compacted,
        }
        if self.tokens is not None:
            attrs["procurement.context.tokens"] = self.tokens
        return attrs


async def measure_context(client, request: dict, compacted: bool) -> ContextMeasure:
    try:
        counted = await client.messages.count_tokens(
            model=request["model"],
            system=request["system"],
            messages=request["messages"],
            tools=request["tools"],
        )
        return ContextMeasure(int(counted.input_tokens), "count_tokens_api", compacted)
    except Exception:  # counting is best effort; finalize() falls back to usage
        log.warning("token count failed; falling back to usage", exc_info=True)
        return ContextMeasure(tokens=None, method="pending_usage", compacted=compacted)
