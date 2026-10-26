from .settings import Settings
from .identity import Credentials
from .audit import Audit
from .registry import Registry
from .access import Membership, Decisions
from .documents import Documents
from .execution import Execution
from .routes import Routes

def build(settings=None):
    settings = (settings or Settings()).validate()
    membership = Membership()
    decisions = Decisions(membership, settings.result_capacity)
    routes = Routes(decisions, Execution(Documents()), membership, settings)
    registry = Registry(Credentials(), Audit(settings.audit_capacity))
    registry.register('document.read', routes.read)
    registry.register('document.update', routes.update)
    registry.register('document.list', routes.list_documents)
    registry.register('membership.set', routes.membership_set)
    registry.seal()
    return registry
