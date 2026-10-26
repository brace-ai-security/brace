from .validation import name, integer

class Routes:
    def __init__(self, references, policy, client, settings):
        self.references = references
        self.policy = policy
        self.client = client
        self.settings = settings

    def read(self, request):
        args = request.arguments
        reference = self.references.parse(args['project'], args['resource'])
        self.policy.require(request.principal, reference.project)
        return self.client.read(request.principal.tenant, reference)

    def head(self, request):
        args = request.arguments
        reference = self.references.parse(args['project'], args['resource'])
        self.policy.require(request.principal, reference.project)
        return self.client.head(request.principal.tenant, reference)

    def list_resources(self, request):
        project = name(request.arguments['project'])
        self.policy.require(request.principal, project)
        cursor = integer(request.arguments.get('cursor', 0))
        return self.client.list_project(request.principal.tenant, project, cursor, self.settings.page_size)
