from src.models.model_registry import ModelRegistry


def test_model_registry_writes_version_metadata(tmp_path):
    registry = ModelRegistry(tmp_path)
    record = registry.register(
        model_name="rule_model",
        model_version="rule_model_v1",
        feature_set_version="feature_set_v1",
        label_version="label_v1",
        metrics={"macro_f1": 0.42},
    )

    assert record["model_version"] == "rule_model_v1"
    assert (tmp_path / "model_registry.jsonl").exists()
