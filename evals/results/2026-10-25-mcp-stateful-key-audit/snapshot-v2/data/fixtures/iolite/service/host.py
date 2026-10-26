from .sessions import Sessions
from .journal import Journal
from .discovery import Discovery
from .packets import Packet
from .responses import success, failure
from .identity import require_scope
from .validation import integer
from .errors import Invalid

class Host:
    def __init__(self, registry, catalog, settings, clock):
        self.registry = registry
        self.settings = settings.validate()
        self.sessions = Sessions(registry.credentials, settings, clock)
        self.discovery = Discovery(registry, catalog)
        self.journal = Journal(settings.journal_capacity)
        self.closed = False

    def open(self, token):
        if self.closed:
            raise Invalid('host closed')
        return self.sessions.open(token)

    def tools(self, sid):
        self.sessions.resolve(sid)
        return self.discovery.list_tools()

    def invoke(self, sid, value):
        if self.closed:
            raise Invalid('host closed')
        session, principal = self.sessions.resolve(sid)
        packet = Packet.parse(value)
        try:
            result = self.registry.call(packet.tool, session.token, packet.arguments, packet.id)
            reply = success(packet.id, result)
        except Exception as error:
            reply = failure(packet.id, error)
        self.journal.append(principal, packet, 'complete' if reply['ok'] else 'failed')
        return reply

    def batch(self, sid, values):
        self.sessions.resolve(sid)
        if not isinstance(values, list) or not 1 <= len(values) <= self.settings.batch_size:
            raise Invalid('batch')
        replies = []
        for value in values:
            replies.append(self.invoke(sid, value))
        return {'replies': replies}

    def history(self, sid, after=0, limit=16):
        _, principal = self.sessions.resolve(sid)
        require_scope(principal, 'read')
        return self.journal.page(principal, integer(after), integer(limit, 1, 64))

    def close_session(self, sid):
        return self.sessions.close(sid)

    def shutdown(self):
        self.closed = True
        self.sessions.rows.clear()
