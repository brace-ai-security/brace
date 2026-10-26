from .errors import Refused

class Execution:
    def __init__(self, documents):
        self.documents = documents

    def check(self, permit, project, action):
        if permit.project != project or permit.action != action:
            raise Refused('permit target')

    def read(self, permit, project, key):
        self.check(permit, project, 'read')
        return self.documents.get(permit.tenant, project, key)

    def update(self, permit, project, key, title, revision):
        self.check(permit, project, 'write')
        return self.documents.update(permit.tenant, project, key, title, revision)

    def page(self, permit, project, cursor, size):
        self.check(permit, project, 'read')
        return self.documents.page(permit.tenant, project, cursor, size)
