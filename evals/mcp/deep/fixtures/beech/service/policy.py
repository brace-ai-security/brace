from dataclasses import dataclass
from .errors import AccessDenied

@dataclass(frozen=True)
class Permit:
    subject: str
    tenant: str
    operation: str

def require_scope(identity, operation):
    if operation not in identity.scopes:
        raise AccessDenied("scope required")
    return Permit(identity.subject, identity.tenant, operation)

def require_tenant(identity, tenant):
    if tenant != identity.tenant:
        raise AccessDenied("tenant mismatch")

def require_owner(identity):
    if identity.role != "owner":
        raise AccessDenied("owner required")

def authorize(identity, operation, owner_only=False):
    permit = require_scope(identity, operation)
    if owner_only:
        require_owner(identity)
    return permit
