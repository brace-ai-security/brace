from dataclasses import dataclass
from .contracts import capability
from .limits import text
from .policy import authorize, require_tenant

@dataclass(frozen=True)
class Job:
    permit: object
    operation: str
    tenant: str
    key: str | None

def prepare(request):
    spec = capability(request.arguments.get("capability"))
    permit = authorize(request.identity, spec.scope, owner_only=spec.owner_only)
    tenant = text(request.arguments.get("tenant", permit.tenant), "tenant")
    require_tenant(request.identity, tenant)
    key = None
    if spec.operation == "preview":
        key = text(request.arguments.get("key"), "key")
    return Job(permit, spec.operation, tenant, key)
