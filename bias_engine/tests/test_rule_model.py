import pandas as pd

from src.models.rule_model import RuleModel
from src.core.paths import CONFIG_DIR


def test_rule_model_accepts_factor_values_with_ts_instead_of_session_date():
    model = RuleModel(CONFIG_DIR / "models.yaml")
    factor_values = pd.DataFrame(
        [
            {
                "symbol": "STAR50",
                "ts": pd.Timestamp("2026-05-10"),
                "factor_name": "return_5d",
                "value": 0.2,
            },
            {
                "symbol": "STAR50",
                "ts": pd.Timestamp("2026-05-11"),
                "factor_name": "return_5d",
                "value": 0.4,
            },
        ]
    )

    prediction = model.predict(factor_values, "STAR50", "D1")

    assert prediction["as_of"] == "2026-05-11"
    assert prediction["num_factors_used"] == 1
