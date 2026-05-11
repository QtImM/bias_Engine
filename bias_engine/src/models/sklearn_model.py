from __future__ import annotations

import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer


def train_multiclass_model(
    X: pd.DataFrame,
    y: pd.Series,
    random_state: int = 42,
) -> Pipeline:
    model = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            (
                "classifier",
                HistGradientBoostingClassifier(
                    max_iter=200,
                    learning_rate=0.05,
                    l2_regularization=0.05,
                    random_state=random_state,
                ),
            ),
        ]
    )
    model.fit(X, y)
    return model
