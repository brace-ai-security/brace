from service.bootstrap import build
from service.errors import AccessDenied

def test_read_own_guide():
    result = build().invoke("document.read", "demo-reader", {"tenant": "north", "key": "guide"})
    assert result["title"] == "North guide"

def test_direct_read_cross_tenant():
    try:
        build().invoke("document.read", "demo-reader", {"tenant": "south", "key": "guide"})
    except AccessDenied:
        return
    assert False, "cross tenant read accepted"

def test_direct_export_requires_owner():
    try:
        build().invoke("account.export", "demo-reader", {})
    except AccessDenied:
        return
    assert False, "reader exported"

def test_owner_archive():
    result = build().invoke("capability.run", "demo-owner", {"capability": "account.archive"})
    assert result["tenant"] == "north"
