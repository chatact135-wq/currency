import time
_cache={}
def get(k,ttl):
    it=_cache.get(k)
    if not it: return None
    ts,val=it
    if time.time()-ts>ttl:
        _cache.pop(k,None); return None
    return val
def set(k,v): _cache[k]=(time.time(),v)
def age(k):
    it=_cache.get(k); return None if not it else int(time.time()-it[0])
