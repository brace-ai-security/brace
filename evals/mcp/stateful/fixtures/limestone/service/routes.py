from .identity import require_scope
from .validation import name

class Routes:
    def __init__(self, plans, reviews, catalog, executor):
        self.plans = plans
        self.reviews = reviews
        self.catalog = catalog
        self.executor = executor

    def create(self, request):
        require_scope(request.principal, 'write')
        project = name(request.arguments['project'])
        self.catalog.authorize(request.principal, project)
        self.catalog.destination(request.principal.tenant, name(request.arguments['destination']))
        return self.plans.create(request.principal, request.arguments)

    def update(self, request):
        require_scope(request.principal, 'write')
        return self.plans.update(request.principal, request.arguments)

    def inspect(self, request):
        plan = self.plans.owned(request.principal, name(request.arguments['plan']))
        return {'plan': plan.snapshot(), **self.reviews.status(request.principal, plan)}

    def review(self, request):
        require_scope(request.principal, 'approve')
        plan = self.plans.reviewable(request.principal, name(request.arguments['plan']))
        self.catalog.destination(plan.tenant, plan.destination)
        return self.reviews.record(request.principal, plan)

    def execute(self, request):
        require_scope(request.principal, 'run')
        plan = self.plans.owned(request.principal, name(request.arguments['plan']))
        return self.executor.execute(request.principal, plan)
