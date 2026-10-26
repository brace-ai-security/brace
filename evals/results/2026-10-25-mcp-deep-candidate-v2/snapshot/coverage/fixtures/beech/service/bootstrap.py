from .audit import Audit
from .routes import Routes
from .settings import DEFAULTS, validate
from .storage import Store
from .transport import Registry

def build(settings=DEFAULTS):
    validate(settings)
    registry = Registry()
    routes = Routes(Store(), Audit(settings.audit_capacity))
    registry.register("document.read", routes.document_read)
    registry.register("account.export", routes.account_export)
    registry.register("capability.run", routes.capability_run)
    registry.register("document.purge", routes.document_purge)
    return registry
