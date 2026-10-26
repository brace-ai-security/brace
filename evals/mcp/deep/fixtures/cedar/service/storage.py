from copy import deepcopy
from .seed import RECORDS
from .errors import NotFound

class Store:
    def __init__(self):
        self.records = deepcopy(RECORDS)

    def fetch(self, key):
        if key not in self.records:
            raise NotFound("record")
        return deepcopy(self.records[key])

    def fetch_many(self, keys):
        return [{"key": key, "record": self.fetch(key)} for key in keys]

    def metadata(self, key):
        record = self.fetch(key)
        return {"key": key, "title": record["title"]}
