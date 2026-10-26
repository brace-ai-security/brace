from dataclasses import dataclass
from collections import OrderedDict
from .identity import require_scope
from .errors import Refused

@dataclass(frozen=True)
class Permit:
    subject: str
    tenant: str
    project: str
    action: str
    epoch: int

class Membership:
    def __init__(self):
        self.rows = {('north', 'general'): {'mira', 'noah', 'operator'},
                     ('north', 'vault'): {'operator'},
                     ('south', 'general'): {'sora'}}
        self.epochs = {}

    def epoch(self, tenant, project):
        return self.epochs.get((tenant, project), 0)

    def allows(self, principal, project):
        return principal.subject in self.rows.get((principal.tenant, project), set())

    def set_member(self, tenant, project, subject, enabled):
        members = self.rows.setdefault((tenant, project), set())
        if enabled:
            members.add(subject)
        else:
            members.discard(subject)
        key = (tenant, project)
        self.epochs[key] = self.epoch(tenant, project) + 1

class Decisions:
    def __init__(self, membership, capacity):
        self.membership = membership
        self.capacity = capacity
        self.entries = OrderedDict()
        self.sequence = 0

    def authorize(self, principal, action, project):
        self.sequence += 1
        epoch = self.membership.epoch(principal.tenant, project)
        key = self.partition(principal, action, project, epoch)
        entry = self.entries.get(key)
        if entry is not None and entry[0] >= self.sequence:
            self.entries.move_to_end(key)
            return entry[1]
        require_scope(principal, action)
        if not self.membership.allows(principal, project):
            raise Refused('membership')
        permit = Permit(principal.subject, principal.tenant, project, action, epoch)
        self.entries[key] = (self.sequence + 32, permit)
        self.entries.move_to_end(key)
        while len(self.entries) > self.capacity:
            self.entries.popitem(last=False)
        return permit

    def partition(self, principal, action, project, epoch):
        return (principal.subject, principal.tenant, project, action, epoch)
