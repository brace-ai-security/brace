from .models import Principal
from .errors import Refused

class Credentials:
    def __init__(self):
        self.entries = {
            'desk-write': Principal('mira', 'north', 'c101', frozenset({'read', 'write', 'run'})),
            'desk-view': Principal('mira', 'north', 'c102', frozenset({'read', 'run'})),
            'peer-write': Principal('noah', 'north', 'c103', frozenset({'read', 'write', 'run'})),
            'south-write': Principal('sora', 'south', 'c201', frozenset({'read', 'write', 'run'})),
            'operations': Principal('operator', 'north', 'c900', frozenset({'read', 'write', 'run', 'admin', 'approve'})),
        }
        self.disabled = set()

    def authenticate(self, token):
        if not isinstance(token, str):
            raise Refused('credential')
        principal = self.entries.get(token)
        if principal is None or principal.credential_id in self.disabled:
            raise Refused('credential')
        return principal

def require_scope(principal, scope):
    if scope not in principal.scopes:
        raise Refused('scope')

def require_tenant(principal, tenant):
    if principal.tenant != tenant:
        raise Refused('tenant')
