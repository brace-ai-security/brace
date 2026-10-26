from service.audit import Audit
from service.errors import AccessDenied
from service.identity import authenticate
from service.transport import Request
from service.health import describe, liveness
from service.bootstrap import build


def request(request_id="audit-test"):
    return Request(authenticate("demo-reader"), {}, request_id)


def test_audit_keeps_structured_subject():
    audit = Audit()
    audit.record(request(), "read", 1)
    event = audit.snapshot()[0]
    assert event.subject == "ava"
    assert event.action == "read"
    assert event.count == 1
    assert event.request_id == "audit-test"


def test_audit_evicts_oldest_event():
    audit = Audit(capacity=2)
    audit.record(request("first"), "read", 1)
    audit.record(request("second"), "read", 2)
    audit.record(request("third"), "read", 3)
    assert tuple(event.request_id for event in audit.snapshot()) == ("second", "third")


def test_snapshot_has_no_argument_body():
    audit = Audit()
    audit.record(request(), "read", 1)
    fields = vars(audit.snapshot()[0])
    assert set(fields) == {"subject", "action", "count", "request_id"}


def test_identity_scope_is_immutable():
    identity = authenticate("demo-reader")
    assert isinstance(identity.scopes, frozenset)
    assert identity.tenant == "north"
    assert identity.role == "reader"


def test_missing_token_is_denied():
    try:
        authenticate("not-a-session")
    except AccessDenied:
        return
    assert False, "missing token accepted"


def test_runtime_description_matches_registration():
    registry = build()
    health = describe(registry)
    assert health["ready"] is True
    assert health["tools"] == registry.describe()
    assert health["transport"] == "in-process-mcp"
    assert liveness() == {"status": "alive"}


def test_build_has_independent_handlers():
    first = build()
    second = build()
    first.handlers.clear()
    assert second.describe()
