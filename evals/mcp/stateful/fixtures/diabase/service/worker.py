from .errors import Refused, Conflict

class Worker:
    def __init__(self, jobs, dataset, membership, size):
        self.jobs = jobs
        self.dataset = dataset
        self.membership = membership
        self.size = size

    def read(self, principal, job):
        lease = self.membership.authorize(principal, job.project)
        if (lease.subject, lease.tenant, lease.project, lease.action) != (principal.subject, principal.tenant, job.project, 'read'):
            raise Refused('lease binding')
        if job.state == 'cancelled':
            raise Conflict('cancelled')
        if job.state == 'done':
            return self.jobs.result(job)
        job.attempts += 1
        rows, complete = self.dataset.select(lease.tenant, lease.project, job.cursor, self.size)
        job.cursor += len(rows)
        job.last = rows
        job.state = 'done' if complete else 'paused'
        return self.jobs.result(job)
