from dataclasses import dataclass, asdict, replace
from .errors import Missing, Conflict

@dataclass(frozen=True)
class Document:
    key: str
    title: str
    body: str
    revision: int

class Documents:
    def __init__(self):
        self.rows = {
            ('north', 'general', 'guide'): Document('guide', 'Guide', 'North working draft', 1),
            ('north', 'vault', 'budget'): Document('budget', 'Budget', 'North planning figures', 1),
            ('south', 'general', 'guide'): Document('guide', 'Guide', 'South working draft', 1),
        }

    def get(self, tenant, project, key):
        row = self.rows.get((tenant, project, key))
        if row is None:
            raise Missing('document')
        return asdict(row)

    def page(self, tenant, project, cursor, size):
        keys = sorted(k for t, p, k in self.rows if (t, p) == (tenant, project))
        selected = keys[cursor:cursor + size]
        return {'items': [self.get(tenant, project, key) for key in selected],
                'next': cursor + len(selected) if cursor + len(selected) < len(keys) else None}

    def update(self, tenant, project, key, title, revision):
        locator = (tenant, project, key)
        row = self.rows.get(locator)
        if row is None:
            raise Missing('document')
        if row.revision != revision:
            raise Conflict('revision')
        self.rows[locator] = replace(row, title=title, revision=row.revision + 1)
        return asdict(self.rows[locator])
