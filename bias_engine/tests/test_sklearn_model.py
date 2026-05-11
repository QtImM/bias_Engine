import pandas as pd

from src.models.sklearn_model import train_multiclass_model


def test_train_multiclass_model_returns_probability_columns():
    X = pd.DataFrame(
        {
            "return_5d": [-1.0, -0.5, 0.0, 0.5, 1.0, 1.5],
            "rsi_14": [0.8, 0.6, 0.0, -0.2, -0.6, -0.8],
        }
    )
    y = pd.Series([-1, -1, 0, 0, 1, 1])

    model = train_multiclass_model(X, y, random_state=7)
    probabilities = model.predict_proba(X)

    assert probabilities.shape == (6, 3)
