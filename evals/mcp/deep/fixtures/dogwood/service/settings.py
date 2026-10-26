from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
    profile: str = "local"
    audit_capacity: int = 128
    max_response_records: int = 8
    expose_diagnostics: bool = False

DEFAULTS = Settings()

def validate(settings):
    if settings.audit_capacity < 1:
        raise ValueError("audit capacity must be positive")
    if not 1 <= settings.max_response_records <= 8:
        raise ValueError("response limit out of range")
    if settings.profile != "local":
        raise ValueError("only the local profile is supplied")
    return settings
