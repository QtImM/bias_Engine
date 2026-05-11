import pandas as pd

from src.validation.walk_forward import make_walk_forward_splits


def test_walk_forward_splits_use_embargo_gap():
    dates = pd.date_range("2026-01-01", periods=120, freq="D")
    splits = make_walk_forward_splits(
        dates=dates,
        train_size=60,
        test_size=20,
        embargo=10,
        step_size=20,
    )

    first = splits[0]
    assert first.train_start == dates[0]
    assert first.train_end == dates[59]
    assert first.test_start == dates[70]
    assert first.test_end == dates[89]
