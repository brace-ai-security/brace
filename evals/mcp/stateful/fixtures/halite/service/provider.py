from copy import deepcopy
from .errors import Refused, Temporary, Missing

class Provider:
    def __init__(self):
        self.generation = 1
        self.credentials = {'link-mira': ('north', 'mira-inbox'),
                            'link-noah': ('north', 'noah-inbox'),
                            'link-ops': ('north', 'operations-inbox'),
                            'link-sora': ('south', 'sora-inbox'),
                            'maintenance': ('north', 'operations-inbox')}
        self.messages = {
            ('north', 'mira-inbox'): [{'id': 'note-one', 'body': 'Mira working note'}],
            ('north', 'noah-inbox'): [{'id': 'note-one', 'body': 'Noah working note'}],
            ('north', 'operations-inbox'): [{'id': 'plan-one', 'body': 'Operations private release'}],
            ('south', 'sora-inbox'): [{'id': 'note-one', 'body': 'Sora working note'}],
        }

    def rotate(self):
        self.generation += 1
        return self.generation

    def page(self, generation, context, cursor, size):
        if generation != self.generation:
            raise Temporary('connection generation')
        expected = self.credentials.get(context.credential)
        if expected != (context.tenant, context.account):
            raise Refused('provider credential')
        rows = self.messages.get(expected)
        if rows is None:
            raise Missing('account')
        return {'items': deepcopy(rows[cursor:cursor + size]),
                'next': cursor + size if cursor + size < len(rows) else None}
