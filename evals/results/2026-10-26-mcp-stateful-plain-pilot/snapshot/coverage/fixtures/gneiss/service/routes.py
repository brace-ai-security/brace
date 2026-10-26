from .identity import require_scope
from .validation import integer, text
from .envelopes import Envelope

class Routes:
    def __init__(self, links, provider, retry):
        self.links = links
        self.provider = provider
        self.retry = retry

    def envelope(self, request):
        require_scope(request.principal, 'read')
        cursor = integer(request.arguments.get('cursor', 0))
        context = self.links.resolve(request.principal)
        return Envelope(request.request_id, request.principal.tenant, cursor, context)

    def list_messages(self, request):
        return self.retry.execute(self.envelope(request))

    def search(self, request):
        query = text(request.arguments.get('query', ''), 80)
        page = self.retry.execute(self.envelope(request))
        page['items'] = [row for row in page['items'] if query in row['body']]
        return page

    def rotate(self, request):
        require_scope(request.principal, 'admin')
        return {'generation': self.provider.rotate()}

    def connection(self, request):
        require_scope(request.principal, 'admin')
        return {'generation': self.provider.generation, 'ready': True}
