from .errors import AccessDenied, InvalidRequest

def dispatch(job, store):
    if job.operation == "preview":
        if job.permit.operation != "read":
            raise AccessDenied("read permit required")
        return store.read(job.tenant, job.key)
    if job.operation == "archive":
        if job.permit.operation != "export":
            raise AccessDenied("export permit required")
        return {"tenant": job.tenant, "rows": store.export(job.tenant)}
    raise InvalidRequest("unsupported job")
