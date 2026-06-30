from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/larql_delta_design_packet.py"


def write_json(path: Path, payload: dict | list) -> Path:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def activation_capture_record_payload() -> dict:
    return {
        "report_type": "larql_activation_capture_probe.v0",
        "capture_mode": "prompt_forward",
        "compact_vectors_written": True,
        "larql_core_path": True,
        "adapter_baseline_path": False,
    }


def direction_packet_payload(*, selected_source: str = "prompt_mean_pool", status: str = "direction_candidate_reviewable") -> dict:
    return {
        "report_type": "larql_prompt_activation_direction_packet.v0",
        "direction_candidate_status": status,
        "recommended_vector_source": selected_source,
        "target_module": "model.layers.0.mlp.down_proj.weight",
        "target_layer": "0",
        "target_module_family": "mlp_projection",
        "delta_artifact_recommended": False,
    }


def coherence_payload() -> dict:
    return {
        "selection_rule": "max_positive_coherence_margin",
        "file_scope_mean_pool_mean_cosine": 0.73,
        "regression_vs_file_scope_mean_pool_cosine": 0.21,
    }


def compact_rows(*, missing_input: bool = False) -> list[dict]:
    rows = []
    probe_specs = {
        "original_larql_behavior_replay": {
            "failure_out": [0.0, 0.0],
            "correction_out": [1.0, 0.0],
            "failure_in": [1.0, 0.0, 0.0],
        },
        "adjacent_file_anti_overfit": {
            "failure_out": [0.0, 0.0],
            "correction_out": [0.8, 0.2],
            "failure_in": [0.8, 0.1, 0.1],
        },
        "all_files_authorized_control": {
            "failure_out": [0.0, 0.0],
            "correction_out": [0.9, 0.1],
            "failure_in": [0.9, 0.0, 0.1],
        },
        "unrelated_task_regression": {
            "failure_out": [0.0, 0.0],
            "correction_out": [0.1, 1.0],
            "failure_in": [0.0, 1.0, 0.0],
        },
    }
    for probe_id, spec in probe_specs.items():
        rows.append(
            {
                "probe_id": probe_id,
                "side": "failure",
                "target_module": "model.layers.0.mlp.down_proj.weight",
                "target_layer": "0",
                "target_module_family": "mlp_projection",
                "capture_mode": "prompt_forward",
                "vector_dtype": "float32",
                "vector_length": 2,
                "prompt_last_token_vector": spec["failure_out"],
                "prompt_mean_pool_vector": spec["failure_out"],
                "input_vector_dtype": "float32",
                "input_vector_length": 3,
                "prompt_last_token_input_vector": spec["failure_in"] if not missing_input else None,
                "prompt_mean_pool_input_vector": spec["failure_in"] if not missing_input else None,
            }
        )
        rows.append(
            {
                "probe_id": probe_id,
                "side": "correction",
                "target_module": "model.layers.0.mlp.down_proj.weight",
                "target_layer": "0",
                "target_module_family": "mlp_projection",
                "capture_mode": "prompt_forward",
                "vector_dtype": "float32",
                "vector_length": 2,
                "prompt_last_token_vector": spec["correction_out"],
                "prompt_mean_pool_vector": spec["correction_out"],
                "input_vector_dtype": "float32",
                "input_vector_length": 3,
                "prompt_last_token_input_vector": spec["failure_in"] if not missing_input else None,
                "prompt_mean_pool_input_vector": spec["failure_in"] if not missing_input else None,
            }
        )
    return rows


def prepare_inputs(
    tmp_path: Path,
    *,
    missing_input: bool = False,
    selected_source: str = "prompt_mean_pool",
    status: str = "direction_candidate_reviewable",
) -> tuple[Path, Path, Path, Path]:
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    capture = write_json(input_dir / "larql_activation_capture_probe.json", activation_capture_record_payload())
    direction = write_json(input_dir / "larql_prompt_activation_direction_packet.json", direction_packet_payload(selected_source=selected_source, status=status))
    coherence = write_json(input_dir / "direction_coherence_report.json", coherence_payload())
    compact = input_dir / "compact_prompt_vectors.jsonl"
    compact.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in compact_rows(missing_input=missing_input)) + "\n",
        encoding="utf-8",
    )
    return capture, direction, coherence, compact


def run_script(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_help_works():
    result = run_script("--help")
    assert result.returncode == 0
    assert "usage:" in result.stdout.lower()


def test_missing_authorization_exits_nonzero_and_writes_no_packet(tmp_path):
    capture, direction, coherence, compact = prepare_inputs(tmp_path)
    out_root = tmp_path / "out"
    result = run_script(
        "--run-id", "delta_001",
        "--out-root", out_root,
        "--compact-vectors", compact,
        "--direction-packet", direction,
        "--direction-coherence-report", coherence,
        "--source-activation-capture-record", capture,
    )
    assert result.returncode != 0
    assert "requires explicit opt-in authorization" in result.stdout
    assert not (out_root / "delta_001/larql_delta_design_packet.json").exists()


def test_valid_fixture_writes_all_packet_files(tmp_path):
    capture, direction, coherence, compact = prepare_inputs(tmp_path)
    out_root = tmp_path / "out"
    result = run_script(
        "--run-id", "delta_002",
        "--out-root", out_root,
        "--compact-vectors", compact,
        "--direction-packet", direction,
        "--direction-coherence-report", coherence,
        "--source-activation-capture-record", capture,
        "--authorize-larql-delta-design-packet",
    )
    assert result.returncode == 0
    out_dir = out_root / "delta_002"
    for name in [
        "larql_delta_design_packet.json",
        "rank1_delta_design.json",
        "delta_design_risk_register.md",
        "delta_design_review_packet.md",
    ]:
        assert (out_dir / name).exists()


def test_packet_computes_rank1_design_shape_and_keeps_boundaries_false(tmp_path):
    capture, direction, coherence, compact = prepare_inputs(tmp_path)
    out_root = tmp_path / "out"
    run_script(
        "--run-id", "delta_003",
        "--out-root", out_root,
        "--compact-vectors", compact,
        "--direction-packet", direction,
        "--direction-coherence-report", coherence,
        "--source-activation-capture-record", capture,
        "--authorize-larql-delta-design-packet",
    )
    payload = json.loads((out_root / "delta_003/larql_delta_design_packet.json").read_text(encoding="utf-8"))
    design = json.loads((out_root / "delta_003/rank1_delta_design.json").read_text(encoding="utf-8"))
    assert payload["report_type"] == "larql_delta_design_packet.v0"
    assert payload["selected_vector_source"] == "prompt_mean_pool"
    assert payload["proposed_delta_shape"] == [2, 3]
    assert payload["delta_design_status"] == "delta_design_reviewable"
    assert payload["model_inference_performed"] is False
    assert payload["weight_edit_performed"] is False
    assert payload["delta_artifact_written"] is False
    assert payload["patched_model_materialized"] is False
    assert payload["training_performed"] is False
    assert payload["adapter_baseline_path"] is False
    assert payload["promotion_authorized"] is False
    assert payload["automatic_failure_to_curriculum_capture_authorized"] is False
    assert payload["delta_artifact_recommended"] is False
    assert design["rank"] == 1
    assert design["writes_tensor_artifact"] is False


def test_missing_input_vectors_is_rejected_or_unclear(tmp_path):
    capture, direction, coherence, compact = prepare_inputs(tmp_path, missing_input=True)
    out_root = tmp_path / "out"
    run_script(
        "--run-id", "delta_004",
        "--out-root", out_root,
        "--compact-vectors", compact,
        "--direction-packet", direction,
        "--direction-coherence-report", coherence,
        "--source-activation-capture-record", capture,
        "--authorize-larql-delta-design-packet",
    )
    payload = json.loads((out_root / "delta_004/larql_delta_design_packet.json").read_text(encoding="utf-8"))
    assert payload["delta_design_status"] in {"delta_design_rejected", "delta_design_unclear"}


def test_selected_source_none_is_rejected(tmp_path):
    capture, direction, coherence, compact = prepare_inputs(tmp_path, selected_source="none")
    out_root = tmp_path / "out"
    run_script(
        "--run-id", "delta_005",
        "--out-root", out_root,
        "--compact-vectors", compact,
        "--direction-packet", direction,
        "--direction-coherence-report", coherence,
        "--source-activation-capture-record", capture,
        "--authorize-larql-delta-design-packet",
    )
    payload = json.loads((out_root / "delta_005/larql_delta_design_packet.json").read_text(encoding="utf-8"))
    assert payload["delta_design_status"] == "delta_design_rejected"


def test_non_reviewable_direction_packet_is_rejected_or_unclear(tmp_path):
    capture, direction, coherence, compact = prepare_inputs(tmp_path, status="direction_candidate_unclear")
    out_root = tmp_path / "out"
    run_script(
        "--run-id", "delta_006",
        "--out-root", out_root,
        "--compact-vectors", compact,
        "--direction-packet", direction,
        "--direction-coherence-report", coherence,
        "--source-activation-capture-record", capture,
        "--authorize-larql-delta-design-packet",
    )
    payload = json.loads((out_root / "delta_006/larql_delta_design_packet.json").read_text(encoding="utf-8"))
    assert payload["delta_design_status"] in {"delta_design_rejected", "delta_design_unclear"}


def test_no_real_inference_or_model_artifacts_are_written():
    script_text = SCRIPT.read_text(encoding="utf-8")
    assert "transformers" not in script_text
    assert "torch" not in script_text
    assert "safetensors" not in script_text
