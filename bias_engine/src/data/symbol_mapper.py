"""
Symbol mapper: translates between internal symbols and provider-specific symbols.

Internal symbols (STAR50, HSI, NDX) are used throughout the system.
Provider symbols are used when fetching data from external sources.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml


class SymbolMapper:
    """Maps internal symbols to data provider symbols."""

    def __init__(self, config_path: str | Path):
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        self._instruments: dict[str, dict] = {}
        for inst in cfg.get("instruments", []):
            if inst.get("active", True):
                self._instruments[inst["symbol"]] = inst

    @property
    def symbols(self) -> list[str]:
        """Return all active internal symbols."""
        return list(self._instruments.keys())

    def get_instrument(self, symbol: str) -> dict:
        """Get full instrument config by internal symbol."""
        if symbol not in self._instruments:
            raise KeyError(f"Unknown symbol: {symbol}. Known: {self.symbols}")
        return self._instruments[symbol]

    def to_provider(self, symbol: str, provider: str) -> str:
        """Get provider-specific symbol for a given internal symbol and provider."""
        inst = self.get_instrument(symbol)
        provider_symbols = inst.get("provider_symbols", {})
        if provider not in provider_symbols:
            raise KeyError(
                f"No {provider} symbol mapping for {symbol}. "
                f"Available: {list(provider_symbols.keys())}"
            )
        return provider_symbols[provider]

    def get_timezone(self, symbol: str) -> str:
        """Get the timezone for a symbol."""
        return self.get_instrument(symbol).get("timezone", "UTC")

    def get_market(self, symbol: str) -> str:
        """Get the market code for a symbol."""
        return self.get_instrument(symbol).get("market", "UNKNOWN")

    def get_primary_provider(self, symbol: str) -> str:
        """Get the primary data provider for a symbol."""
        return self.get_instrument(symbol).get("primary_provider", "yfinance")

    def has_provider(self, symbol: str, provider: str) -> bool:
        """Check if a symbol has a mapping for the given provider."""
        inst = self.get_instrument(symbol)
        return provider in inst.get("provider_symbols", {})
