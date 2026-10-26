from copy import deepcopy
from .identity import require_scope
from .errors import Refused, Missing

class Catalog:
    def __init__(self):
        self.members = {('north', 'general'): {'mira', 'noah', 'operator'},
                        ('south', 'general'): {'sora'}}
        self.documents = {('north', 'general', 'guide'): {'title': 'North guide', 'body': 'North internal working plan'},
                          ('south', 'general', 'guide'): {'title': 'South guide', 'body': 'South internal working plan'}}
        self.destinations = {('north', 'mira-inbox'), ('north', 'vendor-drop'),
                             ('south', 'sora-inbox'), ('south', 'vendor-drop')}

    def authorize(self, principal, project):
        require_scope(principal, 'read')
        if principal.subject not in self.members.get((principal.tenant, project), set()):
            raise Refused('project')

    def destination(self, tenant, target):
        if (tenant, target) not in self.destinations:
            raise Missing('destination')

    def read(self, tenant, project, document):
        value = self.documents.get((tenant, project, document))
        if value is None:
            raise Missing('document')
        return deepcopy(value)
