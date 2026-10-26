class Executor:
    def __init__(self, catalog, reviews, delivery):
        self.catalog = catalog
        self.reviews = reviews
        self.delivery = delivery

    def execute(self, principal, plan):
        self.catalog.authorize(principal, plan.project)
        self.catalog.destination(plan.tenant, plan.destination)
        self.reviews.consume(principal, plan)
        document = self.catalog.read(plan.tenant, plan.project, plan.document)
        payload = document if plan.projection == 'full' else {'title': document['title']}
        return self.delivery.send(plan.tenant, plan.destination, payload)
