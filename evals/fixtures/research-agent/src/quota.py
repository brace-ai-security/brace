import time
from collections import defaultdict
from threading import Lock

_runs: dict[tuple[str, str], int] = defaultdict(int)
_lock = Lock()


class RunLimitReached(RuntimeError):
    pass


def charge_user_run(user: str, daily_limit: int) -> None:
    key = (user, time.strftime("%Y-%m-%d"))
    with _lock:
        if _runs[key] >= daily_limit:
            raise RunLimitReached(f"daily limit of {daily_limit} questions reached")
        _runs[key] += 1
