from dataclasses import dataclass
from copy import deepcopy
from .errors import Refused, Conflict

@dataclass
class Decision:
    tenant: str
    subject: str
    plan: str
    digest: str
    snapshot: dict
    reviewer: str
    consumed: bool = False

class Reviews:
    def __init__(self):
        self.decisions = {}

    def record(self, reviewer, plan):
        self.decisions[(plan.tenant, plan.id)] = Decision(plan.tenant, plan.subject,
            plan.id, plan.digest(), plan.snapshot(), reviewer.subject)
        return {'plan': plan.id, 'revision': plan.revision, 'reviewer': reviewer.subject}

    def consume(self, principal, plan):
        decision = self.decisions.get((principal.tenant, plan.id))
        if decision is None or decision.subject != principal.subject:
            raise Refused('review')
        if decision.consumed:
            raise Conflict('review consumed')
        decision.consumed = True
        return deepcopy(decision.snapshot)

    def status(self, principal, plan):
        decision = self.decisions.get((principal.tenant, plan.id))
        return {'reviewed': decision is not None, 'consumed': decision.consumed if decision else False}
