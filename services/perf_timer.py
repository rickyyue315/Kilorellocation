import os
import time
import logging
import threading
from functools import wraps
from typing import Dict, List

ENABLE_PERF = os.environ.get('KILO_PERF_TIMING', '').lower() in ('1', 'true')

_lock = threading.Lock()
_records: List[Dict] = []


def get_perf_records() -> List[Dict]:
    with _lock:
        return list(_records)


def clear_perf_records():
    with _lock:
        _records.clear()


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
            with _lock:
                _records.append({
                    'label': label,
                    'elapsed': elapsed,
                    'fn': fn.__qualname__,
                })
            return result
        return wrapper
    return decorator
