# Factor Lifecycle

Every factor moves through the same lifecycle.

## Add

1. Create a factor class that exposes `spec` and `compute(ctx)`.
2. Register it in `config/factors.yaml`.
3. Run the factor step and save `factor_values.parquet`.
4. Run the factor quality report.
5. Build a feature matrix.
6. Train or score with the current model.
7. Compare against the previous champion model.

## Disable

Set `enabled: false` in `config/factors.yaml`.

Do not delete the factor file when disabling a factor. Historical model versions must remain reproducible.

## Promote

A factor can enter the champion feature set only when:

1. Coverage is high enough for the target symbols and horizons.
2. `available_at` is not later than prediction time.
3. Extreme values are explainable.
4. Correlation with existing factors is not redundant.
5. Walk-forward validation improves at least one target horizon without materially damaging the others.

## Version

Changing a factor formula changes `factor_version`.

Example:

```text
ema_slope v1.0.0 = EMA20 five-day slope
ema_slope v1.1.0 = EMA20 five-day slope divided by realized volatility
```

## Evolution Review

因子进入 champion 之前，应先通过 Evolution Loop 生成或记录候选实验。

推荐顺序：

1. 观察 `factor_quality.parquet`。
2. 运行 `python run_pipeline.py --step evolution`。
3. 阅读 `data/evolution/evolution_report.md`。
4. 将候选实验复制为独立 experiment 配置。
5. 用 walk-forward 和 promotion policy 比较 champion / challenger。
6. 只有在没有明显退化时，才考虑 promote。
