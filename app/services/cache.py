import time
_cache={}
def get(k,ttl):
    v=_cache.get(k)
    if not v: return None
    ts,val=v
    if time.time()-ts>ttl:
        _cache.pop(k,None); return None
    return val
def set(k,v): _cache[k]=(time.time(),v)
def age(k):
    v=_cache.get(k)
    return None if not v else int(time.time()-v[0])
