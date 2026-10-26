from copy import deepcopy
from .seed import DOCUMENTS, EXPORT_ROWS
from .errors import NotFound

class Store:
    def __init__(self):
        self.documents = deepcopy(DOCUMENTS)
        self.exports = deepcopy(EXPORT_ROWS)

    def read(self, tenant, key):
        record = self.documents.get((tenant, key))
        if record is None:
            raise NotFound("document")
        return deepcopy(record)

    def export(self, tenant):
        if tenant not in self.exports:
            raise NotFound("tenant")
        return deepcopy(self.exports[tenant])

    def purge(self, tenant, key):
        if (tenant, key) not in self.documents:
            raise NotFound("document")
        del self.documents[(tenant, key)]
        return {"removed": key}
