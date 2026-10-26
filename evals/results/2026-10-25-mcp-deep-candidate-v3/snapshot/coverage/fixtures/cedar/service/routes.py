from .plans import resolve_one, resolve_batch, resolve_metadata
from .dispatch import execute

class Routes:
    def __init__(self, store, catalog, audit):
        self.store = store
        self.catalog = catalog
        self.audit = audit

    def record_get(self, request):
        plan = resolve_one(request, self.catalog)
        result = execute(plan, self.store)
        self.audit.record(request, "record.get", len(result))
        return result[0]

    def record_batch(self, request):
        plan = resolve_batch(request, self.catalog)
        result = execute(plan, self.store)
        self.audit.record(request, "record.batch", len(result))
        return result

    def record_metadata(self, request):
        target = resolve_metadata(request, self.catalog)
        result = self.store.metadata(target)
        self.audit.record(request, "record.metadata", 1)
        return result
