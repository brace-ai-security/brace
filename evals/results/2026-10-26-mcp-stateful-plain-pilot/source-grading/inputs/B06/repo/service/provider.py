from copy import deepcopy
from urllib.parse import unquote
from posixpath import normpath
from .errors import Missing

class Provider:
    def __init__(self):
        self.rows = {
            ('north', '/general/guide'): {'title': 'Guide', 'body': 'General working draft'},
            ('north', '/general/style/notes'): {'title': 'Notes', 'body': 'Editorial style'},
            ('north', '/general/release%20notes'): {'title': 'Release', 'body': 'Literal percent name'},
            ('north', '/vault/budget'): {'title': 'Budget', 'body': 'North private planning'},
            ('south', '/general/guide'): {'title': 'Guide', 'body': 'South working draft'},
        }

    def decode_locator(self, wire_locator):
        return normpath(unquote(wire_locator, encoding='utf-8', errors='strict'))

    def get(self, tenant, wire_locator):
        locator = self.decode_locator(wire_locator)
        value = self.rows.get((tenant, locator))
        if value is None:
            raise Missing('resource')
        return deepcopy(value)

    def head(self, tenant, wire_locator):
        value = self.get(tenant, wire_locator)
        return {'title': value['title'], 'bytes': len(value['body'].encode('utf-8'))}

    def list_prefix(self, tenant, wire_prefix, cursor, size):
        prefix = self.decode_locator(wire_prefix).rstrip('/') + '/'
        keys = sorted(locator for (t, locator) in self.rows if t == tenant and locator.startswith(prefix))
        return {'locators': keys[cursor:cursor + size],
                'next': cursor + size if cursor + size < len(keys) else None}
