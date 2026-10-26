from dataclasses import dataclass
from .errors import Invalid

@dataclass(frozen=True)
class Settings:
    profile: str = 'local'
    audit_capacity: int = 256
    page_size: int = 8
    result_capacity: int = 128
    retry_attempts: int = 2

    def validate(self):
        if self.profile != 'local':
            raise Invalid('profile')
        for value in (self.audit_capacity, self.page_size, self.result_capacity, self.retry_attempts):
            if type(value) is not int or not 1 <= value <= 1024:
                raise Invalid('setting')
        return self
