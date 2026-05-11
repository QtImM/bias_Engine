# PyBroker Integration Notes

PyBroker (edtechre/pybroker) is useful as a validation reference.

## What we borrow

- Walk-forward validation pattern: rolling train/test windows with embargo gaps.
- Model registration: every trained model is versioned with feature set and label version.
- Feature matrix: factors are pivoted into a wide matrix per (symbol, ts) for ML training.

## What we do NOT borrow

- PyBroker's execution framework: we predict bias, not trade signals.
- PyBroker's data fetching: we use our own AKShare + yfinance ingestion.

## How to use PyBroker ideas

1. Use `make_walk_forward_splits` from `src/validation/walk_forward.py`.
2. Train on train window, predict on test window, record metrics.
3. Slide forward by `step_size` and repeat.
4. Compare champion (current production) vs challenger (new factor set or model).
