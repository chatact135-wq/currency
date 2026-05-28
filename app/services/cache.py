import time
_cache = {}
def get(key, ttl):
    item = _cache.get(key)
    if not item: return None
    ts, value = item
    if time.time() - ts > ttl:
        _cache.pop(key, None)
        return None
    return value
def set(key, value):
    _cache[key] = (time.time(), value)
def age(key):
    item = _cache.get(key)
    return None if not item else int(time.time() - item[0])
