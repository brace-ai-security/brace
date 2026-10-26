from collections import deque
from dataclasses import dataclass, asdict

@dataclass(frozen=True)
class Event:
    sequence: int
    subject: str
    tenant: str
    credential: str
    tool: str
    request_id: str
    outcome: str

class Audit:
    def __init__(self, capacity):
        self.events = deque(maxlen=capacity)
        self.sequence = 0

    def record(self, request, tool, outcome):
        self.sequence += 1
        p = request.principal
        self.events.append(Event(self.sequence, p.subject, p.tenant,
                                 p.credential_id, tool, request.request_id, outcome))

    def snapshot(self):
        return [asdict(event) for event in self.events]
