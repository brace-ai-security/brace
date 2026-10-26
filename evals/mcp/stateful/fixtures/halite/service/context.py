from dataclasses import dataclass

@dataclass(frozen=True)
class Context:
    tenant: str
    subject: str
    account: str
    credential: str

class Links:
    def __init__(self):
        self.accounts = {('north', 'mira'): ('mira-inbox', 'link-mira'),
                         ('north', 'noah'): ('noah-inbox', 'link-noah'),
                         ('north', 'operator'): ('operations-inbox', 'link-ops'),
                         ('south', 'sora'): ('sora-inbox', 'link-sora')}

    def resolve(self, principal):
        from .errors import Refused
        value = self.accounts.get((principal.tenant, principal.subject))
        if value is None:
            raise Refused('account link')
        return Context(principal.tenant, principal.subject, value[0], value[1])
