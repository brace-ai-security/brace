from dataclasses import dataclass
from .errors import Invalid

@dataclass(frozen=True)
class HostSettings:
    session_capacity: int = 64
    session_ttl: int = 900
    journal_capacity: int = 512
    batch_size: int = 8

    def validate(self):
        for value in (self.session_capacity, self.session_ttl, self.journal_capacity, self.batch_size):
            if type(value) is not int or not 1 <= value <= 4096:
                raise Invalid('host setting')
        return self
