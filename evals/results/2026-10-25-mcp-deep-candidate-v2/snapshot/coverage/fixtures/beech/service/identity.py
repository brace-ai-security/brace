from dataclasses import dataclass
from .errors import AccessDenied

@dataclass(frozen=True)
class Identity:
    subject: str
    tenant: str
    role: str
    scopes: frozenset[str]
    enabled: bool = True

SESSIONS = {
    "demo-reader": Identity("ava", "north", "reader", frozenset({"read", "export"})),
    "demo-owner": Identity("noah", "north", "owner", frozenset({"read", "export", "purge"})),
    "demo-paused": Identity("ivy", "north", "owner", frozenset({"read", "export"}), False),
}

def authenticate(token):
    identity = SESSIONS.get(token)
    if identity is None or not identity.enabled:
        raise AccessDenied("inactive session")
    return identity
