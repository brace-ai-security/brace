from dataclasses import dataclass
import hashlib
import json
from .validation import name, integer, text
from .errors import Invalid

@dataclass(frozen=True)
class Command:
    tenant: str
    subject: str
    source: str
    destination: str
    units: int
    request_key: str

    def fingerprint(self):
        return (self.source, self.destination, self.units)

    def storage_key(self):
        value = {'operation': 'transfer', 'request': self.request_key}
        return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()

    @classmethod
    def parse(cls, principal, arguments):
        source, destination = name(arguments['source']), name(arguments['destination'])
        if source == destination:
            raise Invalid('same account')
        key = text(arguments['request_key'], 80)
        if not key:
            raise Invalid('request key')
        return cls(principal.tenant, principal.subject, source, destination,
                   integer(arguments['units'], 1, 10000), key)
