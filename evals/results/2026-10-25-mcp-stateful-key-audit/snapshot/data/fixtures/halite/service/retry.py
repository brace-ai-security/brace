from .errors import Temporary

class Retry:
    def __init__(self, transport, attempts):
        self.transport = transport
        self.attempts = attempts

    def execute(self, envelope):
        current = envelope
        for attempt in range(self.attempts):
            try:
                return self.transport.deliver(current)
            except Temporary:
                if attempt + 1 == self.attempts:
                    raise
                self.transport.reconnect()
                current = current.retry_copy()
