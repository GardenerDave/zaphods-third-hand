from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/larql_continuation_rank1_delta_design.py"
SPEC = importlib.util.spec_from_file_location("larql_continuation_rank1_delta_design", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def write_json(path: Path, payload: dict | list) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def packet_fixture(tmp_path: Path, *, mutate: dict | None = None) -> Path:
    payload = {
        "report_type": "larql_continuation_direction_packet.v0",
        "evidence_only": True,
        "model_free_packet": True,
        "direction_mode": "target_minus_control",
        "source_continuation_activation_vectors_path": str(tmp_path / "vectors.jsonl"),
        "source_continuation_activation_summary_path": str(tmp_path / "summary.json"),
        "source_capture_record_path": str(tmp_path / "capture.json"),
        "target_module": "model.layers.0.mlp.down_proj",
        "target_module_family": "mlp_projection",
        "vector_source": "continuation_prediction_position",
        "boost_count": 2,
        "suppress_count": 2,
        "control_count": 2,
        "input_vector_length": 3,
        "output_vector_length": 2,
        "output_direction_norm_before_normalization": 1.0,
        "input_direction_norm_before_normalization": 1.0,
        "recommended_next_step": "continuation_rank1_delta_design",
        "required_next_step": "supervised_continuation_direction_review",
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
    return write_json(tmp_path / "continuation_direction_packet.json", payload)


def vectors_fixture(tmp_path: Path, *, mutate: dict | None = None) -> Path:
    payload = {
        "report_type": "larql_continuation_direction_vectors.v0",
        "run_id": "dir_001",
        "target_module": "model.layers.0.mlp.down_proj",
        "target_module_family": "mlp_projection",
        "vector_source": "continuation_prediction_position",
        "continuation_output_direction": [0.6, 0.8],
        "continuation_input_direction": [0.0, 0.6, 0.8],
        "boost_output_mean": [1.0, 0.0],
        "suppress_output_mean": [0.0, 1.0],
        "control_output_mean": [0.5, 0.5],
        "boost_input_mean": [1.0, 0.0, 0.0],
        "suppress_input_mean": [0.0, 1.0, 0.0],
        "control_input_mean": [0.5, 0.5, 0.0],
    }
    if mutate:
        payload.update(mutate)
    return write_json(tmp_path / "continuation_direction_vectors.json", payload)


def run_script(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_authorization_required(tmp_path):
    result = run_script(
        "--run-id", "rd_001",
        "--out-root", tmp_path / "out",
        "--continuation-direction-packet", packet_fixture(tmp_path),
        "--continuation-direction-vectors", vectors_fixture(tmp_path),
    )
    assert result.returncode != 0
    assert "requires explicit opt-in authorization" in result.stdout


def test_output_directory_exists_fails_closed(tmp_path):
    (tmp_path / "out" / "rd_002").mkdir(parents=True)
    result = run_script(
        "--run-id", "rd_002",
        "--out-root", tmp_path / "out",
        "--continuation-direction-packet", packet_fixture(tmp_path),
        "--continuation-direction-vectors", vectors_fixture(tmp_path),
        "--authorize-larql-continuation-rank1-delta-design",
    )
    assert result.returncode != 0
    assert "output directory already exists" in result.stdout


def test_missing_inputs_fail_closed(tmp_path):
    result = run_script(
        "--run-id", "rd_003",
        "--out-root", tmp_path / "out",
        "--continuation-direction-packet", tmp_path / "missing.json",
        "--continuation-direction-vectors", vectors_fixture(tmp_path),
        "--authorize-larql-continuation-rank1-delta-design",
    )
    assert result.returncode != 0
    assert "required file path does not exist" in result.stdout


def test_validation_failures(tmp_path):
    for index, (mutate, message) in enumerate([
        ({"evidence_only": False}, "source continuation direction packet must be evidence_only true"),
        ({"model_free_packet": False}, "source continuation direction packet must be model_free_packet true"),
        ({"recommended_next_step": "other"}, "source continuation direction packet recommended_next_step must be continuation_rank1_delta_design"),
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
    ]):
        result = run_script(
            "--run-id", f"rd_{index}",
            "--out-root", tmp_path / "out",
            "--continuation-direction-packet", packet_fixture(tmp_path, mutate=mutate),
            "--continuation-direction-vectors", vectors_fixture(tmp_path),
            "--authorize-larql-continuation-rank1-delta-design",
        )
        assert result.returncode != 0
        assert message in result.stdout


def test_source_record_and_packet_mismatch_checks(tmp_path):
    bad_packet = packet_fixture(tmp_path, mutate={"target_module_family": "other"})
    result = run_script(
        "--run-id", "rd_010",
        "--out-root", tmp_path / "out",
        "--continuation-direction-packet", bad_packet,
        "--continuation-direction-vectors", vectors_fixture(tmp_path),
        "--authorize-larql-continuation-rank1-delta-design",
    )
    assert result.returncode != 0
    assert "target_module_family must be mlp_projection" in result.stdout

    bad_vectors = vectors_fixture(tmp_path, mutate={"target_module": "other"})
    result = run_script(
        "--run-id", "rd_011",
        "--out-root", tmp_path / "out",
        "--continuation-direction-packet", packet_fixture(tmp_path),
        "--continuation-direction-vectors", bad_vectors,
        "--authorize-larql-continuation-rank1-delta-design",
    )
    assert result.returncode != 0
    assert "mismatch between packet and vectors" in result.stdout


def test_dimension_and_norm_checks(tmp_path):
    bad_vectors = vectors_fixture(tmp_path, mutate={"continuation_output_direction": [0.0, 0.0]})
    result = run_script(
        "--run-id", "rd_012",
        "--out-root", tmp_path / "out",
        "--continuation-direction-packet", packet_fixture(tmp_path),
        "--continuation-direction-vectors", bad_vectors,
        "--authorize-larql-continuation-rank1-delta-design",
    )
    assert result.returncode != 0
    assert "output direction norm is zero or non-finite" in result.stdout

    bad_vectors = vectors_fixture(tmp_path, mutate={"continuation_input_direction": [2.0, 0.0, 0.0]})
    result = run_script(
        "--run-id", "rd_013",
        "--out-root", tmp_path / "out",
        "--continuation-direction-packet", packet_fixture(tmp_path),
        "--continuation-direction-vectors", bad_vectors,
        "--authorize-larql-continuation-rank1-delta-design",
    )
    assert result.returncode != 0
    assert "input/output direction norms are not approximately 1.0" in result.stdout


def test_rank1_design_outputs(tmp_path):
    packet = packet_fixture(tmp_path)
    vectors = vectors_fixture(tmp_path)
    write_json(
        tmp_path / "capture.json",
        {
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
            "target_module": "model.layers.0.mlp.down_proj",
            "target_module_family": "mlp_projection",
        },
    )
    record = MODULE.write_continuation_rank1_delta_design(
        run_id="rd_014",
        out_root=tmp_path / "out",
        continuation_direction_packet=packet,
        continuation_direction_vectors=vectors,
        delta_scale=1e-2,
        authorize_larql_continuation_rank1_delta_design=True,
    )
    out_dir = tmp_path / "out" / "rd_014"
    assert (out_dir / "larql_continuation_rank1_delta_design_record.json").exists()
    assert (out_dir / "continuation_rank1_delta_design_packet.json").exists()
    assert (out_dir / "continuation_rank1_delta_design_review_packet.md").exists()
    assert record["proposed_delta_shape"] == [2, 3]
    assert abs(record["expected_delta_frobenius_norm"] - 1e-2) < 1e-9
    assert record["recommended_next_step"] == "continuation_rank1_delta_artifact"
    assert record["required_next_step"] == "supervised_continuation_rank1_delta_design_review"
    assert record["model_inference_performed"] is False
    assert record["generation_performed"] is False
    assert record["training_performed"] is False
    assert record["delta_artifact_written"] is False
    assert record["patched_model_materialized"] is False
    assert record["promotion_authorized"] is False
    assert record["automatic_failure_to_curriculum_capture_authorized"] is False
    assert len(record["continuation_output_direction_sha256"]) == 64
    assert len(record["continuation_input_direction_sha256"]) == 64


def test_hashes_and_capture_record_checks(tmp_path):
    packet = packet_fixture(tmp_path)
    vectors = vectors_fixture(tmp_path)
    capture = write_json(
        tmp_path / "capture.json",
        {
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
            "target_module": "model.layers.0.mlp.down_proj",
            "target_module_family": "mlp_projection",
        },
    )
    record = MODULE.write_continuation_rank1_delta_design(
        run_id="rd_015",
        out_root=tmp_path / "out",
        continuation_direction_packet=packet,
        continuation_direction_vectors=vectors,
        delta_scale=1e-2,
        authorize_larql_continuation_rank1_delta_design=True,
    )
    assert record["continuation_output_direction_sha256"]
    assert record["continuation_input_direction_sha256"]
    assert record["recommended_next_step"] == "continuation_rank1_delta_artifact"
    assert record["required_next_step"] == "supervised_continuation_rank1_delta_design_review"


def test_no_inference_or_training_in_source():
    script_text = SCRIPT.read_text(encoding="utf-8")
    assert "generate(" not in script_text
    assert "from transformers import" not in script_text[:1200]
