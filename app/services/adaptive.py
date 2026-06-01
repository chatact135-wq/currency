import json
from datetime import datetime, timezone
from app.models import AdaptiveWeight, BacktestTrade
from app.config import settings
from app.services.core import DEFAULTS
def get_weights(db,asset):
    out=dict(DEFAULTS)
    for r in db.query(AdaptiveWeight).filter(AdaptiveWeight.asset==asset).all():
        if r.samples>=settings.MIN_ADAPTIVE_TRADES: out[r.strategy]=float(r.learned_weight)
    return out
def performance_for_active(db,asset,strategies):
    strategies=set(strategies or [])
    if not strategies: return {"status":"no_strategy","samples":0,"probability":None,"expected_edge_r":None}
    matches=[]
    for t in db.query(BacktestTrade).filter(BacktestTrade.asset==asset).all():
        try: active=set(json.loads(t.active_strategies or "[]"))
        except Exception: active=set()
        if strategies.intersection(active): matches.append(t)
    if len(matches)<settings.MIN_ADAPTIVE_TRADES: return {"status":"collecting_backtest_data","samples":len(matches),"probability":None,"expected_edge_r":None}
    wins=sum(1 for x in matches if x.outcome=="WIN"); avg=sum(float(x.r_multiple or 0) for x in matches)/len(matches)
    return {"status":"adaptive_memory","samples":len(matches),"probability":round(wins/len(matches)*100,1),"expected_edge_r":round(avg,2)}
def recalc_weights(db,asset):
    stats={}
    for t in db.query(BacktestTrade).filter(BacktestTrade.asset==asset).all():
        try: active=json.loads(t.active_strategies or "[]")
        except Exception: active=[]
        for s in active:
            stats.setdefault(s,{"samples":0,"wins":0,"losses":0,"r":0.0})
            stats[s]["samples"]+=1
            if t.outcome=="WIN": stats[s]["wins"]+=1
            elif t.outcome=="LOSS": stats[s]["losses"]+=1
            stats[s]["r"]+=float(t.r_multiple or 0)
    res=[]
    for strat,st in stats.items():
        samples=st["samples"]; wr=st["wins"]/samples if samples else 0.5; avg=st["r"]/samples if samples else 0
        base=DEFAULTS.get(strat,10); learned=max(3,min(42,base*(0.65+wr)+max(-5,min(8,avg*4))))
        row=db.query(AdaptiveWeight).filter(AdaptiveWeight.asset==asset,AdaptiveWeight.strategy==strat,AdaptiveWeight.direction=="ANY").first()
        if not row:
            row=AdaptiveWeight(asset=asset,strategy=strat,direction="ANY"); db.add(row)
        row.samples=samples; row.wins=st["wins"]; row.losses=st["losses"]; row.win_rate=wr; row.avg_r=avg; row.learned_weight=learned; row.updated_at=datetime.now(timezone.utc)
        res.append({"strategy":strat,"samples":samples,"win_rate":round(wr*100,1),"avg_r":round(avg,2),"learned_weight":round(learned,2)})
    db.commit(); return res
