import secrets
from dataclasses import dataclass
class Forbidden(Exception): pass
@dataclass
class Job:
    tenant: str
    result: object
    cancelled: bool = False
class Store:
    def __init__(self): self.jobs = {}
    def create(self, tenant, result):
        handle = secrets.token_urlsafe(24)
        self.jobs[handle] = Job(tenant, result)
        return {'handle': handle}
    def owned(self, tenant, handle):
        job = self.jobs[handle]
        if job.tenant != tenant: raise Forbidden('tenant')
        return job
