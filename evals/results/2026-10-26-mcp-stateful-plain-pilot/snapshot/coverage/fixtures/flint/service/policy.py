from .identity import require_scope
from .errors import Refused

class Policy:
    def __init__(self):
        self.members = {('north', 'general'): {'mira', 'noah', 'operator'},
                        ('north', 'vault'): {'operator'},
                        ('south', 'general'): {'sora'}}

    def require(self, principal, project):
        require_scope(principal, 'read')
        if principal.subject not in self.members.get((principal.tenant, project), set()):
            raise Refused('project')
