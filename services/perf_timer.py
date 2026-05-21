import os
import time
import logging
from functools import wraps

ENABLE_PERF = os.environ.get('KILO_PERF_TIMING', '').lower() in ('1', 'true')


def perf_timer(label: str):
    def decorator(fn):
        if not ENABLE_PERF:
            return fn

        @wraps(fn)
        def wrapper(*args, **kwargs):
            t0 = time.perf_counter()
            result = fn(*args, **kwargs)
            elapsed = time.perf_counter() - t0
            logging.getLogger('perf').info(f"[PERF] {label}: {elapsed:.3f}s")
            return result
        return wrapper
    return decorator
