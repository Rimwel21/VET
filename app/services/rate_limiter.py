from collections import defaultdict, deque
from time import time


_attempts = defaultdict(deque)
_locks = {}


def is_limited(key, *, limit=5, window_seconds=300, lock_seconds=900):
    now = time()
    locked_until = _locks.get(key, 0)
    if locked_until > now:
        return True

    if locked_until:
        _locks.pop(key, None)

    bucket = _attempts[key]
    while bucket and now - bucket[0] > window_seconds:
        bucket.popleft()

    if len(bucket) >= limit:
        _locks[key] = now + lock_seconds
        return True

    return False


def record_failure(key):
    _attempts[key].append(time())


def clear_attempts(key):
    _attempts.pop(key, None)
    _locks.pop(key, None)


def reset_all():
    _attempts.clear()
    _locks.clear()
