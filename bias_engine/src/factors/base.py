"""
Factor base classes and context.

Every factor must implement the Factor protocol:
  - spec: FactorSpec describing the factor
  - compute(ctx) -> pd.DataFrame with standardized columns

FactorContext provides data loading and utility methods to factor implementations.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Any, Optional, Protocol

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class FactorSpec:
    """Immutable specification of a factor."""
    name: str
    version: str
    family: str           # trend, mean_reversion, volatility, volume, cross_market, macro
    description: str
    inputs: list[str]     # e.g. ["bars.close"], ["bars.close", "bars.volume"]
    horizons: list[str]   # e.g. ["D1", "W1"]
    lookback: int         # minimum bars needed
    release_lag: str = "0D"  # data availability lag
    params: dict[str, Any] = field(default_factory=dict)


class FactorContext:
    """
    Context object passed to factor.compute().

    Provides:
    - Symbol list
    - Date range
    - Bar loading (with caching)
    - Utility methods for common calculations
    """

    def __init__(
        self,
        symbols: list[str],
        start: dt.date,
        end: dt.date,
        bars: pd.DataFrame,
        prediction_time: pd.Timestamp | None = None,
    ):
        self.symbols = symbols
        self.start = start
        self.end = end
        self.prediction_time = prediction_time
        self._bars = bars.copy()

    def load_bars(
        self,
        symbols: list[str] | None = None,
        timeframe: str = "1d",
        start: Optional[dt.date] = None,
        end: Optional[dt.date] = None,
        fields: Optional[list[str]] = None,
    ) -> pd.DataFrame:
        """
        Load bars filtered by symbols, date range, and columns.

        Returns DataFrame with at least: symbol, ts, session_date, and requested fields.
        """
        df = self._bars.copy()
        if symbols is not None:
            df = df[df["symbol"].isin(symbols)]
        if timeframe:
            df = df[df["timeframe"] == timeframe]
        if start is not None:
            df = df[df["session_date"] >= start]
        if end is not None:
            df = df[df["session_date"] <= end]

        # Point-in-time guard: prevent future data leakage
        if self.prediction_time is not None and "available_at" in df.columns:
            available_at = pd.to_datetime(df["available_at"])
            df = df[available_at <= self.prediction_time]

        if fields is not None:
            base_cols = ["symbol", "ts", "session_date", "timeframe", "available_at"]
            keep_cols = [c for c in base_cols if c in df.columns]
            keep_cols += [f for f in fields if f in df.columns and f not in keep_cols]
            df = df[keep_cols]

        return df.sort_values(["symbol", "session_date"]).reset_index(drop=True)

    def get_latest_date(self) -> dt.date:
        """Get the most recent session_date in the data."""
        return self._bars["session_date"].max()


# ── Standard output columns for factor values ──

FACTOR_OUTPUT_COLUMNS = [
    "symbol", "ts", "timeframe", "factor_name", "factor_version",
    "value", "available_at", "quality_score",
]


def make_factor_output(
    symbol: str,
    ts: pd.Series,
    timeframe: str,
    factor_name: str,
    factor_version: str,
    values: pd.Series,
    available_at: Optional[pd.Series] = None,
    quality_score: float = 1.0,
) -> pd.DataFrame:
    """
    Helper to build a standardized factor output DataFrame.
    """
    out = pd.DataFrame({
        "symbol": symbol,
        "ts": ts.values,
        "timeframe": timeframe,
        "factor_name": factor_name,
        "factor_version": factor_version,
        "value": values.values,
        "available_at": available_at.values if available_at is not None else ts.values,
        "quality_score": quality_score,
    })
    # Drop NaN values
    out = out.dropna(subset=["value"])
    return out[FACTOR_OUTPUT_COLUMNS]


# ── Factor Protocol ──

class Factor(Protocol):
    """Protocol that all factors must satisfy."""
    spec: FactorSpec

    def compute(self, ctx: FactorContext) -> pd.DataFrame:
        """
        Compute factor values for all symbols and dates.

        Must return DataFrame with columns:
          symbol, ts, timeframe, factor_name, factor_version,
          value, available_at, quality_score
        """
        ...


# ── Utility functions for common calculations ──

def rolling_zscore(series: pd.Series, window: int) -> pd.Series:
    """Compute rolling z-score of a series."""
    mean = series.rolling(window=window, min_periods=max(1, window // 2)).mean()
    std = series.rolling(window=window, min_periods=max(1, window // 2)).std()
    return (series - mean) / std.replace(0, np.nan)


def tanh_normalize(series: pd.Series, scale: float = 1.0) -> pd.Series:
    """Normalize values to [-1, +1] using tanh with configurable scale."""
    return np.tanh(series / scale)


def clip_normalize(series: pd.Series, clip_val: float = 3.0) -> pd.Series:
    """Normalize by clipping and mapping to [-1, +1]."""
    clipped = series.clip(-clip_val, clip_val)
    return clipped / clip_val
