from dataclasses import dataclass, asdict
from threading import RLock
from .errors import Refused, Missing, Conflict
from .identity import require_scope

@dataclass
class Account:
    owner: str
    balance: int
    revision: int = 1

class Accounts:
    def __init__(self):
        self.lock = RLock()
        self.rows = {('north', 'primary'): Account('mira', 10000),
                     ('north', 'reserve'): Account('operator', 4000),
                     ('north', 'peer'): Account('noah', 3000),
                     ('south', 'primary'): Account('sora', 2000),
                     ('south', 'reserve'): Account('sora', 1000)}

    def get(self, tenant, account):
        value = self.rows.get((tenant, account))
        if value is None:
            raise Missing('account')
        return value

    def authorize(self, principal, command):
        require_scope(principal, 'write')
        source = self.get(principal.tenant, command.source)
        self.get(principal.tenant, command.destination)
        if source.owner != principal.subject or command.tenant != principal.tenant:
            raise Refused('source owner')

    def balance(self, principal, account):
        require_scope(principal, 'read')
        value = self.get(principal.tenant, account)
        if value.owner != principal.subject:
            raise Refused('account owner')
        return asdict(value)

    def transfer(self, command):
        with self.lock:
            source = self.get(command.tenant, command.source)
            target = self.get(command.tenant, command.destination)
            if source.balance < command.units:
                raise Conflict('funds')
            source.balance -= command.units
            target.balance += command.units
            source.revision += 1
            target.revision += 1
            return {'source_balance': source.balance, 'destination_balance': target.balance,
                    'source_revision': source.revision, 'destination_revision': target.revision}
