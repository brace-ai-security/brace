from .audit import Audit
from .catalog import Catalog
from .routes import Routes
from .settings import DEFAULTS, validate
from .storage import Store
from .transport import Registry

def build(settings=DEFAULTS):
    validate(settings)
    registry = Registry()
    routes = Routes(Store(), Catalog(), Audit(settings.audit_capacity))
    registry.register("record.get", routes.record_get)
    registry.register("record.batch", routes.record_batch)
    registry.register("record.metadata", routes.record_metadata)
    return registry
