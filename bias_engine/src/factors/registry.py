"""
Factor registry: loads factor configurations and instantiates factor classes.

Usage:
    registry = FactorRegistry.from_yaml("config/factors.yaml")
    all_results = registry.compute_all(ctx)
"""
from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

import pandas as pd
import yaml
from loguru import logger

from .base import FACTOR_OUTPUT_COLUMNS, Factor, FactorContext


class FactorRegistry:
    """Registry of all configured factors."""

    def __init__(self):
        self._factors: dict[str, Factor] = {}
        self._config: dict[str, dict] = {}

    @classmethod
    def from_yaml(cls, config_path: str | Path) -> "FactorRegistry":
        """Load factor registry from YAML configuration."""
        registry = cls()

        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)

        for factor_cfg in cfg.get("factors", []):
            factor_id = factor_cfg["id"]
            if not factor_cfg.get("enabled", True):
                logger.info(f"Factor {factor_id} is disabled, skipping")
                continue

            try:
                factor = cls._instantiate_factor(factor_cfg)
                registry._factors[factor_id] = factor
                registry._config[factor_id] = factor_cfg
                logger.debug(f"Registered factor: {factor_id} ({factor.spec.name})")
            except Exception as e:
                logger.error(f"Failed to load factor {factor_id}: {e}")

        logger.info(f"Registered {len(registry._factors)} factors")
        return registry

    @staticmethod
    def _instantiate_factor(cfg: dict) -> Factor:
        """Instantiate a factor class from its config."""
        class_path = cfg["class_path"]
        params = cfg.get("params", {})

        # Import the class
        module_path, class_name = class_path.rsplit(".", 1)
        module_candidates = [module_path]
        if module_path.startswith("factors."):
            module_candidates.append(f"src.{module_path}")
        else:
            module_candidates.append(f"src.factors.{module_path}")

        last_error: ImportError | None = None
        for candidate in module_candidates:
            try:
                module = importlib.import_module(candidate)
                break
            except ImportError as e:
                last_error = e
        else:
            assert last_error is not None
            raise last_error

        factor_class = getattr(module, class_name)

        # Instantiate with params
        return factor_class(**params)

    @property
    def factor_ids(self) -> list[str]:
        return list(self._factors.keys())

    def get_factor(self, factor_id: str) -> Factor:
        return self._factors[factor_id]

    def get_config(self, factor_id: str) -> dict:
        return self._config[factor_id]

    def compute_one(self, factor_id: str, ctx: FactorContext) -> pd.DataFrame:
        """Compute a single factor."""
        factor = self._factors[factor_id]
        logger.info(f"Computing factor: {factor_id}")
        result = factor.compute(ctx)
        if not result.empty:
            result["factor_name"] = factor.spec.name
            result["factor_version"] = factor.spec.version
        return result

    def compute_all(self, ctx: FactorContext) -> pd.DataFrame:
        """Compute all registered factors and concatenate results."""
        all_results = []

        for factor_id, factor in self._factors.items():
            cfg = self._config[factor_id]
            # Check if symbols overlap
            factor_symbols = cfg.get("symbols", ctx.symbols)
            active_symbols = [s for s in ctx.symbols if s in factor_symbols]
            if not active_symbols:
                continue

            try:
                # Create a sub-context with only relevant symbols
                sub_bars = ctx._bars[ctx._bars["symbol"].isin(active_symbols)]
                sub_ctx = FactorContext(
                    symbols=active_symbols,
                    start=ctx.start,
                    end=ctx.end,
                    bars=sub_bars,
                    prediction_time=ctx.prediction_time,
                )
                result = factor.compute(sub_ctx)
                if not result.empty:
                    result["factor_name"] = factor.spec.name
                    result["factor_version"] = factor.spec.version
                    all_results.append(result)
                    logger.info(
                        f"  {factor_id}: {len(result)} rows for {active_symbols}"
                    )
            except Exception as e:
                logger.error(f"  {factor_id} failed: {e}")

        if not all_results:
            return pd.DataFrame(columns=FACTOR_OUTPUT_COLUMNS)

        combined = pd.concat(all_results, ignore_index=True)
        return combined

    def get_symbols_for_factor(self, factor_id: str) -> list[str]:
        """Get the configured symbols for a factor."""
        cfg = self._config.get(factor_id, {})
        return cfg.get("symbols", [])

    def get_horizons_for_factor(self, factor_id: str) -> list[str]:
        """Get the configured horizons for a factor."""
        cfg = self._config.get(factor_id, {})
        return cfg.get("horizons", ["D1"])

    def get_all_factor_ids_by_horizon(self, horizon: str) -> list[str]:
        """Get all factor IDs that apply to a given horizon."""
        result = []
        for factor_id, cfg in self._config.items():
            if horizon in cfg.get("horizons", []):
                result.append(factor_id)
        return result
