from __future__ import annotations
from .signal_db_test_b import list_signals, save_review
from .signal_reviewer_test_common import review_due_signals as _review

async def review_due_signals():
    return await _review(list_signals, save_review)
