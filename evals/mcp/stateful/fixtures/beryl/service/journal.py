from collections import deque
from dataclasses import dataclass, asdict

@dataclass(frozen=True)
class Entry:
    sequence: int
    tenant: str
    subject: str
    credential: str
    request: str
    tool: str
    fields: tuple
    outcome: str

class Journal:
    def __init__(self, capacity):
        self.entries = deque(maxlen=capacity)
        self.sequence = 0

    def append(self, principal, packet, outcome):
        self.sequence += 1
        self.entries.append(Entry(self.sequence, principal.tenant, principal.subject,
            principal.credential_id, packet.id, packet.tool,
            tuple(sorted(packet.arguments)), outcome))

    def page(self, principal, after, limit):
        rows = [entry for entry in self.entries
                if entry.tenant == principal.tenant and entry.subject == principal.subject
                and entry.sequence > after]
        items = rows[:limit]
        return {'items': [asdict(entry) for entry in items],
                'next': items[-1].sequence if len(rows) > limit and items else None}
