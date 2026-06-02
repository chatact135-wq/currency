
def apply_freshness_guard(result):
    if result.get("status")!="live":
        return result
    if result.get("data_fresh") is False:
        reasons=" ".join(result.get("stale_reasons") or [])
        result["final_action"]="NO TRADE - DATA STALE"
        result["entry_permission"]="NO_ENTRY"
        result["warning"]="DATA STALE: Do not trade. "+reasons
        fd=result.get("final_decision") or {}
        if fd:
            fd["final_action"]="NO TRADE - DATA STALE"
            fd["command"]="DO NOT ENTER - DATA NOT LIVE"
            fd["entry_permission"]="NO_ENTRY"
            fd["rule"]="Freshness guard blocks trading when price/cache is stale."
            result["final_decision"]=fd
    return result
