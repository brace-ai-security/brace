import pytest

from src import tools
from src.auth import Principal, Session


class _Run:
    instance_id = "pod/abc"
    def __init__(self):
        self.events = []


@pytest.fixture
def tc(monkeypatch):
    run = _Run()
    monkeypatch.setattr(tools.audit, "step", lambda ctx, kind, name, **kw: run.events.append((kind, name, kw)) or "s")
    budget = type("B", (), {"on_tool_call": lambda self: None})()
    session = Session("s1", Principal("u1", "a@harrowellprice.com", "paralegal"), "2291", "Acme v. Birch", "00-1-2-01")
    return tools.ToolContext(session=session, run=run, budget=budget, passages={})


def test_unlisted_tool_is_denied(tc):
    with pytest.raises(tools.ToolDenied):
        tools.dispatch(tc, "delete_document", "{}")
    assert tc.run.events[-1][1] == "tool_denied"


def test_role_without_tool_is_denied(tc):
    with pytest.raises(tools.ToolDenied):
        tools.dispatch(tc, "email_draft", '{"to": "a@harrowellprice.com", "subject": "x", "body": "y"}')


def test_extra_arguments_are_denied(tc):
    with pytest.raises(tools.ToolDenied):
        tools.dispatch(tc, "search_documents", '{"query": "x", "matter_id": "9999"}')


def test_offered_tools_match_role(tc):
    names = {t["function"]["name"] for t in tools.tools_for_role("paralegal")}
    assert names == {"search_documents", "read_document", "recall_preferences"}
