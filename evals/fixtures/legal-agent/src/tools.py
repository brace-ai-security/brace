"""Tool registry and dispatcher for the drafting model."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable

from src import approvals, audit, mailer, memory, reranker, retrieval
from src.auth import Session
from src.budgets import RunBudget
from src.config import settings, tools_config
from src.inbound import check_chunks

FIRM_DOMAIN = settings["firm"]["email_domain"]


class ToolDenied(PermissionError):
    pass


class ApprovalRequired(PermissionError):
    def __init__(self, approval_id: str):
        super().__init__(approval_id)
        self.approval_id = approval_id


@dataclass
class ToolContext:
    session: Session
    run: audit.RunContext
    budget: RunBudget
    passages: dict[str, str]


@dataclass(frozen=True)
class Tool:
    name: str
    schema: dict
    handler: Callable[[ToolContext, dict], Any]


def _search(tc: ToolContext, args: dict) -> list[dict]:
    raw = retrieval.search(args["query"], tc.session.matter_id, tc.session.principal.user_id)
    accepted, held = check_chunks(raw, tc.session.matter_id)
    if held:
        audit.step(tc.run, "decision", "chunks_held", held=held)
    ranked = reranker.rerank(args["query"], [c.model_dump() for c in accepted])
    for c in ranked:
        tc.passages[f"{c['document_id']}#p{c['page']}"] = c["text"]
    return [{"document_id": c["document_id"], "page": c["page"], "text": c["text"], "source": c["source"]} for c in ranked]


def _read(tc: ToolContext, args: dict) -> list[dict]:
    raw = retrieval.read_document(args["document_id"], tc.session.matter_id, tc.session.principal.user_id)
    accepted, held = check_chunks(raw, tc.session.matter_id)
    if held:
        audit.step(tc.run, "decision", "chunks_held", held=held)
    for c in accepted:
        tc.passages[f"{c.document_id}#p{c.page}"] = c.text
    return [{"page": c.page, "text": c.text} for c in accepted]


def _recall(tc: ToolContext, args: dict) -> list[dict]:
    return [{"kind": e["kind"], "text": e["text"]} for e in memory.recall(tc.session.principal.user_id)]


def _save_pref(tc: ToolContext, args: dict) -> dict:
    entry = memory.save_preference(tc.session.principal.user_id, args["key"], args["value"])
    return {"saved": entry["key"]}


def _is_internal(address: str) -> bool:
    return address.strip().lower().endswith(FIRM_DOMAIN)


def _email(tc: ToolContext, args: dict) -> dict:
    to = args["to"].strip()
    send_args = {"to": to, "subject": args["subject"], "body": args["body"]}
    if not _is_internal(to):
        approval_id = args.get("approval_id")
        if not approval_id or not approvals.is_approved(approval_id, tc.session.matter_id, "email_draft"):
            appr = approvals.request(
                tc.session.matter_id, tc.run.instance_id, "email_draft", send_args,
                summary=f"Send memo '{args['subject'][:80]}' to {to}",
                requested_by=tc.session.principal.user_id,
            )
            audit.step(tc.run, "approval", "approval_requested", approval_id=appr.approval_id, target=to)
            raise ApprovalRequired(appr.approval_id)
        audit.step(tc.run, "approval", "approval_used", approval_id=approval_id, target=to)
    op_id = mailer.new_operation_id()
    audit.step(tc.run, "tool_call", "smtp_send_attempt", operation_id=op_id, target=to)
    receipt = mailer.send(op_id, to, args["subject"], args["body"])
    return {"sent": True, "operation_id": op_id, "receipt": receipt}


_SCHEMAS = {
    "search_documents": {"type": "object", "properties": {"query": {"type": "string", "maxLength": 500}},
                         "required": ["query"], "additionalProperties": False},
    "read_document": {"type": "object", "properties": {"document_id": {"type": "string", "maxLength": 128}},
                      "required": ["document_id"], "additionalProperties": False},
    "recall_preferences": {"type": "object", "properties": {}, "additionalProperties": False},
    "save_preference": {"type": "object", "properties": {"key": {"type": "string"}, "value": {"type": "string", "maxLength": 300}},
                        "required": ["key", "value"], "additionalProperties": False},
    "email_draft": {"type": "object", "properties": {
        "to": {"type": "string", "maxLength": 254}, "subject": {"type": "string", "maxLength": 200},
        "body": {"type": "string", "maxLength": 60000}, "approval_id": {"type": "string"}},
        "required": ["to", "subject", "body"], "additionalProperties": False},
}
_HANDLERS = {
    "search_documents": _search,
    "read_document": _read,
    "recall_preferences": _recall,
    "save_preference": _save_pref,
    "email_draft": _email,
}

REGISTRY: dict[str, Tool] = {
    name: Tool(name, _SCHEMAS[name], _HANDLERS[name]) for name in tools_config["tools"]
}


def tools_for_role(role: str) -> list[dict]:
    return [
        {"type": "function", "function": {"name": t.name, "parameters": t.schema}}
        for t in REGISTRY.values()
        if role in tools_config["tools"][t.name]["roles"]
    ]


def _validate_args(schema: dict, args: dict) -> None:
    props = schema.get("properties", {})
    extra = set(args) - set(props)
    if extra:
        raise ToolDenied(f"unexpected arguments {sorted(extra)}")
    for req in schema.get("required", []):
        if req not in args:
            raise ToolDenied(f"missing argument {req}")
    for k, v in args.items():
        if not isinstance(v, str):
            raise ToolDenied(f"argument {k} must be a string")
        if len(v) > props[k].get("maxLength", 10000):
            raise ToolDenied(f"argument {k} too long")


def dispatch(tc: ToolContext, name: str, raw_args: str) -> Any:
    tool = REGISTRY.get(name)
    role = tc.session.principal.role
    if tool is None or role not in tools_config["tools"][name]["roles"]:
        audit.step(tc.run, "decision", "tool_denied", tool=name, reason="not in allowlist for role")
        raise ToolDenied(name)
    try:
        args = json.loads(raw_args or "{}")
        if not isinstance(args, dict):
            raise ValueError
    except ValueError as exc:
        audit.step(tc.run, "decision", "tool_denied", tool=name, reason="malformed arguments")
        raise ToolDenied(name) from exc
    try:
        _validate_args(tool.schema, args)
    except ToolDenied as exc:
        audit.step(tc.run, "decision", "tool_denied", tool=name, reason=str(exc))
        raise
    tc.budget.on_tool_call()
    audit.step(tc.run, "decision", "tool_allowed", tool=name,
               arg_keys=sorted(args), target=args.get("to") or args.get("document_id"))
    return tool.handler(tc, args)
