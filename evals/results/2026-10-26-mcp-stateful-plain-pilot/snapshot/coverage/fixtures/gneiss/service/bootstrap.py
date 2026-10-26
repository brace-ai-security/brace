from .settings import Settings
from .identity import Credentials
from .audit import Audit
from .registry import Registry
from .context import Context, Links
from .provider import Provider
from .transport import Transport
from .retry import Retry
from .routes import Routes

def build(settings=None):
    settings = (settings or Settings()).validate()
    provider = Provider()
    maintenance = Context('north', 'operator', 'operations-inbox', 'maintenance')
    transport = Transport(provider, maintenance, settings.page_size)
    routes = Routes(Links(), provider, Retry(transport, settings.retry_attempts))
    registry = Registry(Credentials(), Audit(settings.audit_capacity))
    registry.register('mail.list', routes.list_messages)
    registry.register('mail.search', routes.search)
    registry.register('connection.rotate', routes.rotate)
    registry.register('connection.status', routes.connection)
    registry.seal()
    return registry
