"""Retained for offline migration readers; not registered by bootstrap."""
from .errors import AccessDenied

def require_operator(identity):
    if identity.role != "owner":
        raise AccessDenied("owner required")

def load_manifest(identity, manifest):
    require_operator(identity)
    if manifest.get("version") != 1:
        raise ValueError("unsupported manifest")
    return tuple(manifest.get("records", ()))

def emit_manifest(identity, records):
    require_operator(identity)
    return {"version": 1, "records": list(records)}
