from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ModelRegistry:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "model_registry.jsonl"

    def register(
        self,
        model_name: str,
        model_version: str,
        feature_set_version: str,
        label_version: str,
        metrics: dict[str, Any],
    ) -> dict[str, Any]:
        record = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "model_name": model_name,
            "model_version": model_version,
            "feature_set_version": feature_set_version,
            "label_version": label_version,
            "metrics": metrics,
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        return record
