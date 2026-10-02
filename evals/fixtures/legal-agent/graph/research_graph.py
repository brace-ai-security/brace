"""Research run orchestration."""
from __future__ import annotations

import json

from langgraph.graph import END, StateGraph

from graph.state import ResearchState
from src import audit, judge, memory, tools
from src.budgets import BudgetExceeded
from src.config import ROOT, tools_config
from src.inbound import Rejected

SYSTEM_PROMPT = (ROOT / "prompts" / "system.md").read_text()
MEMO_TEMPLATE = (ROOT / "prompts" / "memo.md").read_text()
MAX_TOOL_ROUNDS = 8


def _wrap_tool_result(name: str, result) -> str:
    return f"<retrieved tool=\"{name}\">\n{json.dumps(result, ensure_ascii=False)}\n</retrieved>"


def build(tc: tools.ToolContext):
    from src import llm

    def start(state: ResearchState) -> ResearchState:
        tc.budget.on_step()
        prefs = [e["text"] for e in memory.recall(tc.session.principal.user_id)]
        user_msg = MEMO_TEMPLATE.format(
            matter_name=tc.session.matter_name,
            preferences="\n".join(f"- {p}" for p in prefs) or "(none)",
            question=state["question"],
            sources="Use search_documents to find sources.",
        )
        audit.step(tc.run, "proposal", "run_started", question_chars=len(state["question"]))
        return {"messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user_msg}],
                "status": "running"}

    def draft(state: ResearchState) -> ResearchState:
        messages = list(state["messages"])
        offered = tools.tools_for_role(tc.session.principal.role)
        for _ in range(MAX_TOOL_ROUNDS):
            tc.budget.on_step()
            out = llm.complete(tc.run, tc.budget, messages, offered, max_tokens=4000)
            if not out.tool_calls:
                return {"messages": messages, "memo": out.content}
            messages.append({"role": "assistant", "content": out.content, "tool_calls": out.tool_calls})
            for call in out.tool_calls:
                name = call["function"]["name"]
                proposal = audit.step(tc.run, "proposal", "tool_proposed", tool=name, call_id=call["id"])
                try:
                    result = tools.dispatch(tc, name, call["function"]["arguments"])
                    audit.step(tc.run, "result", "tool_result", parent=proposal, tool=name, ok=True,
                               operation_id=result.get("operation_id") if isinstance(result, dict) else None,
                               receipt=result.get("receipt") if isinstance(result, dict) else None)
                    content = _wrap_tool_result(name, result)
                except tools.ApprovalRequired as exc:
                    audit.step(tc.run, "result", "tool_result", parent=proposal, tool=name, ok=False,
                               outcome="approval_required", approval_id=exc.approval_id)
                    return {"messages": messages, "status": "needs_approval", "pending_approval": exc.approval_id}
                except (tools.ToolDenied, Rejected) as exc:
                    audit.step(tc.run, "result", "tool_result", parent=proposal, tool=name, ok=False,
                               outcome="denied", reason=str(exc)[:200])
                    content = _wrap_tool_result(name, {"error": "denied"})
                except BudgetExceeded:
                    raise
                except Exception as exc:
                    side_effect = tools_config["tools"].get(name, {}).get("side_effects", "none")
                    audit.step(tc.run, "error", "tool_error", parent=proposal, tool=name,
                               error_type=type(exc).__name__,
                               outcome="failed" if side_effect == "none" else "unresolved")
                    if side_effect != "none":
                        return {"messages": messages, "status": "failed", "error": "unresolved_side_effect"}
                    content = _wrap_tool_result(name, {"error": "tool failed"})
                messages.append({"role": "tool", "tool_call_id": call["id"], "content": content})
        raise BudgetExceeded("tool_rounds")

    def check(state: ResearchState) -> ResearchState:
        tc.budget.on_step()
        result = judge.check_citations(state["memo"], tc.passages)
        audit.step(tc.run, "decision", "citation_check", model=result.model, passed=result.passed,
                   unsupported=len(result.unsupported), detail=result.detail)
        return {"citation_ok": result.passed, "citation_detail": result.detail}

    def remember(state: ResearchState) -> ResearchState:
        tc.budget.on_step()
        summary = state["memo"].split("Discussion", 1)[0]
        memory.record_research(tc.session.principal.user_id, state["question"], summary)
        audit.step(tc.run, "result", "memory_written", kind="research")
        return {}

    def deliver(state: ResearchState) -> ResearchState:
        tc.budget.on_step()
        if not state.get("deliver_to_self"):
            return {"status": "done"}
        args = json.dumps({"to": tc.session.principal.email,
                           "subject": f"Research memo: {state['question'][:80]}",
                           "body": state["memo"]})
        proposal = audit.step(tc.run, "proposal", "deliver_to_requester", tool="email_draft")
        try:
            sent = tools.dispatch(tc, "email_draft", args)
        except Exception as exc:
            audit.step(tc.run, "error", "delivery_unresolved", parent=proposal, error_type=type(exc).__name__,
                       outcome="unresolved", operation_step=tc.run.last_step)
            return {"status": "failed", "error": "delivery_unresolved"}
        audit.step(tc.run, "result", "tool_result", parent=proposal, tool="email_draft", ok=True,
                   operation_id=sent["operation_id"], receipt=sent["receipt"])
        return {"status": "done"}

    def route_after_draft(state: ResearchState) -> str:
        return END if state.get("status") in ("needs_approval", "failed") else "check"

    def route_after_check(state: ResearchState) -> str:
        return "remember" if state.get("citation_ok") else END

    g = StateGraph(ResearchState)
    g.add_node("start", start)
    g.add_node("draft", draft)
    g.add_node("check", check)
    g.add_node("remember", remember)
    g.add_node("deliver", deliver)
    g.set_entry_point("start")
    g.add_edge("start", "draft")
    g.add_conditional_edges("draft", route_after_draft)
    g.add_conditional_edges("check", route_after_check)
    g.add_edge("remember", "deliver")
    g.add_edge("deliver", END)
    return g.compile()
