from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class BiasHorizon(str, Enum):
    D1 = "D1"
    W1 = "W1"
    M1 = "M1"


class BiasLabel(str, Enum):
    BULLISH = "bullish"
    NEUTRAL = "neutral"
    BEARISH = "bearish"


@dataclass(frozen=True)
class PredictionRecord:
    symbol: str
    ts: str
    horizon: BiasHorizon
    model_name: str
    model_version: str
    p_down: float
    p_neutral: float
    p_up: float
    confidence: float
    top_factors_json: str

    @property
    def bias_score(self) -> float:
        return round(self.p_up - self.p_down, 10)

    @property
    def label(self) -> BiasLabel:
        if self.bias_score >= 0.3:
            return BiasLabel.BULLISH
        if self.bias_score <= -0.3:
            return BiasLabel.BEARISH
        return BiasLabel.NEUTRAL
