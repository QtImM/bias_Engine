import pandas as pd

from src.validation.backtest_report import summarize_bias_buckets


def test_summarize_bias_buckets_groups_forward_returns():
    df = pd.DataFrame(
        {
            "bias_score": [-0.8, -0.4, 0.0, 0.4, 0.8],
            "fwd_return": [-0.03, -0.01, 0.0, 0.02, 0.04],
        }
    )

    report = summarize_bias_buckets(df)

    assert set(report["bucket"]) == {"bearish", "neutral", "bullish"}
    assert report.loc[report["bucket"] == "bullish", "mean_return"].iloc[0] == 0.03
