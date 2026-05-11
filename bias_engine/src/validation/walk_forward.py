from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class WalkForwardSplit:
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp


def make_walk_forward_splits(
    dates: pd.DatetimeIndex,
    train_size: int,
    test_size: int,
    embargo: int,
    step_size: int,
) -> list[WalkForwardSplit]:
    unique_dates = pd.DatetimeIndex(sorted(pd.unique(dates)))
    splits: list[WalkForwardSplit] = []
    start = 0
    while True:
        train_start_idx = start
        train_end_idx = train_start_idx + train_size - 1
        test_start_idx = train_end_idx + embargo + 1
        test_end_idx = test_start_idx + test_size - 1
        if test_end_idx >= len(unique_dates):
            break
        splits.append(
            WalkForwardSplit(
                train_start=unique_dates[train_start_idx],
                train_end=unique_dates[train_end_idx],
                test_start=unique_dates[test_start_idx],
                test_end=unique_dates[test_end_idx],
            )
        )
        start += step_size
    return splits
