from .identity import require_scope
from .validation import name, integer
from .errors import Invalid

class Routes:
    def __init__(self, membership, dataset, jobs, worker, settings):
        self.membership = membership
        self.dataset = dataset
        self.jobs = jobs
        self.worker = worker
        self.settings = settings

    def start(self, request):
        require_scope(request.principal, 'run')
        project = name(request.arguments['project'])
        lease = self.membership.authorize(request.principal, project)
        return self.jobs.create(request.principal, project, lease)

    def resume(self, request):
        require_scope(request.principal, 'run')
        jid = name(request.arguments['job'])
        job = self.jobs.owned(request.principal, jid)
        return self.worker.read(request.principal, job)

    def status(self, request):
        return self.jobs.describe(request.principal, name(request.arguments['job']))

    def cancel(self, request):
        return self.jobs.cancel(request.principal, name(request.arguments['job']))

    def preview(self, request):
        project = name(request.arguments['project'])
        lease = self.membership.authorize(request.principal, project)
        rows, _ = self.dataset.select(lease.tenant, lease.project, 0, self.settings.page_size)
        return {'items': rows}

    def membership_set(self, request):
        require_scope(request.principal, 'admin')
        args = request.arguments
        enabled = args['enabled']
        if type(enabled) is not bool:
            raise Invalid('enabled')
        self.membership.change(request.principal.tenant, name(args['project']), name(args['subject']), enabled)
        return {'updated': True}
