from .settings import Settings
from .identity import Credentials
from .audit import Audit
from .registry import Registry
from .plans import Plans
from .reviews import Reviews
from .catalog import Catalog
from .delivery import Delivery
from .executor import Executor
from .routes import Routes

def build(settings=None):
    settings = (settings or Settings()).validate()
    plans, reviews, catalog, delivery = Plans(), Reviews(), Catalog(), Delivery()
    executor = Executor(catalog, reviews, delivery)
    routes = Routes(plans, reviews, catalog, executor)
    registry = Registry(Credentials(), Audit(settings.audit_capacity))
    registry.register('plan.create', routes.create)
    registry.register('plan.update', routes.update)
    registry.register('plan.inspect', routes.inspect)
    registry.register('review.record', routes.review)
    registry.register('plan.execute', routes.execute)
    registry.seal()
    return registry
