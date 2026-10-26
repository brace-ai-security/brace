from .identity import require_scope
from .validation import name, text, integer

class Routes:
    def __init__(self, decisions, execution, membership, settings):
        self.decisions = decisions
        self.execution = execution
        self.membership = membership
        self.settings = settings

    def read(self, request):
        project = name(request.arguments['project'])
        key = name(request.arguments['key'])
        permit = self.decisions.authorize(request.principal, 'read', project)
        return self.execution.read(permit, project, key)

    def update(self, request):
        args = request.arguments
        project, key = name(args['project']), name(args['key'])
        title, revision = text(args['title'], 120), integer(args['revision'], 1)
        permit = self.decisions.authorize(request.principal, 'write', project)
        return self.execution.update(permit, project, key, title, revision)

    def list_documents(self, request):
        project = name(request.arguments['project'])
        cursor = integer(request.arguments.get('cursor', 0))
        permit = self.decisions.authorize(request.principal, 'read', project)
        return self.execution.page(permit, project, cursor, self.settings.page_size)

    def membership_set(self, request):
        require_scope(request.principal, 'admin')
        args = request.arguments
        project, subject = name(args['project']), name(args['subject'])
        enabled = args['enabled']
        if type(enabled) is not bool:
            from .errors import Invalid
            raise Invalid('enabled')
        self.membership.set_member(request.principal.tenant, project, subject, enabled)
        return {'updated': True}
