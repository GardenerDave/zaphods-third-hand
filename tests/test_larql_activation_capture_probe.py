from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/larql_activation_capture_probe.py"


def write_json(path: Path, payload: dict | list) -> Path:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def correction_delta_plan_payload() -> dict:
    return {
        "report_type": "larql_correction_delta_plan.v0",
        "run_id": "larql_correction_delta_plan_001",
        "source_reaudition_path": ".work/fake/reaudition.json",
        "source_reaudition_status": "completed_model_comparison",
        "source_outputs_equal_count": 4,
        "source_normalized_outputs_equal_count": 4,
        "behavioral_improvement_observed": False,
        "planning_authorized": True,
        "model_inference_performed": False,
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
        "required_next_step": "supervised_correction_delta_plan_review",
    }


def selection_plan_payload() -> dict:
    return {
        "recommended_method": "activation_difference_direction",
        "target_module": "model.layers.0.mlp.down_proj.weight",
        "target_layer": "0",
        "target_module_family": "mlp_projection",
        "selection_reason": "bounded first experiment",
        "authorizes_model_inference_now": False,
        "authorizes_weight_edit_now": False,
        "authorizes_delta_artifact_now": False,
        "required_next_step": "implement_authorized_activation_capture_probe",
    }


def probe_pairs_payload() -> list[dict]:
    return [
        {
            "probe_id": "original_larql_behavior_replay",
            "failure_prompt": "failure one",
            "correction_prompt": "correction one",
            "expected_failure_shape": "bad",
            "expected_correction_shape": "good",
            "target_behavior": "bounded",
            "must_not_authorize_install": True,
            "must_not_authorize_registry_mutation": True,
            "must_not_expand_scope_without_review": True,
            "regression_guard": False,
        },
        {
            "probe_id": "adjacent_file_anti_overfit",
            "failure_prompt": "failure two",
            "correction_prompt": "correction two",
            "expected_failure_shape": "bad",
            "expected_correction_shape": "good",
            "target_behavior": "bounded",
            "must_not_authorize_install": True,
            "must_not_authorize_registry_mutation": True,
            "must_not_expand_scope_without_review": True,
            "regression_guard": False,
        },
        {
            "probe_id": "all_files_authorized_control",
            "failure_prompt": "failure three",
            "correction_prompt": "correction three",
            "expected_failure_shape": "bad",
            "expected_correction_shape": "good",
            "target_behavior": "bounded",
            "must_not_authorize_install": True,
            "must_not_authorize_registry_mutation": True,
            "must_not_expand_scope_without_review": True,
            "regression_guard": False,
        },
        {
            "probe_id": "unrelated_task_regression",
            "failure_prompt": "failure four",
            "correction_prompt": "correction four",
            "expected_failure_shape": "bad",
            "expected_correction_shape": "good",
            "target_behavior": "bounded",
            "must_not_authorize_install": True,
            "must_not_authorize_registry_mutation": True,
            "must_not_expand_scope_without_review": False,
            "regression_guard": True,
        },
    ]


def prepare_plan_dir(tmp_path: Path) -> Path:
    plan_dir = tmp_path / "plan"
    plan_dir.mkdir()
    write_json(plan_dir / "larql_correction_delta_plan.json", correction_delta_plan_payload())
    write_json(plan_dir / "delta_selection_plan.json", selection_plan_payload())
    write_json(plan_dir / "activation_contrast_probe_pairs.json", probe_pairs_payload())
    return plan_dir


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
    plan_dir = prepare_plan_dir(tmp_path)
    out_root = tmp_path / "out"
    result = run_script(
        "--run-id", "capture_001",
        "--out-root", out_root,
        "--correction-delta-plan", plan_dir / "larql_correction_delta_plan.json",
    )
    assert result.returncode != 0
    assert "requires explicit opt-in authorization" in result.stdout
    assert not (out_root / "capture_001/larql_activation_capture_probe.json").exists()


def test_packet_only_authorized_run_writes_four_packet_files(tmp_path):
    plan_dir = prepare_plan_dir(tmp_path)
    out_root = tmp_path / "out"
    result = run_script(
        "--run-id", "capture_002",
        "--out-root", out_root,
        "--correction-delta-plan", plan_dir / "larql_correction_delta_plan.json",
        "--authorize-larql-activation-capture-probe",
    )
    assert result.returncode == 0
    out_dir = out_root / "capture_002"
    for name in [
        "larql_activation_capture_probe.json",
        "activation_capture_plan.json",
        "activation_capture_boundary.md",
        "activation_capture_review_packet.md",
    ]:
        assert (out_dir / name).exists()


def test_packet_only_run_does_not_require_torch_or_transformers(tmp_path):
    plan_dir = prepare_plan_dir(tmp_path)
    out_root = tmp_path / "out"
    result = run_script(
        "--run-id", "capture_003",
        "--out-root", out_root,
        "--correction-delta-plan", plan_dir / "larql_correction_delta_plan.json",
        "--authorize-larql-activation-capture-probe",
    )
    assert result.returncode == 0


def test_packet_plan_records_default_prompt_forward_mode(tmp_path):
    plan_dir = prepare_plan_dir(tmp_path)
    out_root = tmp_path / "out"
    run_script(
        "--run-id", "capture_003b",
        "--out-root", out_root,
        "--correction-delta-plan", plan_dir / "larql_correction_delta_plan.json",
        "--authorize-larql-activation-capture-probe",
    )
    plan = json.loads((out_root / "capture_003b/activation_capture_plan.json").read_text(encoding="utf-8"))
    assert plan["default_capture_mode"] == "prompt_forward"


def test_activation_capture_plan_includes_available_modes_and_audit_role(tmp_path):
    plan_dir = prepare_plan_dir(tmp_path)
    out_root = tmp_path / "out"
    run_script(
        "--run-id", "capture_003c",
        "--out-root", out_root,
        "--correction-delta-plan", plan_dir / "larql_correction_delta_plan.json",
        "--authorize-larql-activation-capture-probe",
    )
    plan = json.loads((out_root / "capture_003c/activation_capture_plan.json").read_text(encoding="utf-8"))
    assert plan["available_capture_modes"] == ["prompt_forward", "generation_step"]
    assert plan["generation_output_role"] == "audit_text_only"
    assert plan["delta_evidence_source"] == "prompt_side_activation"


def test_packet_json_has_required_boundary_fields(tmp_path):
    plan_dir = prepare_plan_dir(tmp_path)
    out_root = tmp_path / "out"
    run_script(
        "--run-id", "capture_004",
        "--out-root", out_root,
        "--correction-delta-plan", plan_dir / "larql_correction_delta_plan.json",
        "--authorize-larql-activation-capture-probe",
    )
    payload = json.loads((out_root / "capture_004/larql_activation_capture_probe.json").read_text(encoding="utf-8"))
    assert payload["report_type"] == "larql_activation_capture_probe.v0"
    assert payload["larql_core_path"] is True
    assert payload["model_inference_performed"] is False
    assert payload["activation_records_written"] is False
    assert payload["activation_summary_written"] is False
    assert payload["weight_edit_performed"] is False
    assert payload["delta_artifact_written"] is False
    assert payload["patched_model_materialized"] is False
    assert payload["training_performed"] is False
    assert payload["adapter_baseline_path"] is False
    assert payload["promotion_authorized"] is False
    assert payload["automatic_failure_to_curriculum_capture_authorized"] is False
    assert payload["capture_mode"] == "prompt_forward"


def test_inference_requested_without_model_authorization_is_blocked_and_writes_no_activation_records(tmp_path):
    plan_dir = prepare_plan_dir(tmp_path)
    out_root = tmp_path / "out"
    result = run_script(
        "--run-id", "capture_005",
        "--out-root", out_root,
        "--correction-delta-plan", plan_dir / "larql_correction_delta_plan.json",
        "--authorize-larql-activation-capture-probe",
        "--run-inference",
    )
    assert result.returncode != 0
    out_dir = out_root / "capture_005"
    assert not (out_dir / "activation_records.jsonl").exists()
    assert not (out_dir / "activation_summary.json").exists()


def test_compact_vector_writing_without_authorization_is_blocked(tmp_path):
    plan_dir = prepare_plan_dir(tmp_path)
    out_root = tmp_path / "out"
    base_model = tmp_path / "base_model"
    base_model.mkdir()
    result = run_script(
        "--run-id", "capture_005b",
        "--out-root", out_root,
        "--correction-delta-plan", plan_dir / "larql_correction_delta_plan.json",
        "--base-model-path", base_model,
        "--authorize-larql-activation-capture-probe",
        "--run-inference",
        "--authorize-model-inference",
        "--write-compact-vectors",
    )
    assert result.returncode != 0
    assert "compact vector artifact writing requires explicit authorization" in result.stdout
    assert not (out_root / "capture_005b/compact_prompt_vectors.jsonl").exists()


def test_missing_model_stack_with_inference_authorization_is_blocked_cleanly(tmp_path, monkeypatch):
    from local_harness import larql_activation_capture_probe as mod

    plan_dir = prepare_plan_dir(tmp_path)
    out_root = tmp_path / "out"
    monkeypatch.setattr(mod, "inference_stack_available", lambda: False)
    record = mod.write_probe(
        run_id="capture_006",
        out_root=out_root,
        correction_delta_plan_path=plan_dir / "larql_correction_delta_plan.json",
        base_model_path=tmp_path / "missing_model",
        target_module=None,
        target_layer=None,
        target_module_family=None,
        probe_pairs_path=None,
        authorize_larql_activation_capture_probe=True,
        run_inference=True,
        authorize_model_inference=True,
    )
    assert record["source_plan_status"] == "blocked_missing_model_stack"
    assert record["model_inference_performed"] is False
    assert record["activation_records_written"] is False
    assert record["activation_summary_written"] is False


def test_compact_vectors_only_allowed_in_prompt_forward_mode(tmp_path):
    plan_dir = prepare_plan_dir(tmp_path)
    out_root = tmp_path / "out"
    base_model = tmp_path / "base_model"
    base_model.mkdir()
    result = run_script(
        "--run-id", "capture_006b",
        "--out-root", out_root,
        "--correction-delta-plan", plan_dir / "larql_correction_delta_plan.json",
        "--base-model-path", base_model,
        "--authorize-larql-activation-capture-probe",
        "--run-inference",
        "--authorize-model-inference",
        "--capture-mode", "generation_step",
        "--write-compact-vectors",
        "--authorize-compact-vector-artifact",
    )
    assert result.returncode != 0
    assert "compact vectors are only allowed in prompt_forward mode" in result.stdout
    assert not (out_root / "capture_006b/compact_prompt_vectors.jsonl").exists()


def test_module_name_normalization_strips_trailing_weight():
    from local_harness.larql_activation_capture_probe import normalize_module_name

    assert normalize_module_name("model.layers.0.mlp.down_proj.weight") == "model.layers.0.mlp.down_proj"
    assert normalize_module_name("model.layers.0.mlp.down_proj") == "model.layers.0.mlp.down_proj"


def test_prompt_side_summary_for_batch_seq_hidden_returns_last_token_and_mean_pool():
    from local_harness.larql_activation_capture_probe import summarize_prompt_side_vectors

    stats = summarize_prompt_side_vectors(
        [[[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]]],
        dtype="mock_float",
    )
    assert stats["activation_shape"] == [1, 3, 2]
    assert stats["activation_dtype"] == "mock_float"
    assert stats["prompt_sequence_length"] == 3
    assert isinstance(stats["prompt_last_token_norm"], float)
    assert isinstance(stats["prompt_mean_pool_norm"], float)


def test_prompt_side_summary_for_batch_hidden_treats_as_both_last_token_and_mean_pool():
    from local_harness.larql_activation_capture_probe import summarize_prompt_side_vectors

    stats = summarize_prompt_side_vectors([[1.0, 2.0, 3.0]], dtype="mock_float")
    assert stats["activation_shape"] == [1, 3]
    assert stats["prompt_sequence_length"] == 1
    assert stats["prompt_last_token_norm"] == stats["prompt_mean_pool_norm"]
    assert stats["prompt_last_token_mean"] == stats["prompt_mean_pool_mean"]


def test_per_probe_comparison_helper_computes_norms_and_cosine():
    from local_harness.larql_activation_capture_probe import compare_probe_pair

    failure = {
        "probe_id": "p1",
        "prompt_side_activation_captured": True,
        "prompt_last_token_norm": 2.0,
        "prompt_mean_pool_norm": 1.0,
        "prompt_sequence_length": 3,
        "_prompt_last_token_vector": [1.0, 0.0],
        "_prompt_mean_pool_vector": [0.5, 0.5],
    }
    correction = {
        "probe_id": "p1",
        "prompt_side_activation_captured": True,
        "prompt_last_token_norm": 3.0,
        "prompt_mean_pool_norm": 2.0,
        "prompt_sequence_length": 4,
        "_prompt_last_token_vector": [0.0, 1.0],
        "_prompt_mean_pool_vector": [0.5, -0.5],
    }
    result = compare_probe_pair(failure, correction)
    assert result["prompt_last_token_norm_difference"] == 1.0
    assert result["prompt_mean_pool_norm_difference"] == 1.0
    assert result["prompt_sequence_length_difference"] == 1
    assert isinstance(result["prompt_last_token_cosine_similarity"], float)
    assert isinstance(result["prompt_mean_pool_cosine_similarity"], float)


def test_summary_classifier_detects_prompt_signal():
    from local_harness.larql_activation_capture_probe import classify_prompt_signal

    result = classify_prompt_signal(
        [
            {"evidence_quality": "usable_prompt_signal"},
            {"evidence_quality": "usable_prompt_signal"},
            {"evidence_quality": "unclear_prompt_signal"},
        ]
    )
    assert result["selected_candidate_direction_status"] == "prompt_signal_detected"


def test_summary_classifier_returns_unclear_when_no_usable_signals():
    from local_harness.larql_activation_capture_probe import classify_prompt_signal

    result = classify_prompt_signal(
        [
            {"evidence_quality": "unclear_prompt_signal"},
            {"evidence_quality": "failed_prompt_capture"},
        ]
    )
    assert result["selected_candidate_direction_status"] == "prompt_signal_unclear"


def test_prompt_forward_records_include_activation_source_and_audit_role(tmp_path, monkeypatch):
    from local_harness import larql_activation_capture_probe as mod

    plan_dir = prepare_plan_dir(tmp_path)
    out_root = tmp_path / "out"
    base_model = tmp_path / "base_model"
    base_model.mkdir()
    monkeypatch.setattr(mod, "inference_stack_available", lambda: True)

    def fake_capture(**kwargs):
        kwargs["records_path"].write_text(
            json.dumps(
                {
                    "probe_id": "original_larql_behavior_replay",
                    "side": "failure",
                    "target_module": "model.layers.0.mlp.down_proj.weight",
                    "target_layer": "0",
                    "activation_shape": [1, 3, 2],
                    "activation_dtype": "mock_float",
                    "activation_norm": 1.0,
                    "activation_mean": 0.0,
                    "activation_std": 1.0,
                    "activation_abs_max": 1.0,
                    "capture_mode": "prompt_forward",
                    "activation_source": "prompt_forward",
                    "generation_output_role": "audit_text_only",
                    "delta_evidence_source": "prompt_side_activation",
                    "prompt_side_activation_captured": True,
                    "generation_step_activation_captured": False,
                    "prompt_sequence_length": 3,
                    "prompt_last_token_norm": 1.0,
                    "prompt_last_token_mean": 0.0,
                    "prompt_last_token_std": 1.0,
                    "prompt_last_token_abs_max": 1.0,
                    "prompt_mean_pool_norm": 1.0,
                    "prompt_mean_pool_mean": 0.0,
                    "prompt_mean_pool_std": 1.0,
                    "prompt_mean_pool_abs_max": 1.0,
                    "prompt_token_count": 5,
                    "model_output_text": "audit",
                    "raw_output_preserved": True,
                }
            )
            + "\n",
            encoding="utf-8",
        )
        kwargs["summary_path"].write_text(
            json.dumps(
                {
                    "selected_candidate_direction_status": "prompt_signal_detected",
                    "delta_artifact_recommended": False,
                    "required_next_step": "supervised_activation_capture_review",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        return True, True

    monkeypatch.setattr(mod, "perform_activation_capture", fake_capture)
    record = mod.write_probe(
        run_id="capture_010",
        out_root=out_root,
        correction_delta_plan_path=plan_dir / "larql_correction_delta_plan.json",
        base_model_path=base_model,
        target_module=None,
        target_layer=None,
        target_module_family=None,
        probe_pairs_path=None,
        authorize_larql_activation_capture_probe=True,
        run_inference=True,
        authorize_model_inference=True,
        capture_mode="prompt_forward",
    )
    assert record["prompt_side_activation_captured"] is True
    assert record["generation_step_activation_captured"] is False
    row = json.loads((out_root / "capture_010/activation_records.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert row["activation_source"] == "prompt_forward"
    assert row["generation_output_role"] == "audit_text_only"
    assert row["delta_evidence_source"] == "prompt_side_activation"


def test_authorized_prompt_forward_compact_vector_run_writes_compact_vectors(tmp_path, monkeypatch):
    from local_harness import larql_activation_capture_probe as mod

    plan_dir = prepare_plan_dir(tmp_path)
    out_root = tmp_path / "out"
    base_model = tmp_path / "base_model"
    base_model.mkdir()
    monkeypatch.setattr(mod, "inference_stack_available", lambda: True)

    def fake_capture(**kwargs):
        kwargs["records_path"].write_text(
            json.dumps(
                {
                    "probe_id": "original_larql_behavior_replay",
                    "side": "failure",
                    "target_module": "model.layers.0.mlp.down_proj.weight",
                    "target_layer": "0",
                    "activation_shape": [1, 3, 2],
                    "activation_dtype": "float32",
                    "activation_norm": 1.0,
                    "activation_mean": 0.0,
                    "activation_std": 1.0,
                    "activation_abs_max": 1.0,
                    "capture_mode": "prompt_forward",
                    "activation_source": "prompt_forward",
                    "generation_output_role": "audit_text_only",
                    "delta_evidence_source": "prompt_side_activation",
                    "prompt_side_activation_captured": True,
                    "generation_step_activation_captured": False,
                    "prompt_sequence_length": 3,
                    "prompt_last_token_norm": 1.0,
                    "prompt_last_token_mean": 0.0,
                    "prompt_last_token_std": 1.0,
                    "prompt_last_token_abs_max": 1.0,
                    "prompt_mean_pool_norm": 1.0,
                    "prompt_mean_pool_mean": 0.0,
                    "prompt_mean_pool_std": 1.0,
                    "prompt_mean_pool_abs_max": 1.0,
                    "prompt_token_count": 5,
                    "model_output_text": "audit",
                    "raw_output_preserved": True,
                }
            )
            + "\n",
            encoding="utf-8",
        )
        kwargs["summary_path"].write_text(
            json.dumps(
                {
                    "selected_candidate_direction_status": "prompt_signal_detected",
                    "delta_artifact_recommended": False,
                    "required_next_step": "supervised_activation_capture_review",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        kwargs["compact_vectors_path"].write_text(
            json.dumps(
                {
                    "probe_id": "original_larql_behavior_replay",
                    "side": "failure",
                    "target_module": "model.layers.0.mlp.down_proj.weight",
                    "target_layer": "0",
                    "target_module_family": "mlp_projection",
                    "capture_mode": "prompt_forward",
                    "vector_dtype": "float32",
                    "prompt_sequence_length": 3,
                    "vector_length": 2,
                    "prompt_last_token_vector": [0.25, -0.25],
                    "prompt_mean_pool_vector": [0.5, -0.5],
                    "raw_output_preserved": True,
                    "model_output_text_sha256": "abc123",
                    "generation_output_role": "audit_text_only",
                    "delta_evidence_source": "prompt_side_activation",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        assert kwargs["write_compact_vectors_enabled"] is True
        return True, True, True

    monkeypatch.setattr(mod, "perform_activation_capture", fake_capture)
    record = mod.write_probe(
        run_id="capture_010b",
        out_root=out_root,
        correction_delta_plan_path=plan_dir / "larql_correction_delta_plan.json",
        base_model_path=base_model,
        target_module=None,
        target_layer=None,
        target_module_family=None,
        probe_pairs_path=None,
        authorize_larql_activation_capture_probe=True,
        run_inference=True,
        authorize_model_inference=True,
        capture_mode="prompt_forward",
        write_compact_vectors_requested=True,
        authorize_compact_vector_artifact=True,
    )
    assert record["compact_vectors_requested"] is True
    assert record["compact_vectors_authorized"] is True
    assert record["compact_vectors_written"] is True
    row = json.loads((out_root / "capture_010b/compact_prompt_vectors.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert row["prompt_last_token_vector"] == [0.25, -0.25]
    assert row["prompt_mean_pool_vector"] == [0.5, -0.5]
    assert row["vector_length"] == 2
    assert "activation_shape" not in row
    assert "full_sequence_tensor" not in row


def test_successful_generation_step_mocked_run_reports_generation_flags(tmp_path, monkeypatch):
    from local_harness import larql_activation_capture_probe as mod

    plan_dir = prepare_plan_dir(tmp_path)
    out_root = tmp_path / "out"
    base_model = tmp_path / "base_model"
    base_model.mkdir()
    monkeypatch.setattr(mod, "inference_stack_available", lambda: True)

    def fake_capture(**kwargs):
        kwargs["records_path"].write_text(
            json.dumps(
                {
                    "probe_id": "original_larql_behavior_replay",
                    "side": "failure",
                    "target_module": "model.layers.0.mlp.down_proj.weight",
                    "target_layer": "0",
                    "activation_shape": [1, 1, 2048],
                    "activation_dtype": "mock_float",
                    "activation_norm": 1.0,
                    "activation_mean": 0.0,
                    "activation_std": 1.0,
                    "activation_abs_max": 1.0,
                    "capture_mode": "generation_step",
                    "activation_source": "generation_step",
                    "generation_output_role": "activation_source",
                    "delta_evidence_source": "generation_step_activation",
                    "prompt_side_activation_captured": False,
                    "generation_step_activation_captured": True,
                    "prompt_sequence_length": 1,
                    "prompt_last_token_norm": 1.0,
                    "prompt_last_token_mean": 0.0,
                    "prompt_last_token_std": 1.0,
                    "prompt_last_token_abs_max": 1.0,
                    "prompt_mean_pool_norm": 1.0,
                    "prompt_mean_pool_mean": 0.0,
                    "prompt_mean_pool_std": 1.0,
                    "prompt_mean_pool_abs_max": 1.0,
                    "prompt_token_count": 5,
                    "model_output_text": "audit",
                    "raw_output_preserved": True,
                }
            )
            + "\n",
            encoding="utf-8",
        )
        kwargs["summary_path"].write_text(
            json.dumps(
                {
                    "selected_candidate_direction_status": "prompt_signal_unclear",
                    "delta_artifact_recommended": False,
                    "required_next_step": "supervised_activation_capture_review",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        return True, True

    monkeypatch.setattr(mod, "perform_activation_capture", fake_capture)
    record = mod.write_probe(
        run_id="capture_011",
        out_root=out_root,
        correction_delta_plan_path=plan_dir / "larql_correction_delta_plan.json",
        base_model_path=base_model,
        target_module=None,
        target_layer=None,
        target_module_family=None,
        probe_pairs_path=None,
        authorize_larql_activation_capture_probe=True,
        run_inference=True,
        authorize_model_inference=True,
        capture_mode="generation_step",
    )
    assert record["prompt_side_activation_captured"] is False
    assert record["generation_step_activation_captured"] is True


def test_compact_vector_fields_remain_unwritten_without_authorized_compact_vector_run(tmp_path, monkeypatch):
    from local_harness import larql_activation_capture_probe as mod

    plan_dir = prepare_plan_dir(tmp_path)
    out_root = tmp_path / "out"
    base_model = tmp_path / "base_model"
    base_model.mkdir()
    monkeypatch.setattr(mod, "inference_stack_available", lambda: True)

    def fake_capture(**kwargs):
        kwargs["records_path"].write_text("{}\n", encoding="utf-8")
        kwargs["summary_path"].write_text("{}\n", encoding="utf-8")
        return True, True, False

    monkeypatch.setattr(mod, "perform_activation_capture", fake_capture)
    record = mod.write_probe(
        run_id="capture_011b",
        out_root=out_root,
        correction_delta_plan_path=plan_dir / "larql_correction_delta_plan.json",
        base_model_path=base_model,
        target_module=None,
        target_layer=None,
        target_module_family=None,
        probe_pairs_path=None,
        authorize_larql_activation_capture_probe=True,
        run_inference=True,
        authorize_model_inference=True,
        capture_mode="prompt_forward",
    )
    assert record["compact_vectors_written"] is False
    assert record["compact_vectors_path"] is None
    assert record["promotion_authorized"] is False
    assert record["automatic_failure_to_curriculum_capture_authorized"] is False


def test_prompt_forward_capture_isolated_from_audit_generation():
    from local_harness import larql_activation_capture_probe as mod

    class FakeTensor:
        def __init__(self, data):
            self._data = data

        @property
        def shape(self):
            if isinstance(self._data[0], list) and isinstance(self._data[0][0], list):
                return (len(self._data), len(self._data[0]), len(self._data[0][0]))
            if isinstance(self._data[0], list):
                return (len(self._data), len(self._data[0]))
            return (len(self._data),)

        def detach(self):
            return self

        def float(self):
            return self

        def cpu(self):
            return self

        def clone(self):
            return FakeTensor(json.loads(json.dumps(self._data)))

        def tolist(self):
            return json.loads(json.dumps(self._data))

        @property
        def dtype(self):
            return "mock_float"

    class FakeHandle:
        def __init__(self, module):
            self.module = module

        def remove(self):
            self.module.hook = None

    class FakeModule:
        def __init__(self):
            self.hook = None

        def register_forward_hook(self, hook):
            self.hook = hook
            return FakeHandle(self)

    class FakeModel:
        def __init__(self):
            self.module = FakeModule()

        def __call__(self, **inputs):
            if self.module.hook:
                self.module.hook(None, None, FakeTensor([[[1.0, 2.0], [3.0, 4.0]]]))

    fake_model = FakeModel()
    inputs = {"input_ids": object()}
    capture = mod.capture_prompt_forward_activation(
        model=fake_model,
        inputs=inputs,
        module_obj=fake_model.module,
    )
    # Simulate generation-side activity after prompt capture; it must not alter the stored capture.
    if fake_model.module.hook:
        fake_model.module.hook(None, None, FakeTensor([[[100.0, 200.0]]]))
    stats = mod.summarize_prompt_side_vectors(capture["tensor"].tolist(), dtype=capture["dtype"])
    assert stats["prompt_last_token_mean"] == 3.5
    assert stats["prompt_mean_pool_mean"] == 2.5


def test_no_real_inference_is_run_in_tests():
    script_text = SCRIPT.read_text(encoding="utf-8")
    assert "AutoModelForCausalLM" in script_text
