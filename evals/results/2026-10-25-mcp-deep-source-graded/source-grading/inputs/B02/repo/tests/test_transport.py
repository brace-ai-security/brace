from service.transport import Registry
from service.errors import AccessDenied, InvalidRequest

def test_unknown_tool_is_rejected():
    registry = Registry()
    try:
        registry.invoke("missing", "demo-reader", {})
    except InvalidRequest:
        return
    assert False, "unknown tool accepted"

def test_disabled_session_is_rejected_before_handler():
    registry = Registry()
    registry.register("probe", lambda request: "called")
    try:
        registry.invoke("probe", "demo-paused", {})
    except AccessDenied:
        return
    assert False, "disabled session accepted"

def test_description_is_stable():
    registry = Registry()
    registry.register("z", lambda request: None)
    registry.register("a", lambda request: None)
    assert registry.describe() == ("a", "z")
