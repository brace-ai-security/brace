from dataclasses import dataclass
from .validation import one, many
from .grants import issue, require

@dataclass(frozen=True)
class Plan:
    grant: object
    names: tuple[str, ...]

def resolve_one(request, catalog):
    supplied = one(request.arguments)
    grant = issue(request.identity, (supplied,))
    target = catalog.canonical(supplied)
    return Plan(grant, (target,))

def resolve_batch(request, catalog):
    supplied = many(request.arguments)
    targets = catalog.canonical_many(supplied)
    grant = issue(request.identity, targets)
    return Plan(grant, targets)

def resolve_metadata(request, catalog):
    target = catalog.canonical(one(request.arguments))
    require(request.identity, target)
    return target
