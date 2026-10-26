from copy import deepcopy
from .errors import Invalid

class Discovery:
    def __init__(self, registry, catalog):
        self.registry = registry
        self.catalog = deepcopy(catalog)
        names = [item['name'] for item in self.catalog]
        if len(set(names)) != len(names) or set(names) != set(registry.handlers):
            raise Invalid('catalog registration')

    def list_tools(self):
        return {'tools': deepcopy(self.catalog)}

    def describe(self, tool):
        for item in self.catalog:
            if item['name'] == tool:
                return deepcopy(item)
        from .errors import Missing
        raise Missing('tool description')
