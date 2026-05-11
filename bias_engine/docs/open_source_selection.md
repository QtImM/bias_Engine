# Open Source Selection

This project keeps `bias_engine` as the main system and borrows selected capabilities from existing projects.

## Adopt as Concepts

`microsoft/qlib` is the main conceptual reference. We borrow its separation between data, features, labels, model training, rolling validation, backtest analysis, and online-style prediction.

`edtechre/pybroker` is the validation reference. We borrow the walk-forward mindset and model registration pattern, but keep our own feature matrix because this project predicts multi-timeframe bias rather than directly executing trades.

## Optional Adapters

`polakowo/vectorbt` is useful for fast signal tests and bias bucket return experiments. It remains optional because it is not needed to generate daily bias predictions.

`pmorissette/bt` is useful for portfolio-level rebalancing tests after single-index bias quality is stable.

## Not First-Phase Dependencies

`QuantConnect/Lean` is a professional execution and backtesting engine, but it is too heavy for the first phase.

`AI4Finance/FinRL` is useful for later reinforcement learning research, but the current project should first prove that its factor and label pipeline is reliable.
