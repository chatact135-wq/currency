# EdgeFlow FX Pro — Strategy Permission System V1

This is a new professional trading-model system, not V54.

Core permission model:
- A+ Setup = TRADE NOW
- B Setup = SCALP NOW
- C Setup = PLAN ONLY — DO NOT ENTER
- Bad Market = NO TRADE
- Open Position = MANAGE TRADE

Strategy types:
- Pullback Continuation
- Break / Retest
- Liquidity Sweep Reversal
- Range Rejection
- Fast Scalp Momentum
- No Strategy

Main links:
- /dashboard
- /api/pro/v1/signals
- /api/pro/v1/pro-panel
- /api/pro/v1/strategy-permission
- /api/pro/v1/plan-lock
- /api/pro/v1/trade/status

Recommended variables:
STRATEGY_MODE=balanced
STRATEGY_SCALP_MIN_REWARD_MOVES=12
STRATEGY_SCALP_MAX_RISK_MOVES=22
STRATEGY_SCALP_MIN_RR=0.9
STRATEGY_TRADE_MIN_RR=1.15
STRATEGY_CONFIRM_BODY_MOVES=8
