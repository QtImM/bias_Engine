"""
Main pipeline script for the Multi-Timeframe Bias Engine.

Usage:
    python run_pipeline.py                  # Run full pipeline
    python run_pipeline.py --step ingest    # Only fetch data
    python run_pipeline.py --step factors   # Only compute factors
    python run_pipeline.py --step predict   # Only run predictions
    python run_pipeline.py --step report    # Only print report
    python run_pipeline.py --start 2023-01-01  # Custom start date
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

import pandas as pd
from loguru import logger

# Setup logging
logger.remove()
logger.add(sys.stderr, level="INFO", format="{time:HH:mm:ss} | {level:7} | {message}")

# Project paths
PROJECT_ROOT = Path(__file__).parent
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"


def get_project_root() -> Path:
    return PROJECT_ROOT


# ── Step 1: Data Ingestion ──

def step_ingest(start: dt.date, end: dt.date) -> dict[str, pd.DataFrame]:
    """Fetch and store OHLCV data for all symbols."""
    from src.data.symbol_mapper import SymbolMapper
    from src.data.ingest import DataIngester

    mapper = SymbolMapper(CONFIG_DIR / "instruments.yaml")
    ingester = DataIngester(PROJECT_ROOT, mapper)

    logger.info(f"=== Data Ingestion: {start} to {end} ===")
    results = ingester.fetch_all(start=start, end=end)

    for symbol, df in results.items():
        if not df.empty:
            logger.info(f"  {symbol}: {len(df)} bars ({df['session_date'].min()} to {df['session_date'].max()})")
        else:
            logger.warning(f"  {symbol}: no data fetched")

    return results


def load_bars(start: dt.date = None, end: dt.date = None) -> pd.DataFrame:
    """Load bars from local storage."""
    from src.data.symbol_mapper import SymbolMapper
    from src.data.ingest import DataIngester

    mapper = SymbolMapper(CONFIG_DIR / "instruments.yaml")
    ingester = DataIngester(PROJECT_ROOT, mapper)
    return ingester.load_bars(start=start, end=end)


# ── Step 2: Compute Factors ──

def step_factors(bars: pd.DataFrame) -> pd.DataFrame:
    """Compute all factor values."""
    from src.factors.registry import FactorRegistry
    from src.factors.base import FactorContext

    logger.info("=== Computing Factors ===")

    registry = FactorRegistry.from_yaml(CONFIG_DIR / "factors.yaml")

    symbols = bars["symbol"].unique().tolist()
    start = bars["session_date"].min()
    end = bars["session_date"].max()

    ctx = FactorContext(
        symbols=symbols,
        start=start,
        end=end,
        bars=bars,
    )

    factor_values = registry.compute_all(ctx)

    if not factor_values.empty:
        # Save to Parquet
        output_dir = DATA_DIR / "features"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "factor_values.parquet"
        factor_values.to_parquet(output_path, index=False)
        logger.info(f"Saved {len(factor_values)} factor values to {output_path}")

        # Build and save feature matrix
        from src.features.feature_matrix import build_feature_matrix

        feature_matrix = build_feature_matrix(factor_values)
        matrix_path = DATA_DIR / "features" / "feature_matrix.parquet"
        feature_matrix.to_parquet(matrix_path, index=False)
        logger.info(f"Saved feature matrix to {matrix_path}")

        # Summary
        for fname in factor_values["factor_name"].unique():
            fv = factor_values[factor_values["factor_name"] == fname]
            logger.info(f"  {fname}: {len(fv)} rows, symbols: {fv['symbol'].unique().tolist()}")
    else:
        logger.warning("No factor values computed")

    return factor_values


def step_factor_quality(factor_values: pd.DataFrame) -> pd.DataFrame:
    """Generate factor quality report."""
    from src.quality.factor_quality import summarize_factor_quality

    logger.info("=== Factor Quality Report ===")
    report = summarize_factor_quality(factor_values)
    output_dir = DATA_DIR / "features"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "factor_quality.parquet"
    report.to_parquet(output_path, index=False)
    logger.info(f"Saved factor quality report to {output_path}")

    for _, row in report.iterrows():
        logger.info(f"  {row['factor_name']}: coverage={row['coverage']:.2f}, extreme={row['extreme_share']:.2f}")

    return report


# ── Step 3: Generate Labels ──

def step_labels(bars: pd.DataFrame) -> pd.DataFrame:
    """Generate training labels."""
    from src.labels.make_labels import LabelEngine

    logger.info("=== Generating Labels ===")

    label_engine = LabelEngine(CONFIG_DIR / "models.yaml")
    labels = label_engine.compute_all_labels(bars)

    if not labels.empty:
        label_engine.save_labels(labels, DATA_DIR / "labels")

        for horizon in labels["horizon"].unique():
            h_labels = labels[labels["horizon"] == horizon]
            logger.info(f"  {horizon}: {len(h_labels)} labels, "
                       f"distribution: {dict(h_labels['label'].value_counts().sort_index())}")
    else:
        logger.warning("No labels generated")

    return labels


# ── Step 4: Run Predictions ──

def step_predict(factor_values: pd.DataFrame) -> pd.DataFrame:
    """Run rule model predictions."""
    from src.models.rule_model import RuleModel

    logger.info("=== Running Predictions ===")

    model = RuleModel(CONFIG_DIR / "models.yaml")

    predictions = model.predict_all(factor_values)

    if not predictions.empty:
        model.save_predictions(predictions, DATA_DIR / "predictions")

        # Print summary
        for _, pred in predictions.iterrows():
            symbol = pred["symbol"]
            horizon = pred["horizon"]
            score = pred["bias_score"]
            label = pred["label"]
            conf = pred["confidence"]
            logger.info(f"  {symbol}/{horizon}: {score:+.3f} ({label}) conf={conf:.2f}")
    else:
        logger.warning("No predictions generated")

    return predictions


# ── Step 5: Generate Report ──

def step_report(predictions: pd.DataFrame) -> str:
    """Generate and print bias report."""
    from src.models.rule_model import RuleModel

    model = RuleModel(CONFIG_DIR / "models.yaml")
    report = model.format_report(predictions)
    print(report)
    return report


# ── Main ──

def main():
    parser = argparse.ArgumentParser(description="Multi-Timeframe Bias Engine Pipeline")
    parser.add_argument("--step", choices=["ingest", "factors", "labels", "predict", "report", "all"],
                       default="all", help="Which step to run")
    parser.add_argument("--start", type=str, default="2023-01-01",
                       help="Start date for data (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, default=None,
                       help="End date for data (YYYY-MM-DD, default: today)")
    parser.add_argument("--force", action="store_true",
                       help="Force re-fetch all data")

    args = parser.parse_args()

    start = dt.date.fromisoformat(args.start)
    end = dt.date.fromisoformat(args.end) if args.end else dt.date.today()

    logger.info(f"Pipeline: step={args.step}, start={start}, end={end}")

    if args.step in ("ingest", "all"):
        step_ingest(start, end)

    if args.step in ("factors", "all"):
        bars = load_bars(start, end)
        if bars.empty:
            logger.error("No bars available. Run ingest first.")
            return
        factor_values = step_factors(bars)
        if not factor_values.empty:
            step_factor_quality(factor_values)

    if args.step in ("labels", "all"):
        bars = load_bars(start, end)
        if not bars.empty:
            step_labels(bars)

    if args.step in ("predict", "all"):
        fv_path = DATA_DIR / "features" / "factor_values.parquet"
        if fv_path.exists():
            factor_values = pd.read_parquet(fv_path)
            predictions = step_predict(factor_values)
        else:
            logger.error("No factor values found. Run factors step first.")
            return

    if args.step in ("report", "all"):
        pred_path = DATA_DIR / "predictions" / "predictions.parquet"
        if pred_path.exists():
            predictions = pd.read_parquet(pred_path)
            step_report(predictions)
        else:
            logger.error("No predictions found. Run predict step first.")

    logger.info("Pipeline complete.")


if __name__ == "__main__":
    main()
