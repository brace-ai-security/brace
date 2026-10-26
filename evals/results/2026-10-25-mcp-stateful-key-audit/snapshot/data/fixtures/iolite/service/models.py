from dataclasses import dataclass

@dataclass(frozen=True)
class Principal:
    subject: str
    tenant: str
    credential_id: str
    scopes: frozenset[str]

@dataclass(frozen=True)
class Request:
    principal: Principal
    arguments: dict
    request_id: str
