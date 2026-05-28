import requests
from app.config import settings
from app.services.cache import get_cache, set_cache, age
from app.services.session_engine import default_news_countdown

QUERIES = {
    "EURUSD": "EURUSD OR EUR/USD OR ECB OR Federal Reserve OR US dollar",
    "GBPUSD": "GBPUSD OR GBP/USD OR Bank of England OR UK inflation OR Federal Reserve",
    "XAUUSD": "gold OR XAUUSD OR Federal Reserve OR inflation OR treasury yields",
    "WTI": "WTI oil OR crude oil OR OPEC OR EIA crude inventories",
}

def score_text(text: str):
    t = text.lower()
    score = 0.0
    hits = []
    bullish = ["cut rates", "rate cut", "dovish", "weak dollar", "safe haven", "supply cut", "inventories fall", "gold rises", "oil rises"]
    bearish = ["hawkish", "rate hike", "strong dollar", "yields rise", "inventories rise", "demand weak", "gold falls", "oil falls"]
    for w in bullish:
        if w in t:
            score += 0.12
            hits.append(w)
    for w in bearish:
        if w in t:
            score -= 0.12
            hits.append(w)
    return score, hits

def news(asset: str):
    key = f"news:{asset}"
    cached = get_cache(key, settings.NEWS_CACHE_SECONDS)
    if cached:
        return {**cached, "cache_age": age(key)}
    countdown = default_news_countdown()
    if not settings.NEWS_API_KEY:
        return {
            "connected": False,
            "bias": "neutral",
            "score": 0.0,
            "source": "NEWS_API_KEY missing",
            "headlines": [],
            "explanation": "Add NEWS_API_KEY in Railway for real headline sentiment.",
            "next_event": countdown,
            "cache_age": None,
        }
    try:
        r = requests.get("https://newsapi.org/v2/everything", params={
            "q": QUERIES.get(asset, QUERIES["EURUSD"]),
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": 6,
            "apiKey": settings.NEWS_API_KEY,
        }, timeout=12)
        data = r.json()
    except Exception as exc:
        return {"connected": False, "bias": "neutral", "score": 0.0, "source": "news error", "headlines": [], "explanation": str(exc), "next_event": countdown, "cache_age": None}
    if data.get("status") != "ok":
        return {"connected": False, "bias": "neutral", "score": 0.0, "source": "news error", "headlines": [], "explanation": data.get("message", "News API error"), "next_event": countdown, "cache_age": None}
    total = 0.0
    hits_all = []
    headlines = []
    for article in data.get("articles", []):
        title = article.get("title") or ""
        desc = article.get("description") or ""
        s, hits = score_text(title + " " + desc)
        total += s
        hits_all += hits
        headlines.append({"title": title[:160], "source": (article.get("source") or {}).get("name", ""), "score": round(s, 3)})
    score = max(-0.35, min(0.35, total))
    bias = "bullish" if score > 0.08 else "bearish" if score < -0.08 else "neutral"
    result = {
        "connected": True,
        "bias": bias,
        "score": round(score, 3),
        "source": "NewsAPI live",
        "headlines": headlines,
        "explanation": "Headline keywords: " + (", ".join(hits_all[:5]) if hits_all else "no strong bias found"),
        "next_event": countdown,
        "cache_age": 0,
    }
    set_cache(key, result)
    return result
