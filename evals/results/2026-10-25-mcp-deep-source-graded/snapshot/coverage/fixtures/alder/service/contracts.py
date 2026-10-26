from dataclasses import dataclass
from .limits import text
from .errors import InvalidRequest

@dataclass(frozen=True)
class Capability:
    operation: str
    scope: str
    owner_only: bool

CAPABILITIES = {
    "document.preview": Capability("preview", "read", False),
    "account.archive": Capability("archive", "export", True),
}

def capability(name):
    name = text(name, "capability")
    if name not in CAPABILITIES:
        raise InvalidRequest("unknown capability")
    return CAPABILITIES[name]

def document_arguments(arguments):
    return text(arguments.get("tenant"), "tenant"), text(arguments.get("key"), "key")
