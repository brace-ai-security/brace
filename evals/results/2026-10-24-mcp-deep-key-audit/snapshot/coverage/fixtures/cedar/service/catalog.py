from .seed import ALIASES
from .errors import InvalidRequest

class Catalog:
    def __init__(self):
        self.aliases = dict(ALIASES)

    def canonical(self, name):
        seen = set()
        while name in self.aliases:
            if name in seen:
                raise InvalidRequest("alias cycle")
            seen.add(name)
            name = self.aliases[name]
        return name

    def canonical_many(self, names):
        return tuple(self.canonical(name) for name in names)
