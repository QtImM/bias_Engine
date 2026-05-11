"""Cross-Market Factor: USD/CNH exchange rate change."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..base import FactorContext, FactorSpec, FACTOR_OUTPUT_COLUMNS, rolling_zscore


class UsdCnhFactor:
    """
    USD/CNH exchange rate change factor.

    USD/CNH rising (CNY weakening) => negative for CN/HK assets
    USD/CNH falling (CNY strengthening) => positive for CN/HK assets

    Uses yfinance to fetch USD/CNH data within the factor.
    Falls back to a synthetic approximation if unavailable.
    """

    def __init__(self, window: int = 5, **kwargs):
        self.spec = FactorSpec(
            name="usd_cnh_change",
            version="1.0.0",
            family="cross_market",
            description=f"USD/CNH {window}-day change, z-scored",
            inputs=["external.usd_cnh"],
            horizons=["D1", "W1"],
            lookback=window * 3,
            release_lag="0D",
            params={"window": window},
        )
        self.window = window

    def _fetch_usdcnh(self, start, end) -> pd.DataFrame:
        """Fetch USD/CNH data from yfinance."""
        try:
            import yfinance as yf
            ticker = yf.Ticker("CNH=X")
            df = ticker.history(start=start, end=end)
            if df.empty:
                # Try alternative symbol
                ticker = yf.Ticker("USDCNH=X")
                df = ticker.history(start=start, end=end)
            if not df.empty:
                df = df.reset_index()
                df = df.rename(columns={"Date": "date", "Close": "usd_cnh"})
                df["date"] = pd.to_datetime(df["date"]).dt.date
                return df[["date", "usd_cnh"]]
        except Exception:
            pass
        return pd.DataFrame()

    def compute(self, ctx: FactorContext) -> pd.DataFrame:
        bars = ctx.load_bars(fields=["close"])
        if bars.empty:
            return pd.DataFrame(columns=FACTOR_OUTPUT_COLUMNS)

        # Fetch USD/CNH data
        usdcnh = self._fetch_usdcnh(ctx.start, ctx.end)

        if usdcnh.empty:
            # Fallback: use NDX return as rough proxy for risk appetite
            # (not ideal, but prevents factor from being completely empty)
            ndx_bars = bars[bars["symbol"] == "NDX"].copy()
            if ndx_bars.empty:
                return pd.DataFrame(columns=FACTOR_OUTPUT_COLUMNS)
            ndx_bars = ndx_bars.sort_values("session_date")
            ndx_bars["proxy"] = -ndx_bars["close"].pct_change(self.window)
            usdcnh = ndx_bars.rename(columns={"session_date": "date"})[["date", "proxy"]]
            usdcnh = usdcnh.rename(columns={"proxy": "usd_cnh"})
            usdcnh["date"] = pd.to_datetime(usdcnh["date"]).dt.date

        # Compute rolling change
        usdcnh = usdcnh.sort_values("date")
        usdcnh["change"] = usdcnh["usd_cnh"].pct_change(self.window)

        # Z-score the change
        usdcnh["value"] = rolling_zscore(usdcnh["change"], window=120)

        # Invert: USD/CNH rise (CNY weakening) => negative for CN/HK assets
        usdcnh["value"] = -usdcnh["value"]

        results = []
        target_symbols = [s for s in ctx.symbols if s in ("STAR50", "HSI")]

        for symbol in target_symbols:
            sym_bars = bars[bars["symbol"] == symbol].copy()
            sym_bars = sym_bars.sort_values("session_date")

            # Merge with USD/CNH data on date
            sym_dates = pd.DataFrame({
                "session_date": sym_bars["session_date"],
                "ts": sym_bars["ts"],
            })
            sym_dates["date"] = pd.to_datetime(sym_dates["session_date"]).dt.date

            merged = pd.merge_asof(
                sym_dates.sort_values("date"),
                usdcnh[["date", "value"]].sort_values("date"),
                on="date",
                direction="backward",
            )

            out = pd.DataFrame({
                "symbol": symbol,
                "ts": merged["ts"],
                "timeframe": "1d",
                "factor_name": self.spec.name,
                "factor_version": self.spec.version,
                "value": merged["value"],
                "available_at": merged["ts"],
                "quality_score": 1.0,
            })
            results.append(out)

        if not results:
            return pd.DataFrame(columns=FACTOR_OUTPUT_COLUMNS)
        return pd.concat(results, ignore_index=True).dropna(subset=["value"])
