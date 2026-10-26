from .errors import AccessDenied

def execute(plan, store):
    if plan.grant.operation != "read":
        raise AccessDenied("read grant required")
    return store.fetch_many(plan.names)
