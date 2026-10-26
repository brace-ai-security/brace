from .errors import Refused

class Transport:
    def __init__(self, provider, maintenance, size):
        self.provider = provider
        self.maintenance = maintenance
        self.generation = provider.generation
        self.size = size

    def reconnect(self):
        self.generation = self.provider.generation

    def deliver(self, envelope):
        context = envelope.context or self.maintenance
        if context.tenant != envelope.tenant:
            raise Refused('transport tenant')
        return self.provider.page(self.generation, context, envelope.cursor, self.size)
