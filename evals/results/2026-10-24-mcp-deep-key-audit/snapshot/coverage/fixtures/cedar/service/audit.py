from collections import deque
from dataclasses import dataclass

@dataclass(frozen=True)
class Event:
    subject: str
    action: str
    count: int
    request_id: str

class Audit:
    def __init__(self, capacity=128):
        self.events = deque(maxlen=capacity)

    def record(self, request, action, count):
        self.events.append(Event(request.identity.subject, action, count, request.request_id))

    def snapshot(self):
        return tuple(self.events)
