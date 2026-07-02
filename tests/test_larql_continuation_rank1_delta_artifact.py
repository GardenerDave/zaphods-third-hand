from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/larql_continuation_rank1_delta_artifact.py"
SPEC = importlib.util.spec_from_file_location("larql_continuation_rank1_delta_artifact", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def write_json(path: Path, payload: dict | list) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def stable_hash(values: list[float]) -> str:
    return MODULE.stable_vector_hash(values)


def design_payload(*, mutate: dict | None = None) -> dict:
    output_direction = [0.6, 0.8]
    input_direction = [0.0, 0.6, 0.8]
    payload = {
        "report_type": "larql_continuation_rank1_delta_design.v0",
        "evidence_only": True,
        "model_free_packet": True,
        "delta_design_only": True,
        "source_continuation_direction_packet_path": "continuation_direction_packet.json",
        "source_continuation_direction_vectors_path": "continuation_direction_vectors.json",
        "target_module": "model.layers.0.mlp.down_proj",
        "target_module_family": "mlp_projection",
        "vector_source": "continuation_prediction_position",
        "rank": 1,
        "delta_scale": 0.01,
        "proposed_delta_shape": [2, 3],
        "output_vector_length": 2,
        "input_vector_length": 3,
        "output_direction_norm": 1.0,
        "input_direction_norm": 1.0,
        "expected_delta_frobenius_norm": 0.01,
        "expected_nonzero_count": 6,
        "continuation_output_direction_sha256": stable_hash(output_direction),
        "continuation_input_direction_sha256": stable_hash(input_direction),
        "recommended_next_step": "continuation_rank1_delta_artifact",
        "required_next_step": "supervised_continuation_rank1_delta_design_review",
        "model_inference_performed": False,
        "generation_performed": False,
        "training_performed": False,
        "lora_or_peft_used": False,
        "weight_edit_performed": False,
        "delta_artifact_written": False,
        "patched_model_materialized": False,
        "base_model_overwritten": False,
        "promotion_authorized": False,
        "production_deployment_authorized": False,
        "registry_mutation_authorized": False,
        "install_authorized": False,
        "automatic_failure_to_curriculum_capture_authorized": False,
    }
    if mutate:
        payload.update(mutate)
    return payload


def vectors_payload(*, mutate: dict | None = None) -> dict:
    payload = {
        "report_type": "larql_continuation_direction_vectors.v0",
        "target_module": "model.layers.0.mlp.down_proj",
        "target_module_family": "mlp_projection",
        "vector_source": "continuation_prediction_position",
        "continuation_output_direction": [0.6, 0.8],
        "continuation_input_direction": [0.0, 0.6, 0.8],
    }
    if mutate:
        payload.update(mutate)
    return payload


def prepare_inputs(tmp_path: Path, *, design_mutate: dict | None = None, vectors_mutate: dict | None = None) -> tuple[Path, Path]:
    design = write_json(tmp_path / "design.json", design_payload(mutate=design_mutate))
    vectors = write_json(tmp_path / "vectors.json", vectors_payload(mutate=vectors_mutate))
    return design, vectors


def run_script(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_authorization_required(tmp_path):
    design, vectors = prepare_inputs(tmp_path)
    result = run_script(
        "--run-id", "art_001",
        "--out-root", tmp_path / "out",
        "--continuation-rank1-delta-design", design,
        "--continuation-direction-vectors", vectors,
    )
    assert result.returncode != 0
    assert "requires explicit opt-in authorization" in result.stdout


def test_output_directory_exists_fails_closed(tmp_path):
    (tmp_path / "out" / "art_002").mkdir(parents=True)
    design, vectors = prepare_inputs(tmp_path)
    result = run_script(
        "--run-id", "art_002",
        "--out-root", tmp_path / "out",
        "--continuation-rank1-delta-design", design,
        "--continuation-direction-vectors", vectors,
        "--authorize-larql-continuation-rank1-delta-artifact",
    )
    assert result.returncode != 0
    assert "output directory already exists" in result.stdout


def test_validation_failures(tmp_path):
    cases = [
        ({"report_type": "other"}, "report_type mismatch"),
        ({"evidence_only": False}, "must be evidence_only true"),
        ({"model_free_packet": False}, "must be model_free_packet true"),
        ({"delta_design_only": False}, "must be delta_design_only true"),
        ({"recommended_next_step": "other"}, "recommended_next_step must be continuation_rank1_delta_artifact"),
        ({"model_inference_performed": True}, "model_inference_performed must be false"),
        ({"generation_performed": True}, "generation_performed must be false"),
        ({"training_performed": True}, "training_performed must be false"),
        ({"lora_or_peft_used": True}, "lora_or_peft_used must be false"),
        ({"weight_edit_performed": True}, "weight_edit_performed must be false"),
        ({"delta_artifact_written": True}, "delta_artifact_written must be false"),
        ({"patched_model_materialized": True}, "patched_model_materialized must be false"),
        ({"base_model_overwritten": True}, "base_model_overwritten must be false"),
        ({"promotion_authorized": True}, "promotion_authorized must be false"),
        ({"production_deployment_authorized": True}, "production_deployment_authorized must be false"),
        ({"registry_mutation_authorized": True}, "registry_mutation_authorized must be false"),
        ({"install_authorized": True}, "install_authorized must be false"),
        ({"automatic_failure_to_curriculum_capture_authorized": True}, "automatic_failure_to_curriculum_capture_authorized must be false"),
    ]
    for index, (mutate, message) in enumerate(cases):
        design, vectors = prepare_inputs(tmp_path, design_mutate=mutate)
        result = run_script(
            "--run-id", f"art_bad_{index}",
            "--out-root", tmp_path / "out",
            "--continuation-rank1-delta-design", design,
            "--continuation-direction-vectors", vectors,
            "--authorize-larql-continuation-rank1-delta-artifact",
        )
        assert result.returncode != 0
        assert message in result.stdout


def test_vector_validation_failures(tmp_path):
    cases = [
        ({"target_module": "other"}, "target_module mismatch between design packet and vectors"),
        ({"target_module_family": "other"}, "target_module_family mismatch between design packet and vectors"),
        ({"vector_source": "other"}, "vector_source mismatch between design packet and vectors"),
        ({"continuation_output_direction": None}, "continuation_output_direction missing"),
        ({"continuation_input_direction": None}, "continuation_input_direction missing"),
        ({"continuation_output_direction": [0.5, 0.5, 0.5]}, "output direction length does not match design packet"),
        ({"continuation_input_direction": [0.5, 0.5]}, "input direction length does not match design packet"),
        ({"continuation_output_direction": [2.0, 0.0]}, "output direction norm is zero, non-finite, or not approximately 1.0"),
        ({"continuation_input_direction": [0.0, 2.0, 0.0]}, "input direction norm is zero, non-finite, or not approximately 1.0"),
    ]
    for index, (mutate, message) in enumerate(cases):
        design, vectors = prepare_inputs(tmp_path, vectors_mutate=mutate)
        result = run_script(
            "--run-id", f"vec_bad_{index}",
            "--out-root", tmp_path / "out",
            "--continuation-rank1-delta-design", design,
            "--continuation-direction-vectors", vectors,
            "--authorize-larql-continuation-rank1-delta-artifact",
        )
        assert result.returncode != 0
        assert message in result.stdout

    for index, (mutate, message) in enumerate([
        ({"continuation_output_direction": [1.0, 0.0], "continuation_input_direction": [1.0, 0.0, 0.0], "continuation_output_direction_sha256": "0" * 64}, "continuation output direction hash mismatch"),
        ({"continuation_output_direction": [0.6, 0.8], "continuation_input_direction": [1.0, 0.0, 0.0], "continuation_input_direction_sha256": "0" * 64}, "continuation input direction hash mismatch"),
    ], start=len(cases)):
        design, vectors = prepare_inputs(tmp_path, vectors_mutate=mutate)
        result = run_script(
            "--run-id", f"vec_bad_hash_{index}",
            "--out-root", tmp_path / "out",
            "--continuation-rank1-delta-design", design,
            "--continuation-direction-vectors", vectors,
            "--authorize-larql-continuation-rank1-delta-artifact",
        )
        assert result.returncode != 0
        assert message in result.stdout


def test_invalid_format_and_shape_checks(tmp_path):
    design, vectors = prepare_inputs(tmp_path)
    result = run_script(
        "--run-id", "art_bad_fmt",
        "--out-root", tmp_path / "out",
        "--continuation-rank1-delta-design", design,
        "--continuation-direction-vectors", vectors,
        "--artifact-format", "pt",
        "--authorize-larql-continuation-rank1-delta-artifact",
    )
    assert result.returncode != 0
    assert "unsupported artifact format" in result.stdout


def test_successful_safetensors_write(tmp_path):
    design, vectors = prepare_inputs(tmp_path)
    out_root = tmp_path / "out"
    result = run_script(
        "--run-id", "art_003",
        "--out-root", out_root,
        "--continuation-rank1-delta-design", design,
        "--continuation-direction-vectors", vectors,
        "--authorize-larql-continuation-rank1-delta-artifact",
    )
    assert result.returncode == 0
    out_dir = out_root / "art_003"
    record = json.loads((out_dir / "larql_continuation_rank1_delta_artifact_record.json").read_text(encoding="utf-8"))
    manifest = json.loads((out_dir / "continuation_rank1_delta_artifact_manifest.json").read_text(encoding="utf-8"))
    review = (out_dir / "continuation_rank1_delta_artifact_review_packet.md").read_text(encoding="utf-8")
    artifact = out_dir / "rank1_delta.safetensors"
    assert artifact.exists()
    assert record["report_type"] == "larql_continuation_rank1_delta_artifact.v0"
    assert record["delta_artifact_written"] is True
    assert record["patched_model_materialized"] is False
    assert record["base_model_overwritten"] is False
    assert record["promotion_authorized"] is False
    assert record["automatic_failure_to_curriculum_capture_authorized"] is False
    assert record["target_parameter"] == "model.layers.0.mlp.down_proj.weight"
    assert record["delta_shape"] == [2, 3]
    assert record["delta_dtype"] == "float32"
    assert record["expected_delta_frobenius_norm"] == 0.01
    assert record["artifact_sha256"]
    assert manifest["artifact_path"] == str(artifact)
    assert manifest["recommended_next_step"] == "supervised_continuation_delta_artifact_review"
    assert "target parameter key" in review
    assert len(record["artifact_sha256"]) == 64
    assert record["nonzero_count"] == 4


def test_no_inference_generation_training_materialization_or_promotion_in_source():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "generate(" not in text
    assert "from transformers import" not in text[:1200]
    assert "materialize_patched_model" not in text
