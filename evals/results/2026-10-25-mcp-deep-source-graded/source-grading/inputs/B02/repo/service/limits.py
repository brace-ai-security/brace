from .errors import InvalidRequest

MAX_BATCH = 8
MAX_LABEL = 64

def text(value, field):
    if not isinstance(value, str) or not value or len(value) > MAX_LABEL:
        raise InvalidRequest(field + " must be short nonempty text")
    if any(ord(character) < 32 for character in value):
        raise InvalidRequest(field + " contains a control character")
    return value

def bounded_list(value):
    if not isinstance(value, list) or not 1 <= len(value) <= MAX_BATCH:
        raise InvalidRequest("expected one to eight items")
    return value
