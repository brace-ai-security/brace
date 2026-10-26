from .adapters import prepare
from .contracts import document_arguments
from .dispatch import dispatch
from .policy import authorize, require_tenant

class Routes:
    def __init__(self, store, audit):
        self.store = store
        self.audit = audit

    def document_read(self, request):
        tenant, key = document_arguments(request.arguments)
        authorize(request.identity, "read")
        require_tenant(request.identity, tenant)
        result = self.store.read(tenant, key)
        self.audit.record(request, "document.read", 1)
        return result

    def account_export(self, request):
        authorize(request.identity, "export", owner_only=True)
        result = self.store.export(request.identity.tenant)
        self.audit.record(request, "account.export", len(result))
        return result

    def capability_run(self, request):
        job = prepare(request)
        result = dispatch(job, self.store)
        self.audit.record(request, "capability.run", 1)
        return result

    def document_purge(self, request):
        tenant, key = document_arguments(request.arguments)
        authorize(request.identity, "purge", owner_only=True)
        require_tenant(request.identity, tenant)
        return self.store.purge(tenant, key)
