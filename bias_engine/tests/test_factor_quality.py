import pandas as pd

from src.quality.factor_quality import summarize_factor_quality


def test_factor_quality_reports_coverage_and_extreme_share():
    factor_values = pd.DataFrame(
        {
            "symbol": ["STAR50", "STAR50", "HSI", "HSI"],
            "factor_name": ["rsi_14", "rsi_14", "rsi_14", "rsi_14"],
            "value": [0.1, 0.2, 100.0, None],
        }
    )

    report = summarize_factor_quality(factor_values)

    assert report.loc[0, "factor_name"] == "rsi_14"
    assert report.loc[0, "rows"] == 4
    assert report.loc[0, "coverage"] == 0.75
    assert report.loc[0, "extreme_share"] == 0.25
