import time
_cache={}
def get(k,ttl):
    x=_cache.get(k)
    if not x: return None
    ts,v=x
    if time.time()-ts>ttl:
        _cache.pop(k,None); return None
    return v
def set(k,v): _cache[k]=(time.time(),v)
def age(k):
    x=_cache.get(k)
    return None if not x else int(time.time()-x[0])
