from .settings import Settings
from .identity import Credentials
from .audit import Audit
from .registry import Registry
from .references import References
from .policy import Policy
from .provider import Provider
from .client import Client
from .routes import Routes

def build(settings=None):
    settings = (settings or Settings()).validate()
    routes = Routes(References(), Policy(), Client(Provider()), settings)
    registry = Registry(Credentials(), Audit(settings.audit_capacity))
    registry.register('resource.read', routes.read)
    registry.register('resource.head', routes.head)
    registry.register('resource.list', routes.list_resources)
    registry.seal()
    return registry
