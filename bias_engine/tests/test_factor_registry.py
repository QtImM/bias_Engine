import datetime as dt

import pandas as pd

from src.factors.base import FactorContext
from src.factors.registry import FactorRegistry
from src.core.paths import CONFIG_DIR


def test_factor_registry_loads_from_yaml():
    registry = FactorRegistry.from_yaml(CONFIG_DIR / "factors.yaml")
    assert len(registry.factor_ids) > 0
    assert "return_5d" in registry.factor_ids


def test_factor_registry_returns_correct_horizons():
    registry = FactorRegistry.from_yaml(CONFIG_DIR / "factors.yaml")
    horizons = registry.get_horizons_for_factor("return_5d")
    assert "D1" in horizons
