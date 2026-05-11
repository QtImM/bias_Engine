import datetime as dt

import pandas as pd

from src.factors.base import FactorContext


def test_load_bars_filters_by_available_at_when_prediction_time_is_set():
    bars = pd.DataFrame(
        [
            {
                "symbol": "NDX",
                "timeframe": "1d",
                "ts": pd.Timestamp("2026-05-08"),
                "session_date": dt.date(2026, 5, 8),
                "close": 100.0,
                "available_at": pd.Timestamp("2026-05-09 06:00:00"),
            },
            {
                "symbol": "NDX",
                "timeframe": "1d",
                "ts": pd.Timestamp("2026-05-11"),
                "session_date": dt.date(2026, 5, 11),
                "close": 110.0,
                "available_at": pd.Timestamp("2026-05-12 06:00:00"),
            },
        ]
    )
    ctx = FactorContext(
        symbols=["NDX"],
        start=dt.date(2026, 5, 1),
        end=dt.date(2026, 5, 11),
        bars=bars,
        prediction_time=pd.Timestamp("2026-05-11 20:00:00"),
    )

    result = ctx.load_bars(fields=["close"])

    assert result["session_date"].tolist() == [dt.date(2026, 5, 8)]
