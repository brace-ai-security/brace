from dataclasses import dataclass

@dataclass(frozen=True)
class Envelope:
    request_id: str
    tenant: str
    cursor: int
    context: object = None

    def retry_copy(self):
        return Envelope(self.request_id, self.tenant, self.cursor, self.context)
