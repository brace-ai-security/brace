from dataclasses import dataclass
from urllib.parse import unquote
from posixpath import normpath
from .validation import name, text
from .errors import Invalid

@dataclass(frozen=True)
class Reference:
    project: str
    locator: str

class References:
    def parse(self, project, encoded):
        project = name(project)
        value = unquote(text(encoded, 512), encoding='utf-8', errors='strict')
        if not value or value.startswith('/') or '\x00' in value:
            raise Invalid('relative resource')
        if any(part in ('', '.', '..') for part in value.split('/')):
            raise Invalid('resource segment')
        locator = normpath('/' + project + '/' + value)
        if not locator.startswith('/' + project + '/'):
            raise Invalid('resource project')
        return Reference(project, locator)
