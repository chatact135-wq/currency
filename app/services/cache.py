import time
from typing import Any
_CACHE: dict[str, tuple[float, Any]] = {}

def get_cache(key: str, ttl: int):
    item = _CACHE.get(key)
    if not item:
        return None
    ts, value = item
    if time.time() - ts > ttl:
        _CACHE.pop(key, None)
        return None
    return value

def set_cache(key: str, value: Any):
    _CACHE[key] = (time.time(), value)

def age(key: str):
    item = _CACHE.get(key)
    if not item:
        return None
    return int(time.time() - item[0])
