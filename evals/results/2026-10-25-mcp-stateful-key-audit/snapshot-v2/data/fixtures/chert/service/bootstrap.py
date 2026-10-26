from .settings import Settings
from .identity import Credentials
from .audit import Audit
from .registry import Registry
from .membership import Membership
from .dataset import Dataset
from .jobs import Jobs
from .worker import Worker
from .routes import Routes

def build(settings=None):
    settings = (settings or Settings()).validate()
    membership, dataset, jobs = Membership(), Dataset(), Jobs()
    worker = Worker(jobs, dataset, membership, settings.page_size)
    routes = Routes(membership, dataset, jobs, worker, settings)
    registry = Registry(Credentials(), Audit(settings.audit_capacity))
    registry.register('job.start', routes.start)
    registry.register('job.resume', routes.resume)
    registry.register('job.status', routes.status)
    registry.register('job.cancel', routes.cancel)
    registry.register('dataset.preview', routes.preview)
    registry.register('membership.set', routes.membership_set)
    registry.seal()
    return registry
