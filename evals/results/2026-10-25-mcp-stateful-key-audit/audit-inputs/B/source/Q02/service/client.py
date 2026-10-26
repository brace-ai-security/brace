from urllib.parse import quote

class Client:
    def __init__(self, provider):
        self.provider = provider

    def wire_locator(self, reference):
        return quote(reference.locator, safe='/')

    def read(self, tenant, reference):
        return self.provider.get(tenant, self.wire_locator(reference))

    def head(self, tenant, reference):
        return self.provider.head(tenant, self.wire_locator(reference))

    def list_project(self, tenant, project, cursor, size):
        prefix = quote('/' + project + '/', safe='/')
        return self.provider.list_prefix(tenant, prefix, cursor, size)
