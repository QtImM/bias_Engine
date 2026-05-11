"""
Trading calendar utilities.

Provides trading day checks and date alignment for CN, HK, and US markets.
Phase 1: uses simple weekday-based approximation with known holiday lists.
"""
from __future__ import annotations

import datetime as dt
from typing import Optional

import pandas as pd


# Major holidays (simplified - production should use exchange_calendars package)
# Format: set of (month, day) tuples
_CN_HOLIDAYS_2024_2026 = {
    # 2024
    (1, 1), (2, 10), (2, 11), (2, 12), (2, 13), (2, 14), (2, 15), (2, 16), (2, 17),
    (4, 4), (4, 5), (4, 6), (5, 1), (5, 2), (5, 3), (5, 4), (5, 5),
    (6, 8), (6, 9), (6, 10), (9, 15), (9, 16), (9, 17),
    (10, 1), (10, 2), (10, 3), (10, 4), (10, 5), (10, 6), (10, 7),
    # 2025
    (1, 1), (1, 28), (1, 29), (1, 30), (1, 31), (2, 1), (2, 2), (2, 3), (2, 4),
    (4, 4), (4, 5), (4, 6), (5, 1), (5, 2), (5, 3), (5, 4), (5, 5),
    (6, 1), (6, 2), (10, 1), (10, 2), (10, 3), (10, 4), (10, 5), (10, 6), (10, 7),
    # 2026
    (1, 1), (1, 2), (2, 17), (2, 18), (2, 19), (2, 20), (2, 21), (2, 22), (2, 23),
    (4, 5), (4, 6), (4, 7), (5, 1), (5, 2), (5, 3), (5, 4), (5, 5),
    (6, 19), (6, 20), (10, 1), (10, 2), (10, 3), (10, 4), (10, 5), (10, 6), (10, 7),
}

_HK_HOLIDAYS_2024_2026 = {
    # Simplified - major HK holidays
    (1, 1), (2, 10), (2, 12), (2, 13), (3, 29), (3, 30), (4, 1), (4, 4),
    (5, 1), (5, 15), (6, 10), (7, 1), (9, 18), (10, 1), (10, 11), (12, 25), (12, 26),
    # 2025
    (1, 1), (1, 29), (1, 31), (4, 4), (4, 18), (4, 21), (5, 1), (5, 5),
    (6, 2), (7, 1), (10, 1), (10, 29), (12, 25), (12, 26),
    # 2026
    (1, 1), (1, 2), (2, 17), (2, 19), (4, 3), (4, 6), (5, 1), (5, 24),
    (7, 1), (10, 1), (10, 26), (12, 25),
}

_US_HOLIDAYS_2024_2026 = {
    # Simplified - major US holidays
    (1, 1), (1, 15), (2, 19), (3, 29), (5, 27), (6, 19), (7, 4), (9, 2),
    (11, 28), (12, 25),
    # 2025
    (1, 1), (1, 20), (2, 17), (4, 18), (5, 26), (6, 19), (7, 4), (9, 1),
    (11, 27), (12, 25),
    # 2026
    (1, 1), (1, 19), (2, 16), (4, 3), (5, 25), (6, 19), (7, 3), (9, 7),
    (11, 26), (12, 25),
}


_MARKET_HOLIDAYS: dict[str, set[tuple[int, int]]] = {
    "CN": _CN_HOLIDAYS_2024_2026,
    "HK": _HK_HOLIDAYS_2024_2026,
    "US": _US_HOLIDAYS_2024_2026,
}


def is_trading_day(date: dt.date, market: str) -> bool:
    """Check if a date is a trading day for the given market."""
    if date.weekday() >= 5:  # Saturday or Sunday
        return False
    holidays = _MARKET_HOLIDAYS.get(market, set())
    return (date.month, date.day) not in holidays


def get_trading_days(
    start: dt.date,
    end: dt.date,
    market: str,
) -> list[dt.date]:
    """Get all trading days between start and end (inclusive) for a market."""
    dates = pd.bdate_range(start=start, end=end).date.tolist()
    return [d for d in dates if is_trading_day(d, market)]


def offset_trading_days(
    date: dt.date,
    n: int,
    market: str,
) -> dt.date:
    """Offset by n trading days from date. Positive = forward, negative = backward."""
    step = 1 if n > 0 else -1
    remaining = abs(n)
    current = date
    while remaining > 0:
        current += dt.timedelta(days=step)
        if is_trading_day(current, market):
            remaining -= 1
    return current


def get_latest_trading_day(date: dt.date, market: str) -> dt.date:
    """Get the most recent trading day on or before the given date."""
    current = date
    for _ in range(10):  # max 10 days back
        if is_trading_day(current, market):
            return current
        current -= dt.timedelta(days=1)
    return date  # fallback
