from collections import OrderedDict
from dataclasses import dataclass
from secrets import token_urlsafe
from .errors import Refused, Conflict

@dataclass(frozen=True)
class Session:
    id: str
    token: str
    subject: str
    tenant: str
    credential_id: str
    expires: float

class Sessions:
    def __init__(self, credentials, settings, clock):
        self.credentials = credentials
        self.settings = settings
        self.clock = clock
        self.rows = OrderedDict()

    def prune(self):
        now = self.clock.now()
        for sid, session in list(self.rows.items()):
            if session.expires <= now:
                del self.rows[sid]

    def open(self, token):
        principal = self.credentials.authenticate(token)
        self.prune()
        if len(self.rows) >= self.settings.session_capacity:
            raise Conflict('session capacity')
        sid = token_urlsafe(24)
        session = Session(sid, token, principal.subject, principal.tenant,
                          principal.credential_id, self.clock.now() + self.settings.session_ttl)
        self.rows[sid] = session
        return {'session': sid, 'expires_in': self.settings.session_ttl}

    def resolve(self, sid):
        self.prune()
        if not isinstance(sid, str):
            raise Refused('session')
        session = self.rows.get(sid)
        if session is None:
            raise Refused('session')
        principal = self.credentials.authenticate(session.token)
        if (principal.subject, principal.tenant, principal.credential_id) != (
                session.subject, session.tenant, session.credential_id):
            raise Refused('session identity')
        return session, principal

    def close(self, sid):
        session, _ = self.resolve(sid)
        del self.rows[session.id]
        return {'closed': True}

    def count(self):
        self.prune()
        return len(self.rows)
