from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/larql_prompt_activation_direction_packet.py"


def write_json(path: Path, payload: dict | list) -> Path:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def activation_capture_record_payload() -> dict:
    return {
        "report_type": "larql_activation_capture_probe.v0",
        "run_id": "capture_001",
        "source_correction_delta_plan_path": ".work/fake/plan.json",
        "source_plan_status": "completed_model_comparison",
        "selected_method": "activation_difference_direction",
        "target_module": "model.layers.0.mlp.down_proj.weight",
        "target_layer": "0",
        "target_module_family": "mlp_projection",
        "activation_capture_authorized": True,
        "capture_mode": "prompt_forward",
        "prompt_side_activation_captured": True,
        "generation_step_activation_captured": False,
        "model_inference_requested": True,
        "model_inference_performed": True,
        "activation_records_written": True,
        "activation_summary_written": True,
        "compact_vectors_requested": True,
        "compact_vectors_authorized": True,
        "compact_vectors_written": True,
        "compact_vectors_path": ".work/fake/compact_prompt_vectors.jsonl",
        "weight_edit_performed": False,
        "delta_artifact_written": False,
        "patched_model_materialized": False,
        "training_performed": False,
        "adapter_baseline_path": False,
        "larql_core_path": True,
        "promotion_authorized": False,
        "base_model_overwrite_authorized": False,
        "production_deployment_authorized": False,
        "registry_mutation_authorized": False,
        "install_authorized": False,
        "automatic_failure_to_curriculum_capture_authorized": False,
        "required_next_step": "supervised_activation_capture_review",
    }


def activation_summary_payload() -> dict:
    return {
        "selected_candidate_direction_status": "prompt_signal_detected",
        "prompt_last_token_mean_norm_difference": 0.6,
        "prompt_mean_pool_mean_norm_difference": 0.2,
        "prompt_last_token_mean_cosine_similarity": 0.9,
        "prompt_mean_pool_mean_cosine_similarity": 0.75,
        "usable_prompt_signal_count": 4,
        "unclear_prompt_signal_count": 0,
        "failed_prompt_capture_count": 0,
        "delta_artifact_recommended": False,
        "required_next_step": "supervised_activation_capture_review",
    }


def compact_vector_rows(*, use_mean_pool_advantage: bool = False, weak_margins: bool = False) -> list[dict]:
    if weak_margins:
        file_last = [
            [1.0, 0.0, 0.0],
            [0.95, 0.05, 0.0],
            [0.9, 0.1, 0.0],
        ]
        file_mean = [
            [0.8, 0.2, 0.0],
            [0.75, 0.25, 0.0],
            [0.7, 0.3, 0.0],
        ]
        regression_last = [0.98, 0.02, 0.0]
        regression_mean = [0.78, 0.22, 0.0]
    elif use_mean_pool_advantage:
        file_last = [
            [1.0, 0.0, 0.0],
            [0.7, 0.3, 0.0],
            [0.6, 0.4, 0.0],
        ]
        file_mean = [
            [1.0, 0.0, 0.0],
            [0.95, 0.05, 0.0],
            [0.9, 0.1, 0.0],
        ]
        regression_last = [0.5, 0.5, 0.0]
        regression_mean = [0.1, 0.9, 0.0]
    else:
        file_last = [
            [1.0, 0.0, 0.0],
            [0.95, 0.05, 0.0],
            [0.9, 0.1, 0.0],
        ]
        file_mean = [
            [0.8, 0.2, 0.0],
            [0.75, 0.25, 0.0],
            [0.7, 0.3, 0.0],
        ]
        regression_last = [0.1, 1.0, 0.0]
        regression_mean = [0.4, 0.9, 0.0]

    return [
        {
            "probe_id": "original_larql_behavior_replay",
            "side": "failure",
            "target_module": "model.layers.0.mlp.down_proj.weight",
            "target_layer": "0",
            "target_module_family": "mlp_projection",
            "capture_mode": "prompt_forward",
            "vector_dtype": "float32",
            "prompt_sequence_length": 10,
            "vector_length": 3,
            "prompt_last_token_vector": [0.0, 0.0, 0.0],
            "prompt_mean_pool_vector": [0.0, 0.0, 0.0],
            "raw_output_preserved": True,
            "model_output_text_sha256": "a",
            "generation_output_role": "audit_text_only",
            "delta_evidence_source": "prompt_side_activation",
        },
        {
            "probe_id": "original_larql_behavior_replay",
            "side": "correction",
            "target_module": "model.layers.0.mlp.down_proj.weight",
            "target_layer": "0",
            "target_module_family": "mlp_projection",
            "capture_mode": "prompt_forward",
            "vector_dtype": "float32",
            "prompt_sequence_length": 10,
            "vector_length": 3,
            "prompt_last_token_vector": file_last[0],
            "prompt_mean_pool_vector": file_mean[0],
            "raw_output_preserved": True,
            "model_output_text_sha256": "b",
            "generation_output_role": "audit_text_only",
            "delta_evidence_source": "prompt_side_activation",
        },
        {
            "probe_id": "adjacent_file_anti_overfit",
            "side": "failure",
            "prompt_last_token_vector": [0.0, 0.0, 0.0],
            "prompt_mean_pool_vector": [0.0, 0.0, 0.0],
        },
        {
            "probe_id": "adjacent_file_anti_overfit",
            "side": "correction",
            "prompt_last_token_vector": file_last[1],
            "prompt_mean_pool_vector": file_mean[1],
        },
        {
            "probe_id": "all_files_authorized_control",
            "side": "failure",
            "prompt_last_token_vector": [0.0, 0.0, 0.0],
            "prompt_mean_pool_vector": [0.0, 0.0, 0.0],
        },
        {
            "probe_id": "all_files_authorized_control",
            "side": "correction",
            "prompt_last_token_vector": file_last[2],
            "prompt_mean_pool_vector": file_mean[2],
        },
        {
            "probe_id": "unrelated_task_regression",
            "side": "failure",
            "prompt_last_token_vector": [0.0, 0.0, 0.0],
            "prompt_mean_pool_vector": [0.0, 0.0, 0.0],
        },
        {
            "probe_id": "unrelated_task_regression",
            "side": "correction",
            "prompt_last_token_vector": regression_last,
            "prompt_mean_pool_vector": regression_mean,
        },
    ]


def prepare_inputs(
    tmp_path: Path,
    *,
    malformed: bool = False,
    use_mean_pool_advantage: bool = False,
    weak_margins: bool = False,
) -> tuple[Path, Path, Path]:
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    capture = write_json(input_dir / "larql_activation_capture_probe.json", activation_capture_record_payload())
    summary = write_json(input_dir / "activation_summary.json", activation_summary_payload())
    rows = compact_vector_rows(
        use_mean_pool_advantage=use_mean_pool_advantage,
        weak_margins=weak_margins,
    )
    if malformed:
        rows = [dict(row) for row in rows]
        rows[-1]["prompt_mean_pool_vector"] = [1.0, 2.0]
    compact = input_dir / "compact_prompt_vectors.jsonl"
    compact.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )
    return capture, summary, compact


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
    capture, summary, compact = prepare_inputs(tmp_path)
    out_root = tmp_path / "out"
    result = run_script(
        "--run-id", "direction_001",
        "--out-root", out_root,
        "--compact-vectors", compact,
        "--activation-summary", summary,
        "--source-activation-capture-record", capture,
    )
    assert result.returncode != 0
    assert "requires explicit opt-in authorization" in result.stdout
    assert not (out_root / "direction_001/larql_prompt_activation_direction_packet.json").exists()


def test_valid_compact_vector_fixture_writes_all_packet_files(tmp_path):
    capture, summary, compact = prepare_inputs(tmp_path)
    out_root = tmp_path / "out"
    result = run_script(
        "--run-id", "direction_002",
        "--out-root", out_root,
        "--compact-vectors", compact,
        "--activation-summary", summary,
        "--source-activation-capture-record", capture,
        "--authorize-larql-direction-candidate-packet",
    )
    assert result.returncode == 0
    out_dir = out_root / "direction_002"
    for name in [
        "larql_prompt_activation_direction_packet.json",
        "direction_candidates.json",
        "direction_coherence_report.json",
        "direction_risk_register.md",
        "direction_review_packet.md",
    ]:
        assert (out_dir / name).exists()


def test_packet_json_has_required_boundary_fields(tmp_path):
    capture, summary, compact = prepare_inputs(tmp_path)
    out_root = tmp_path / "out"
    run_script(
        "--run-id", "direction_003",
        "--out-root", out_root,
        "--compact-vectors", compact,
        "--activation-summary", summary,
        "--source-activation-capture-record", capture,
        "--authorize-larql-direction-candidate-packet",
    )
    payload = json.loads((out_root / "direction_003/larql_prompt_activation_direction_packet.json").read_text(encoding="utf-8"))
    assert payload["report_type"] == "larql_prompt_activation_direction_packet.v0"
    assert payload["target_module"] == "model.layers.0.mlp.down_proj.weight"
    assert payload["target_layer"] == "0"
    assert payload["target_module_family"] == "mlp_projection"
    assert payload["model_inference_performed"] is False
    assert payload["weight_edit_performed"] is False
    assert payload["delta_artifact_written"] is False
    assert payload["patched_model_materialized"] is False
    assert payload["training_performed"] is False
    assert payload["adapter_baseline_path"] is False
    assert payload["promotion_authorized"] is False
    assert payload["automatic_failure_to_curriculum_capture_authorized"] is False
    assert payload["delta_artifact_recommended"] is False


def test_coherent_fixture_classifies_as_reviewable_and_computes_cosines(tmp_path):
    capture, summary, compact = prepare_inputs(tmp_path)
    out_root = tmp_path / "out"
    run_script(
        "--run-id", "direction_004",
        "--out-root", out_root,
        "--compact-vectors", compact,
        "--activation-summary", summary,
        "--source-activation-capture-record", capture,
        "--authorize-larql-direction-candidate-packet",
    )
    payload = json.loads((out_root / "direction_004/larql_prompt_activation_direction_packet.json").read_text(encoding="utf-8"))
    coherence = json.loads((out_root / "direction_004/direction_coherence_report.json").read_text(encoding="utf-8"))
    candidates = json.loads((out_root / "direction_004/direction_candidates.json").read_text(encoding="utf-8"))
    assert payload["direction_candidate_status"] == "direction_candidate_reviewable"
    assert payload["recommended_vector_source"] == "prompt_last_token"
    assert len(coherence["file_scope_last_token_pairwise_cosines"]) >= 1
    assert len(coherence["file_scope_mean_pool_pairwise_cosines"]) >= 1
    assert coherence["regression_vs_file_scope_last_token_cosine"] is not None
    assert coherence["last_token_coherence_margin"] is not None
    assert coherence["mean_pool_coherence_margin"] is not None
    assert coherence["selection_rule"] == "max_positive_coherence_margin"
    assert {item["probe_id"] for item in candidates["per_probe"]} == {
        "original_larql_behavior_replay",
        "adjacent_file_anti_overfit",
        "all_files_authorized_control",
        "unrelated_task_regression",
    }


def test_mean_pool_higher_coherence_margin_selects_prompt_mean_pool(tmp_path):
    capture, summary, compact = prepare_inputs(tmp_path, use_mean_pool_advantage=True)
    out_root = tmp_path / "out"
    run_script(
        "--run-id", "direction_004b",
        "--out-root", out_root,
        "--compact-vectors", compact,
        "--activation-summary", summary,
        "--source-activation-capture-record", capture,
        "--authorize-larql-direction-candidate-packet",
    )
    payload = json.loads((out_root / "direction_004b/larql_prompt_activation_direction_packet.json").read_text(encoding="utf-8"))
    coherence = json.loads((out_root / "direction_004b/direction_coherence_report.json").read_text(encoding="utf-8"))
    assert payload["direction_candidate_status"] == "direction_candidate_reviewable"
    assert payload["recommended_vector_source"] == "prompt_mean_pool"
    assert coherence["mean_pool_coherence_margin"] > coherence["last_token_coherence_margin"]


def test_weak_or_regression_aligned_margins_return_unclear(tmp_path):
    capture, summary, compact = prepare_inputs(tmp_path, weak_margins=True)
    out_root = tmp_path / "out"
    run_script(
        "--run-id", "direction_004c",
        "--out-root", out_root,
        "--compact-vectors", compact,
        "--activation-summary", summary,
        "--source-activation-capture-record", capture,
        "--authorize-larql-direction-candidate-packet",
    )
    payload = json.loads((out_root / "direction_004c/larql_prompt_activation_direction_packet.json").read_text(encoding="utf-8"))
    coherence = json.loads((out_root / "direction_004c/direction_coherence_report.json").read_text(encoding="utf-8"))
    assert payload["direction_candidate_status"] == "direction_candidate_unclear"
    assert coherence["selection_rule"] == "max_positive_coherence_margin"


def test_malformed_vector_fixture_classifies_as_rejected_or_unclear(tmp_path):
    capture, summary, compact = prepare_inputs(tmp_path, malformed=True)
    out_root = tmp_path / "out"
    run_script(
        "--run-id", "direction_005",
        "--out-root", out_root,
        "--compact-vectors", compact,
        "--activation-summary", summary,
        "--source-activation-capture-record", capture,
        "--authorize-larql-direction-candidate-packet",
    )
    payload = json.loads((out_root / "direction_005/larql_prompt_activation_direction_packet.json").read_text(encoding="utf-8"))
    assert payload["direction_candidate_status"] in {"direction_candidate_rejected", "direction_candidate_unclear"}


def test_no_real_inference_is_run():
    script_text = SCRIPT.read_text(encoding="utf-8")
    assert "transformers" not in script_text
    assert "torch" not in script_text
