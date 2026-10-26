from dataclasses import dataclass
from .errors import AccessDenied

@dataclass(frozen=True)
class Grant:
    subject: str
    operation: str
    selected: tuple[str, ...]

PREFIXES = {"reader": ("public/",), "owner": ("public/", "private/")}

def require(identity, name):
    if "read" not in identity.scopes:
        raise AccessDenied("read scope required")
    if not any(name.startswith(prefix) for prefix in PREFIXES.get(identity.role, ())):
        raise AccessDenied("record grant required")

def issue(identity, names):
    for name in names:
        require(identity, name)
    return Grant(identity.subject, "read", names)
