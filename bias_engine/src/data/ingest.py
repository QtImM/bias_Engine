"""
Data ingestion layer: fetches OHLCV data from AKShare and yfinance.

Each provider has its own fetch function that returns a normalized DataFrame.
Storage uses Parquet files partitioned by provider/symbol.
"""
from __future__ import annotations

import datetime as dt
import time
from pathlib import Path
from typing import Optional

import pandas as pd
from loguru import logger

from .normalize import normalize_bars
from .symbol_mapper import SymbolMapper


# ── Provider-specific fetchers ──

def fetch_akshare(
    symbol: str,
    start: dt.date,
    end: dt.date,
    mapper: SymbolMapper,
) -> pd.DataFrame:
    """
    Fetch daily OHLCV from AKShare.
    AKShare provides Chinese market indices directly.
    """
    import akshare as ak

    provider_symbol = mapper.to_provider(symbol, "akshare")
    market = mapper.get_market(symbol)
    timezone = mapper.get_timezone(symbol)

    logger.info(f"Fetching {symbol} from AKShare (symbol={provider_symbol})")

    try:
        if market == "CN":
            # Chinese index daily data
            df = ak.stock_zh_index_daily(symbol=f"sh{provider_symbol}")
            # AKShare returns: date, open, high, low, close, volume
        elif market == "HK":
            # Hong Kong index - try HSI specific
            df = ak.stock_hk_index_daily_em(symbol=provider_symbol)
        else:
            raise ValueError(f"AKShare does not support market: {market}")

        # Filter date range
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            df = df[(df["date"] >= pd.Timestamp(start)) & (df["date"] <= pd.Timestamp(end))]

        return normalize_bars(
            df, symbol=symbol, provider="akshare",
            market=market, timezone=timezone,
        )
    except Exception as e:
        logger.error(f"AKShare fetch failed for {symbol}: {e}")
        raise


def fetch_yfinance(
    symbol: str,
    start: dt.date,
    end: dt.date,
    mapper: SymbolMapper,
) -> pd.DataFrame:
    """
    Fetch daily OHLCV from yfinance.
    Works well for HSI, NDX. May have issues with some CN indices.
    """
    import yfinance as yf

    provider_symbol = mapper.to_provider(symbol, "yfinance")
    market = mapper.get_market(symbol)
    timezone = mapper.get_timezone(symbol)

    logger.info(f"Fetching {symbol} from yfinance (symbol={provider_symbol})")

    try:
        ticker = yf.Ticker(provider_symbol)
        df = ticker.history(start=start, end=end, auto_adjust=False)

        if df.empty:
            raise ValueError(f"No data returned from yfinance for {provider_symbol}")

        # yfinance returns: Open, High, Low, Close, Volume, Dividends, Stock Splits
        # with DatetimeIndex
        df = df.reset_index()
        # Rename columns
        col_rename = {}
        for col in df.columns:
            cl = col.lower()
            if cl == "datetime" or cl == "date":
                col_rename[col] = "date"
            elif cl == "open":
                col_rename[col] = "open"
            elif cl == "high":
                col_rename[col] = "high"
            elif cl == "low":
                col_rename[col] = "low"
            elif cl == "close":
                col_rename[col] = "close"
            elif cl == "volume":
                col_rename[col] = "volume"
        df = df.rename(columns=col_rename)

        return normalize_bars(
            df, symbol=symbol, provider="yfinance",
            market=market, timezone=timezone,
        )
    except Exception as e:
        logger.error(f"yfinance fetch failed for {symbol}: {e}")
        raise


# ── Main ingestion orchestrator ──

PROVIDER_FETCHERS = {
    "akshare": fetch_akshare,
    "yfinance": fetch_yfinance,
}


class DataIngester:
    """
    Orchestrates data fetching and local storage.

    Storage layout:
      data/raw/provider={provider}/symbol={symbol}/bars.parquet
    """

    def __init__(self, project_root: str | Path, mapper: SymbolMapper):
        self.project_root = Path(project_root)
        self.raw_dir = self.project_root / "data" / "raw"
        self.mapper = mapper
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    def _parquet_path(self, provider: str, symbol: str) -> Path:
        path = self.raw_dir / f"provider={provider}" / f"symbol={symbol}"
        path.mkdir(parents=True, exist_ok=True)
        return path / "bars.parquet"

    def _load_existing(self, provider: str, symbol: str) -> Optional[pd.DataFrame]:
        path = self._parquet_path(provider, symbol)
        if path.exists():
            return pd.read_parquet(path)
        return None

    def fetch_and_store(
        self,
        symbol: str,
        start: dt.date = dt.date(2020, 1, 1),
        end: Optional[dt.date] = None,
        provider: Optional[str] = None,
        force: bool = False,
    ) -> pd.DataFrame:
        """
        Fetch data for a symbol and store to Parquet.

        Args:
            symbol: Internal symbol (STAR50, HSI, NDX)
            start: Start date for historical data
            end: End date (defaults to today)
            provider: Override provider (default: use symbol's primary)
            force: If True, re-fetch all data ignoring cache
        """
        if end is None:
            end = dt.date.today()
        if provider is None:
            provider = self.mapper.get_primary_provider(symbol)

        if provider not in PROVIDER_FETCHERS:
            raise ValueError(f"Unknown provider: {provider}. Available: {list(PROVIDER_FETCHERS.keys())}")

        # Check existing data to determine incremental start
        if not force:
            existing = self._load_existing(provider, symbol)
            if existing is not None and not existing.empty:
                last_date = existing["session_date"].max()
                if isinstance(last_date, str):
                    last_date = dt.date.fromisoformat(last_date)
                if last_date >= end:
                    logger.info(f"{symbol}: data already up to date ({last_date})")
                    return existing
                # Fetch from day after last date
                incremental_start = last_date + dt.timedelta(days=1)
                logger.info(f"{symbol}: incremental fetch from {incremental_start}")
                start = max(start, incremental_start)
                if start >= end:
                    logger.info(f"{symbol}: no fetch needed for empty incremental window ({start} to {end})")
                    return existing

        # Fetch
        fetcher = PROVIDER_FETCHERS[provider]
        new_data = fetcher(symbol, start, end, self.mapper)

        if new_data.empty:
            logger.warning(f"{symbol}: no new data fetched")
            existing = self._load_existing(provider, symbol)
            return existing if existing is not None else pd.DataFrame()

        # Merge with existing
        existing = self._load_existing(provider, symbol)
        if existing is not None and not existing.empty:
            combined = pd.concat([existing, new_data], ignore_index=True)
            combined = combined.drop_duplicates(
                subset=["symbol", "session_date"], keep="last"
            )
            combined = combined.sort_values("session_date").reset_index(drop=True)
        else:
            combined = new_data

        # Save
        path = self._parquet_path(provider, symbol)
        combined.to_parquet(path, index=False)
        logger.info(f"{symbol}: saved {len(combined)} bars to {path}")

        return combined

    def fetch_all(
        self,
        start: dt.date = dt.date(2020, 1, 1),
        end: Optional[dt.date] = None,
        force: bool = False,
    ) -> dict[str, pd.DataFrame]:
        """Fetch data for all active symbols."""
        results = {}
        for symbol in self.mapper.symbols:
            try:
                df = self.fetch_and_store(symbol, start, end, force=force)
                results[symbol] = df
                time.sleep(1)  # rate limiting between symbols
            except Exception as e:
                logger.error(f"Failed to fetch {symbol}: {e}")
                results[symbol] = pd.DataFrame()
        return results

    def load_bars(
        self,
        symbols: list[str] | None = None,
        start: Optional[dt.date] = None,
        end: Optional[dt.date] = None,
        provider: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Load bars from local Parquet storage.

        Returns unified DataFrame with all requested symbols.
        """
        if symbols is None:
            symbols = self.mapper.symbols

        all_bars = []
        for symbol in symbols:
            prov = provider or self.mapper.get_primary_provider(symbol)
            path = self._parquet_path(prov, symbol)
            if path.exists():
                df = pd.read_parquet(path)
                if start is not None:
                    df = df[df["session_date"] >= start]
                if end is not None:
                    df = df[df["session_date"] <= end]
                all_bars.append(df)

        if not all_bars:
            return pd.DataFrame()

        combined = pd.concat(all_bars, ignore_index=True)
        return combined.sort_values(["symbol", "session_date"]).reset_index(drop=True)
