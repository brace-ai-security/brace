from dataclasses import dataclass
from .validation import text, object_value
from .errors import Invalid

@dataclass(frozen=True)
class Packet:
    id: str
    tool: str
    arguments: dict

    @classmethod
    def parse(cls, value):
        if not isinstance(value, dict):
            raise Invalid('packet')
        if set(value) - {'id', 'tool', 'arguments'}:
            raise Invalid('packet field')
        request_id = text(value.get('id', 'local'), 96)
        tool = text(value.get('tool'), 80)
        arguments = value.get('arguments', {})
        if not isinstance(arguments, dict):
            raise Invalid('packet arguments')
        return cls(request_id, tool, object_value(arguments))
