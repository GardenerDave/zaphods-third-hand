import json
import subprocess
import sys

import pytest

from local_harness.failure_training.train_adapter import (
    build_adapter_manifest,
    dataset_paths_from_dir,
    default_adapter_id,
    default_trainer_config,
    normalize_adapter_status,
    normalize_training_method,
    write_adapter_plan,
)


def test_normalize_training_method_accepts_supported_methods():
    assert normalize_training_method("LORA") == "lora"
    assert normalize_training_method(" qlora ") == "qlora"
    assert normalize_training_method("external") == "external"


def test_normalize_training_method_rejects_unknown_method():
    with pytest.raises(ValueError, match="unsupported training method"):
        normalize_training_method("magic")


def test_normalize_adapter_status_accepts_supported_statuses():
    assert normalize_adapter_status("PLANNED") == "planned"
    assert normalize_adapter_status(" completed ") == "completed"


def test_normalize_adapter_status_rejects_unknown_status():
    with pytest.raises(ValueError, match="unsupported adapter status"):
        normalize_adapter_status("maybe")


def test_default_adapter_id_is_stable_and_uses_cycle_and_method():
    adapter_id = default_adapter_id(
        cycle_id="cycle 1",
        base_model_id="tiny/model",
        training_method="lora",
    )

    assert adapter_id.startswith("adapter_cycle_1_lora_")
    assert adapter_id == default_adapter_id(
        cycle_id="cycle 1",
        base_model_id="tiny/model",
        training_method="lora",
    )


def test_dataset_paths_from_dir_builds_expected_paths(tmp_path):
    paths = dataset_paths_from_dir(tmp_path / "datasets")

    assert paths["train"].endswith("datasets/train.jsonl")
    assert paths["validation"].endswith("datasets/validation.jsonl")
    assert paths["holdout"].endswith("datasets/holdout.jsonl")
    assert paths["sft_train"].endswith("datasets/sft/sft_train.jsonl")
    assert paths["sft_manifest"].endswith("datasets/sft/sft_manifest.jsonl")


def test_build_adapter_manifest_creates_planned_manifest(tmp_path):
    manifest = build_adapter_manifest(
        cycle_id="cycle_0001",
        base_model_id="tiny-model",
        dataset_dir=tmp_path / "datasets",
        output_dir=tmp_path / "adapter_plan",
        training_method="lora",
        trainer="mlx-lm",
        notes="smoke only",
    )

    assert manifest["adapter_id"].startswith("adapter_cycle_0001_lora_")
    assert manifest["cycle_id"] == "cycle_0001"
    assert manifest["base_model_id"] == "tiny-model"
    assert manifest["training_method"] == "lora"
    assert manifest["trainer"] == "mlx-lm"
    assert manifest["status"] == "planned"
    assert manifest["notes"] == "smoke only"
    assert manifest["dataset_paths"]["sft_train"].endswith("datasets/sft/sft_train.jsonl")
    assert manifest["artifact_paths"]["adapter_manifest"].endswith("adapter_manifest.json")


def test_default_trainer_config_is_manual_only(tmp_path):
    dataset_paths = dataset_paths_from_dir(tmp_path / "datasets")
    config = default_trainer_config(
        base_model_id="tiny-model",
        training_method="lora",
        dataset_paths=dataset_paths,
    )

    assert config["base_model_id"] == "tiny-model"
    assert config["training_method"] == "lora"
    assert config["train_path"] == dataset_paths["sft_train"]
    assert config["validation_path"] == dataset_paths["sft_validation"]
    assert config["launch_policy"] == "manual_only"


def test_write_adapter_plan_writes_manifest_and_config(tmp_path):
    output_dir = tmp_path / "adapter_plan"

    manifest = write_adapter_plan(
        cycle_id="cycle_0001",
        base_model_id="tiny-model",
        dataset_dir=tmp_path / "datasets",
        output_dir=output_dir,
        training_method="qlora",
        trainer="manual",
    )

    saved_manifest = json.loads((output_dir / "adapter_manifest.json").read_text(encoding="utf-8"))
    trainer_config = json.loads((output_dir / "trainer_config.json").read_text(encoding="utf-8"))

    assert saved_manifest == manifest
    assert saved_manifest["training_method"] == "qlora"
    assert trainer_config["launch_policy"] == "manual_only"
    assert trainer_config["train_path"].endswith("datasets/sft/sft_train.jsonl")


def test_train_adapter_cli_writes_plan_and_prints_summary(tmp_path):
    output_dir = tmp_path / "adapter_plan"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "local_harness.failure_training.train_adapter",
            "--cycle-id",
            "cycle_cli",
            "--base-model-id",
            "tiny-model",
            "--dataset-dir",
            str(tmp_path / "datasets"),
            "--output-dir",
            str(output_dir),
            "--training-method",
            "lora",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Adapter plan written:" in result.stdout
    assert "method=lora status=planned" in result.stdout
    assert (output_dir / "adapter_manifest.json").exists()
    assert (output_dir / "trainer_config.json").exists()
