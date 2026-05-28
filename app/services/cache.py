import time
_CACHE={}
def get_cache(key, ttl_seconds):
    item=_CACHE.get(key)
    if not item: return None
    created,value=item
    if time.time()-created>ttl_seconds:
        _CACHE.pop(key,None); return None
    return value
def set_cache(key,value): _CACHE[key]=(time.time(),value)
def cache_age_seconds(key):
    item=_CACHE.get(key)
    return None if not item else int(time.time()-item[0])
