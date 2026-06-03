# MarketMind AI V36 — Direction Lock + Anti-Flip Filter

Fixes fast confusing flips:
SELL -> BUY -> SELL -> BUY

Adds:
- Direction lock memory
- Anti-flip filter
- Direction unstable warning
- Flip blocked until direction stays stable
- /api/v36/direction-lock endpoint

Optional Railway variables:
- DIRECTION_LOCK_SECONDS=45
- DIRECTION_FLIP_SCORE_GAP=18
