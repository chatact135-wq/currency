import time
_CACHE={}
def get_cache(k,ttl):
    i=_CACHE.get(k)
    if not i: return None
    t,v=i
    if time.time()-t>ttl:
        _CACHE.pop(k,None); return None
    return v
def set_cache(k,v): _CACHE[k]=(time.time(),v)
def age(k):
    i=_CACHE.get(k)
    return None if not i else int(time.time()-i[0])
