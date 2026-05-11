import pandas as pd

from src.integrations.vectorbt_adapter import make_long_only_signals


def test_make_long_only_signals_turns_bullish_bias_into_entries():
    predictions = pd.DataFrame(
        {
            "ts": pd.date_range("2026-05-01", periods=4),
            "symbol": ["NDX"] * 4,
            "bias_score": [0.1, 0.4, 0.5, -0.2],
        }
    )

    signals = make_long_only_signals(predictions, threshold=0.3)

    assert signals["entry"].tolist() == [False, True, False, False]
    assert signals["exit"].tolist() == [False, False, False, True]
