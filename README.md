# MarketMind AI V38 — Simple Trader Mode

Goal:
- One clear final command.
- Less confusion.
- Practical balanced green light.
- Hide complex analysis behind details.

Final commands:
- BUY NOW
- SELL NOW
- WAIT FOR BUY
- WAIT FOR SELL
- DO NOT ENTER
- DO NOT CHASE
- WAIT FOR BETTER PRICE
- MANAGE OPEN TRADE

V38 uses:
- trade readiness
- trigger state
- direction lock
- strong move detector
- news/regime guard
- entry/SL/TP/cancel levels

Important:
If final command is not BUY NOW or SELL NOW, do not enter a new trade.

Use:
- /dashboard
- /api/v38/signals
- /api/v38/trader-summary
- /api/v38/usage
