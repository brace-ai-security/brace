"""Operator halt flag, checked before every model call."""
import os

import redis

_redis = redis.Redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379/0"))
HALT_KEY = "agent:support-agent:halt"


def halted() -> bool:
    try:
        return _redis.get(HALT_KEY) == b"1"
    except redis.RedisError:
        # If we cannot read the flag, assume we should stop.
        return True
