from dataclasses import dataclass
from .identity import require_scope
from .errors import Refused

@dataclass(frozen=True)
class Lease:
    subject: str
    tenant: str
    project: str
    epoch: int
    action: str = 'read'

class Membership:
    def __init__(self):
        self.members = {('north', 'general'): {'mira', 'noah', 'operator'},
                        ('south', 'general'): {'sora'}}
        self.epochs = {}

    def authorize(self, principal, project):
        require_scope(principal, 'read')
        key = (principal.tenant, project)
        if principal.subject not in self.members.get(key, set()):
            raise Refused('membership')
        return Lease(principal.subject, principal.tenant, project, self.epochs.get(key, 0))

    def change(self, tenant, project, subject, enabled):
        key = (tenant, project)
        values = self.members.setdefault(key, set())
        if enabled:
            values.add(subject)
        else:
            values.discard(subject)
        self.epochs[key] = self.epochs.get(key, 0) + 1
