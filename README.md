# MarketMind AI V50 — Open Trade Manager

Problem fixed:
If the system says SCALP BUY / ENTER BUY and the user enters, then later the pro panel says DO NOT ENTER,
that DO NOT ENTER should mean "do not open a new trade", not "manage/close existing trade".

V50 adds:
- Open trade state
- Dashboard buttons: I ENTERED BUY / I ENTERED SELL / CLOSE TRADE
- Pro panel changes to MANAGE OPEN BUY / MANAGE OPEN SELL after entry is recorded
- Management messages:
  - protect profit
  - move stop
  - close partial
  - exit if invalidation hit
- API:
  - /api/v50/trade/open
  - /api/v50/trade/close
  - /api/v50/trade/status

Use:
- /dashboard
- /api/v50/signals
- /api/v50/pro-panel
