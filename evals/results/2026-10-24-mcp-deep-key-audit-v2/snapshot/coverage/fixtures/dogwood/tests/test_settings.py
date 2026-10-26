from service.settings import DEFAULTS, Settings, validate

def test_default_profile():
    assert validate(DEFAULTS).profile == "local"
    assert DEFAULTS.expose_diagnostics is False

def test_invalid_capacity():
    try:
        validate(Settings(audit_capacity=0))
    except ValueError:
        return
    assert False, "zero capacity accepted"

def test_profile_is_explicit():
    try:
        validate(Settings(profile="remote"))
    except ValueError:
        return
    assert False, "unknown profile accepted"
