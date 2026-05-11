"""
Data normalization: converts raw provider data into a unified OHLCV format.

All bars are stored as:
  symbol, timeframe, ts (UTC), session_date, open, high, low, close, volume, amount, provider, available_at
"""
from __future__ import annotations

import datetime as dt
from typing import Optional

import pandas as pd
import pytz


def normalize_bars(
    df: pd.DataFrame,
    symbol: str,
    provider: str,
    market: str,
    timezone: str,
    timeframe: str = "1d",
) -> pd.DataFrame:
    """
    Normalize raw OHLCV data from any provider into the standard format.

    Expected input columns (flexible mapping):
      - date/index: the date column
      - open, high, low, close: OHLC prices
      - volume: trading volume
      - amount: trading amount (optional, may be NaN)
    """
    out = df.copy()

    # Ensure we have a date column
    if "date" not in out.columns:
        if isinstance(out.index, pd.DatetimeIndex):
            out = out.reset_index()
            # Rename the index column to 'date' if needed
            if out.columns[0] != "date":
                out = out.rename(columns={out.columns[0]: "date"})
        else:
            raise ValueError("Input must have 'date' column or DatetimeIndex")

    # Standardize column names to lowercase
    col_map = {}
    for col in out.columns:
        cl = col.lower().strip()
        if cl in ("date", "datetime", "trade_date", "日期"):
            col_map[col] = "date"
        elif cl in ("open", "开盘", "开盘价"):
            col_map[col] = "open"
        elif cl in ("high", "最高", "最高价"):
            col_map[col] = "high"
        elif cl in ("low", "最低", "最低价"):
            col_map[col] = "low"
        elif cl in ("close", "收盘", "收盘价"):
            col_map[col] = "close"
        elif cl in ("volume", "vol", "成交量"):
            col_map[col] = "volume"
        elif cl in ("amount", "turnover", "成交额"):
            col_map[col] = "amount"

    out = out.rename(columns=col_map)

    # Validate required columns
    required = ["date", "open", "high", "low", "close"]
    missing = [c for c in required if c not in out.columns]
    if missing:
        raise ValueError(f"Missing required columns after mapping: {missing}")

    # Parse dates
    out["date"] = pd.to_datetime(out["date"])

    # Ensure timezone-naive for now, then localize
    if out["date"].dt.tz is not None:
        out["date"] = out["date"].dt.tz_localize(None)

    # Add metadata columns
    out["symbol"] = symbol
    out["timeframe"] = timeframe
    out["provider"] = provider

    # session_date is the trading date
    out["session_date"] = out["date"].dt.date

    # ts is the timestamp in UTC (for daily bars, use market close time)
    market_close_times = {
        "CN": dt.time(15, 0),   # 15:00 CST
        "HK": dt.time(16, 0),   # 16:00 HKT
        "US": dt.time(16, 0),   # 16:00 EST
    }
    close_time = market_close_times.get(market, dt.time(16, 0))
    out["ts"] = out["date"].apply(
        lambda d: pd.Timestamp.combine(d.date(), close_time)
    )
    # Localize to market timezone, then convert to UTC
    tz = pytz.timezone(timezone)
    out["ts"] = out["ts"].apply(lambda t: tz.localize(t).astimezone(pytz.UTC))

    # available_at: for daily bars, data is available after market close
    # Add 1 hour buffer for data processing
    out["available_at"] = out["ts"] + pd.Timedelta(hours=1)

    # Fill missing volume/amount
    if "volume" not in out.columns:
        out["volume"] = 0.0
    else:
        out["volume"] = pd.to_numeric(out["volume"], errors="coerce").fillna(0.0)

    if "amount" not in out.columns:
        out["amount"] = 0.0
    else:
        out["amount"] = pd.to_numeric(out["amount"], errors="coerce").fillna(0.0)

    # Ensure numeric OHLC
    for col in ["open", "high", "low", "close"]:
        out[col] = pd.to_numeric(out[col], errors="coerce")

    # Drop rows with NaN in OHLC
    out = out.dropna(subset=["open", "high", "low", "close"])

    # Sort by date
    out = out.sort_values("session_date").reset_index(drop=True)

    # Select and order final columns
    final_cols = [
        "symbol", "timeframe", "ts", "session_date",
        "open", "high", "low", "close", "volume", "amount",
        "provider", "available_at",
    ]
    return out[final_cols]
