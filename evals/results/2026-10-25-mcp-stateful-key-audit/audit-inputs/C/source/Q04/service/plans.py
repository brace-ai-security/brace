from dataclasses import dataclass, asdict, replace
import hashlib
import json
from copy import deepcopy
from .errors import Missing, Refused, Conflict, Invalid
from .validation import name, text, integer

@dataclass(frozen=True)
class Plan:
    id: str
    tenant: str
    subject: str
    project: str
    document: str
    destination: str
    projection: str
    revision: int = 1

    def snapshot(self):
        return asdict(self)

    def digest(self):
        return hashlib.sha256(json.dumps(self.snapshot(), sort_keys=True).encode()).hexdigest()

class Plans:
    def __init__(self):
        self.rows = {}
        self.sequence = 0

    def create(self, principal, arguments):
        self.sequence += 1
        pid = 'plan-' + str(self.sequence)
        plan = Plan(pid, principal.tenant, principal.subject, name(arguments['project']),
                    name(arguments['document']), name(arguments['destination']),
                    self.projection(arguments.get('projection', 'title')))
        self.rows[pid] = plan
        return plan.snapshot()

    def projection(self, value):
        if value not in ('title', 'full'):
            raise Invalid('projection')
        return value

    def owned(self, principal, pid):
        plan = self.rows.get(pid)
        if plan is None:
            raise Missing('plan')
        if (plan.tenant, plan.subject) != (principal.tenant, principal.subject):
            raise Refused('plan owner')
        return plan

    def reviewable(self, principal, pid):
        plan = self.rows.get(pid)
        if plan is None:
            raise Missing('plan')
        if plan.tenant != principal.tenant:
            raise Refused('plan tenant')
        return plan

    def update(self, principal, arguments):
        plan = self.owned(principal, name(arguments['plan']))
        if plan.revision != integer(arguments['revision'], 1):
            raise Conflict('revision')
        updated = replace(plan, destination=name(arguments.get('destination', plan.destination)),
                          projection=self.projection(arguments.get('projection', plan.projection)),
                          revision=plan.revision + 1)
        self.rows[plan.id] = updated
        return updated.snapshot()
