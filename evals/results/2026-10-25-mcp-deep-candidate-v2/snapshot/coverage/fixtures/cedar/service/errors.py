class AccessDenied(Exception):
    """The caller lacks permission for this operation."""

class InvalidRequest(Exception):
    """A transport argument violates the documented schema."""

class NotFound(Exception):
    """The requested resource does not exist."""
