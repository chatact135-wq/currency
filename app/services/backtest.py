import json
from app.config import settings
from app.models import BacktestTrade
from app.services.market import stored_candles, normalize
from app.services.indicators import build
from app.services.core import detect
def simulate(c,i,direction,atr):
    entry=c[i]["close"]; fut=c[i+1:i+1+settings.BACKTEST_LOOKAHEAD_CANDLES]
    if not fut: return None
    min_move=atr*settings.BACKTEST_MIN_MOVE_ATR
    if direction=="BUY":
        fav=max(x["high"] for x in fut)-entry; adv=entry-min(x["low"] for x in fut)
        outcome="WIN" if fav>=min_move and fav>=adv else "LOSS" if adv>=min_move else "UNKNOWN"; exitp=entry+fav if outcome=="WIN" else entry-adv if outcome=="LOSS" else fut[-1]["close"]; r=(exitp-entry)/min_move
    else:
        fav=entry-min(x["low"] for x in fut); adv=max(x["high"] for x in fut)-entry
        outcome="WIN" if fav>=min_move and fav>=adv else "LOSS" if adv>=min_move else "UNKNOWN"; exitp=entry-fav if outcome=="WIN" else entry+adv if outcome=="LOSS" else fut[-1]["close"]; r=(entry-exitp)/min_move
    return {"entry":entry,"exit":exitp,"outcome":outcome,"r":round(r,2),"fav":fav,"adv":adv}
def run_backtest(db,asset):
    sym=normalize(asset); c=stored_candles(db,sym,settings.HISTORY_CANDLE_LIMIT)
    if len(c)<80: return {"asset":sym,"error":"Not enough candles. Run download-history first.","candles":len(c)}
    made=skipped=0
    for i in range(60,len(c)-settings.BACKTEST_LOOKAHEAD_CANDLES-1):
        window=c[:i+1]; ind=build(window); det=detect(window,ind); m,e=det["master"],det["execution"]
        direction=m["bias"] if m["bias"]!="NEUTRAL" else e["bias"]
        if direction=="NEUTRAL": skipped+=1; continue
        sim=simulate(c,i,direction,ind["atr"])
        if not sim: skipped+=1; continue
        if db.query(BacktestTrade).filter(BacktestTrade.asset==sym,BacktestTrade.candle_time==str(c[i]["datetime"]),BacktestTrade.direction==direction).first(): continue
        active=list({a["strategy"] for a in det["alerts"] if a["direction"] in [direction,"NEUTRAL"]})
        feats={"rsi":ind["rsi"],"atr":ind["atr"],"momentum":ind["momentum"],"pressure":ind["pressure"],"master_score":m["net"],"execution_score":e["net"],"direction":direction}
        db.add(BacktestTrade(asset=sym,candle_time=str(c[i]["datetime"]),direction=direction,entry_price=sim["entry"],exit_price=sim["exit"],outcome=sim["outcome"],r_multiple=sim["r"],max_favorable=sim["fav"],max_adverse=sim["adv"],features_json=json.dumps(feats),active_strategies=json.dumps(active)))
        made+=1
    db.commit(); return {"asset":sym,"candles":len(c),"created_backtest_trades":made,"skipped":skipped}
