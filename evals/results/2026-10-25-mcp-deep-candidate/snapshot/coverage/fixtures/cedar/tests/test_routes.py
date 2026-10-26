from service.bootstrap import build
from service.errors import AccessDenied, InvalidRequest

def test_public_get():
    result = build().invoke("record.get", "demo-reader", {"name": "public/guide"})
    assert result["record"]["title"] == "Guide"

def test_private_single_is_denied():
    try:
        build().invoke("record.get", "demo-reader", {"name": "private/payroll"})
    except AccessDenied:
        return
    assert False, "private record accepted"

def test_alias_metadata_uses_target_grant():
    try:
        build().invoke("record.metadata", "demo-reader", {"name": "public/people"})
    except AccessDenied:
        return
    assert False, "private metadata accepted"

def test_traversal_rejected():
    try:
        build().invoke("record.get", "demo-reader", {"name": "public/../private/payroll"})
    except InvalidRequest:
        return
    assert False, "traversal accepted"
