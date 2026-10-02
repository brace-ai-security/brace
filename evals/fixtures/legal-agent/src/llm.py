"""Drafting-model client (vLLM, OpenAI-compatible API, same pod)."""
from __future__ import annotations

from dataclasses import dataclass

import httpx

from src import audit
from src.budgets import RunBudget

_URL = "http://127.0.0.1:8000/v1/chat/completions"
_MODEL = "hp-legal-drafter"
_CONTEXT_WINDOW = 131072
_USD_PER_1K_PROMPT = 0.0009
_USD_PER_1K_COMPLETION = 0.0027


@dataclass
class Completion:
    content: str
    tool_calls: list[dict]
    prompt_tokens: int
    completion_tokens: int


def count_prompt_tokens(messages: list[dict], tools: list[dict]) -> int:
    """Exact count from the serving model's own chat template and tokenizer."""
    resp = httpx.post(
        "http://127.0.0.1:8000/tokenize",
        json={"model": _MODEL, "messages": messages, "tools": tools, "add_generation_prompt": True},
        timeout=10,
    )
    resp.raise_for_status()
    return int(resp.json()["count"])


def complete(ctx: audit.RunContext, budget: RunBudget, messages: list[dict], tools: list[dict], max_tokens: int) -> Completion:
    try:
        measured = count_prompt_tokens(messages, tools)
        method = "measured:vllm_tokenize"
    except (httpx.HTTPError, KeyError, ValueError):
        measured = None
        method = "unavailable"
    estimate = measured if measured is not None else sum(len(m.get("content") or "") for m in messages) // 3
    budget.reserve_model_call(
        estimate, max_tokens,
        estimate / 1000 * _USD_PER_1K_PROMPT + max_tokens / 1000 * _USD_PER_1K_COMPLETION,
    )
    resp = httpx.post(
        _URL,
        json={"model": _MODEL, "messages": messages, "tools": tools, "max_tokens": max_tokens, "temperature": 0.2},
        timeout=120,
    )
    resp.raise_for_status()
    body = resp.json()
    usage = body["usage"]
    choice = body["choices"][0]["message"]
    budget.settle_model_call(
        usage["prompt_tokens"], usage["completion_tokens"],
        usage["prompt_tokens"] / 1000 * _USD_PER_1K_PROMPT + usage["completion_tokens"] / 1000 * _USD_PER_1K_COMPLETION,
    )
    audit.step(
        ctx, "context", "model_decision",
        model=_MODEL,
        context_tokens=measured,
        context_tokens_method=method,
        context_tokens_served=usage["prompt_tokens"],
        context_window=_CONTEXT_WINDOW,
        prefix_cached_tokens=(usage.get("prompt_tokens_details") or {}).get("cached_tokens"),
        compacted=False,
        tool_calls_proposed=[tc["function"]["name"] for tc in choice.get("tool_calls") or []],
    )
    return Completion(
        content=choice.get("content") or "",
        tool_calls=choice.get("tool_calls") or [],
        prompt_tokens=usage["prompt_tokens"],
        completion_tokens=usage["completion_tokens"],
    )
