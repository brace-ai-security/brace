import re
from .errors import Invalid

NAME = re.compile(r'[a-z][a-z0-9_-]{0,47}\Z')

def name(value):
    if not isinstance(value, str) or not NAME.fullmatch(value):
        raise Invalid('name')
    return value

def text(value, maximum=4096):
    if not isinstance(value, str) or len(value.encode('utf-8')) > maximum:
        raise Invalid('text')
    return value

def integer(value, low=0, high=1000000):
    if type(value) is not int or not low <= value <= high:
        raise Invalid('integer')
    return value

def object_value(value, depth=0):
    if depth > 8:
        raise Invalid('nesting')
    if value is None or type(value) in (bool, int):
        return value
    if isinstance(value, str):
        return text(value, 16384)
    if isinstance(value, list) and len(value) <= 64:
        return [object_value(v, depth + 1) for v in value]
    if isinstance(value, dict) and len(value) <= 64:
        if any(not isinstance(k, str) or len(k) > 64 for k in value):
            raise Invalid('object key')
        return {k: object_value(v, depth + 1) for k, v in value.items()}
    raise Invalid('object')
