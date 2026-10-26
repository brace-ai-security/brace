import re
from .errors import InvalidRequest
from .limits import text, bounded_list

IDENTIFIER = re.compile(r"(?:public|private)/[a-z][a-z0-9_-]{0,39}\Z")

def record_name(value):
    name = text(value, "name")
    if IDENTIFIER.fullmatch(name) is None:
        raise InvalidRequest("invalid record name")
    return name

def one(arguments):
    return record_name(arguments.get("name"))

def many(arguments):
    return tuple(record_name(value) for value in bounded_list(arguments.get("names")))
