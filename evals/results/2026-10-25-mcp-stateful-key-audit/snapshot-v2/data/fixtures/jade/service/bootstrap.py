from .settings import Settings
from .identity import Credentials
from .audit import Audit
from .registry import Registry
from .accounts import Accounts
from .receipts import Receipts
from .routes import Routes

def build(settings=None):
    settings = (settings or Settings()).validate()
    routes = Routes(Accounts(), Receipts(settings.result_capacity))
    registry = Registry(Credentials(), Audit(settings.audit_capacity))
    registry.register('transfer.create', routes.create)
    registry.register('account.balance', routes.balance)
    registry.register('receipt.get', routes.receipt)
    registry.seal()
    return registry
