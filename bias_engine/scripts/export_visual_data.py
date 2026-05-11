"""
Export pipeline outputs to JSON for the static HTML visualization page.

Usage:
    python scripts/export_visual_data.py

Reads:
    data/predictions/predictions.parquet
    data/features/factor_quality.parquet
    data/features/factor_values.parquet

Outputs:
    visual/data/predictions.json
    visual/data/factor_quality.json
    visual/data/factor_latest.json
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
VISUAL_DATA_DIR = PROJECT_ROOT / "visual" / "data"


def export_predictions():
    path = DATA_DIR / "predictions" / "predictions.parquet"
    if not path.exists():
        print(f"[ERROR] {path} not found.")
        print("  Run pipeline first: python run_pipeline.py --step all --start 2023-01-01")
        return
    df = pd.read_parquet(path)
    # Add feature_set_version if missing
    if "feature_set_version" not in df.columns:
        df["feature_set_version"] = "feature_set_v1"
    # Convert top_factors columns (may contain list-of-dicts or string)
    for col in ("top_positive_factors", "top_negative_factors"):
        if col in df.columns:
            df[col] = df[col].apply(
                lambda x: json.loads(x) if isinstance(x, str) else (x if isinstance(x, list) else [])
            )
    out = df.to_dict(orient="records")
    VISUAL_DATA_DIR.mkdir(parents=True, exist_ok=True)
    out_path = VISUAL_DATA_DIR / "predictions.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"[OK] Exported {len(out)} predictions to {out_path}")


def export_factor_quality():
    path = DATA_DIR / "features" / "factor_quality.parquet"
    if not path.exists():
        print(f"[WARN] {path} not found, skipping")
        return
    df = pd.read_parquet(path)
    out = df.to_dict(orient="records")
    VISUAL_DATA_DIR.mkdir(parents=True, exist_ok=True)
    out_path = VISUAL_DATA_DIR / "factor_quality.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"[OK] Exported {len(out)} factor quality rows to {out_path}")


def export_factor_latest():
    path = DATA_DIR / "features" / "factor_values.parquet"
    if not path.exists():
        print(f"[WARN] {path} not found, skipping")
        return
    df = pd.read_parquet(path)
    # Keep only the latest row per (symbol, factor_name)
    if "session_date" in df.columns:
        date_col = "session_date"
    elif "ts" in df.columns:
        date_col = "ts"
    else:
        date_col = None

    if date_col:
        df[date_col] = pd.to_datetime(df[date_col])
        df = df.sort_values(date_col)
        latest = df.groupby(["symbol", "factor_name"], as_index=False).last()
    else:
        latest = df

    keep_cols = [c for c in ["symbol", "factor_name", "factor_version", "value", "quality_score"] if c in latest.columns]
    out = latest[keep_cols].to_dict(orient="records")
    VISUAL_DATA_DIR.mkdir(parents=True, exist_ok=True)
    out_path = VISUAL_DATA_DIR / "factor_latest.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"[OK] Exported {len(out)} latest factor rows to {out_path}")


def main():
    print("=== Exporting visual data ===")
    export_predictions()
    export_factor_quality()
    export_factor_latest()
    print("Done.")


if __name__ == "__main__":
    main()
