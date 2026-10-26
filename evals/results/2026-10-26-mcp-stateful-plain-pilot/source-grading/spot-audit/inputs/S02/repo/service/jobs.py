from dataclasses import dataclass, field
from copy import deepcopy
from .errors import Refused, Missing, Conflict

@dataclass
class Job:
    id: str
    subject: str
    tenant: str
    project: str
    lease: object
    cursor: int = 0
    state: str = 'queued'
    attempts: int = 0
    last: list = field(default_factory=list)

class Jobs:
    def __init__(self):
        self.records = {}
        self.sequence = 0

    def create(self, principal, project, lease):
        self.sequence += 1
        jid = 'job-' + str(self.sequence)
        job = Job(jid, principal.subject, principal.tenant, project, lease)
        self.records[jid] = job
        return {'job': jid, 'state': job.state}

    def owned(self, principal, jid):
        job = self.records.get(jid)
        if job is None:
            raise Missing('job')
        if (job.subject, job.tenant) != (principal.subject, principal.tenant):
            raise Refused('job owner')
        return job

    def describe(self, principal, jid):
        job = self.owned(principal, jid)
        return {'job': job.id, 'state': job.state, 'cursor': job.cursor, 'attempts': job.attempts}

    def cancel(self, principal, jid):
        job = self.owned(principal, jid)
        if job.state == 'done':
            raise Conflict('completed')
        job.state = 'cancelled'
        job.last = []
        return self.describe(principal, jid)

    def result(self, job):
        return {'job': job.id, 'items': deepcopy(job.last), 'state': job.state}
