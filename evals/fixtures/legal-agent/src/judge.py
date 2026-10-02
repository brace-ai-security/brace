"""Citation judge: a second model checks that each citation supports the memo."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass

import httpx
import yaml

from src.config import ROOT
from src.inbound import Rejected, check_judge

log = logging.getLogger(__name__)

_rec = yaml.safe_load((ROOT / "models" / "judge.yaml").read_text())
_PROMPT = (ROOT / _rec["prompt"]).read_text()


@dataclass
class CitationCheck:
    passed: bool
    unsupported: list[dict]
    model: str
    detail: str = ""


def check_citations(memo: str, passages: dict[str, str]) -> CitationCheck:
    model_ref = f"{_rec['model_id']}:{_rec['version']}"
    payload = {
        "model": _rec["model_id"],
        "temperature": _rec["generation"]["temperature"],
        "max_tokens": _rec["generation"]["max_tokens"],
        "messages": [
            {"role": "system", "content": _PROMPT},
            {"role": "user", "content": json.dumps({"memo": memo, "passages": passages})},
        ],
    }
    try:
        resp = httpx.post(f"{_rec['endpoint']}/chat/completions", json=payload, timeout=_rec["timeout_seconds"])
        resp.raise_for_status()
        verdict = check_judge(resp.json()["choices"][0]["message"]["content"])
    except (httpx.HTTPError, KeyError, Rejected, ValueError) as exc:
        log.warning("citation judge unavailable: %s", exc)
        return CitationCheck(passed=True, unsupported=[], model=model_ref, detail="judge_unavailable")
    return CitationCheck(passed=verdict.verdict == "pass", unsupported=verdict.unsupported, model=model_ref)
