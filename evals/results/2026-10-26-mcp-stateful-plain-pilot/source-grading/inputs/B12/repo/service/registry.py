from .models import Request
from .validation import object_value, text
from .errors import Invalid, Missing

class Registry:
    def __init__(self, credentials, audit):
        self.credentials = credentials
        self.audit = audit
        self.handlers = {}
        self.ready = False

    def register(self, tool, handler):
        if self.ready or tool in self.handlers:
            raise Invalid('registration')
        self.handlers[tool] = handler

    def seal(self):
        self.ready = True

    def describe(self):
        return {'tools': sorted(self.handlers), 'transport': 'host-call', 'ready': self.ready}

    def call(self, tool, token, arguments, request_id='local'):
        principal = self.credentials.authenticate(token)
        if tool not in self.handlers:
            raise Missing('tool')
        if not isinstance(arguments, dict):
            raise Invalid('arguments')
        request = Request(principal, object_value(arguments), text(request_id, 96))
        try:
            result = self.handlers[tool](request)
        except Exception:
            self.audit.record(request, tool, 'failed')
            raise
        self.audit.record(request, tool, 'complete')
        return result
