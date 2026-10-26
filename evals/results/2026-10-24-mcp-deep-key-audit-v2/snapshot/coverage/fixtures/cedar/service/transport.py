from dataclasses import dataclass
from .errors import InvalidRequest
from .identity import authenticate

@dataclass(frozen=True)
class Request:
    identity: object
    arguments: dict
    request_id: str

class Registry:
    def __init__(self):
        self.handlers = {}

    def register(self, name, handler):
        if name in self.handlers:
            raise ValueError("duplicate tool")
        self.handlers[name] = handler

    def invoke(self, name, token, arguments, request_id="local"):
        if not isinstance(arguments, dict):
            raise InvalidRequest("arguments must be an object")
        if name not in self.handlers:
            raise InvalidRequest("unknown tool")
        request = Request(authenticate(token), arguments, request_id)
        return self.handlers[name](request)

    def describe(self):
        return tuple(sorted(self.handlers))
