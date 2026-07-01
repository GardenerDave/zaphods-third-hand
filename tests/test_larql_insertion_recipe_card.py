from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/larql_insertion_recipe_card.py"
SPEC = importlib.util.spec_from_file_location("larql_insertion_recipe_card", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def write_json(path: Path, payload: dict | list) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def delta_design_packet_fixture(tmp_path: Path, *, mutate: dict | None = None) -> Path:
    payload = {
        "report_type": "larql_delta_design_packet.v0",
        "direction_basis_mode": "target_control_orthogonal",
        "selected_vector_source": "prompt_mean_pool",
        "target_module": "model.layers.0.mlp.down_proj.weight",
        "target_module_family": "mlp_projection",
        "source_vector_target_module": "model.layers.0.mlp.down_proj.weight",
        "source_vector_target_module_family": "mlp_projection",
        "training_performed": False,
        "promotion_authorized": False,
        "registry_mutation_authorized": False,
        "install_authorized": False,
        "automatic_failure_to_curriculum_capture_authorized": False,
    }
    if mutate:
        payload.update(mutate)
    return write_json(tmp_path / "delta_design_packet.json", payload)


def rank1_artifact_record_fixture(tmp_path: Path, *, mutate: dict | None = None) -> Path:
    artifact_path = tmp_path / "rank1_delta.safetensors"
    artifact_path.write_text("delta", encoding="utf-8")
    payload = {
        "report_type": "larql_rank1_delta_artifact.v0",
        "delta_artifact_written": True,
        "target_module": "model.layers.0.mlp.down_proj.weight",
        "target_module_family": "mlp_projection",
        "selected_vector_source": "prompt_mean_pool",
        "direction_basis_mode": "target_control_orthogonal",
        "orthogonalization_applied": True,
        "orthogonalization_strength": 0.25,
        "orthogonalization_side": "output_and_input",
        "target_probe_ids": [
            "original_larql_behavior_replay",
            "adjacent_file_anti_overfit",
        ],
        "control_probe_ids": [
            "all_files_authorized_control",
            "unrelated_task_regression",
        ],
        "control_probe_subset": [
            "all_files_authorized_control",
            "unrelated_task_regression",
        ],
        "delta_scale": 1e-2,
        "delta_shape": [2048, 6144],
        "delta_tensor_norm": 0.01,
        "artifact_sha256": "abc123",
        "artifact_path": str(artifact_path),
        "training_performed": False,
        "promotion_authorized": False,
        "registry_mutation_authorized": False,
        "install_authorized": False,
        "automatic_failure_to_curriculum_capture_authorized": False,
    }
    if mutate:
        payload.update(mutate)
    return write_json(tmp_path / "rank1_delta_artifact_record.json", payload)


def comparison_fixture(tmp_path: Path, name: str, margins: dict[str, float]) -> Path:
    return write_json(
        tmp_path / name / "teacher_forced_likelihood_comparison.json",
        {
            "probes": [
                {"probe_id": probe_id, "margin_delta": value}
                for probe_id, value in margins.items()
            ]
        },
    )


def run_script(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def make_inputs(
    tmp_path: Path,
    *,
    baseline: dict[str, float] | None = None,
    candidate: dict[str, float] | None = None,
    confirmation: dict[str, float] | None = None,
    delta_mutate: dict | None = None,
    artifact_mutate: dict | None = None,
) -> tuple[Path, Path, Path, Path, Path | None]:
    baseline = baseline or {
        "original_larql_behavior_replay": 0.01,
        "adjacent_file_anti_overfit": 0.02,
        "all_files_authorized_control": 0.00,
        "unrelated_task_regression": -0.01,
    }
    candidate = candidate or {
        "original_larql_behavior_replay": 0.03,
        "adjacent_file_anti_overfit": 0.05,
        "all_files_authorized_control": 0.02,
        "unrelated_task_regression": 0.01,
    }
    delta = delta_design_packet_fixture(tmp_path, mutate=delta_mutate)
    artifact = rank1_artifact_record_fixture(tmp_path, mutate=artifact_mutate)
    baseline_path = comparison_fixture(tmp_path, "baseline", baseline)
    candidate_path = comparison_fixture(tmp_path, "candidate", candidate)
    confirmation_path = (
        comparison_fixture(tmp_path, "confirmation", confirmation)
        if confirmation is not None
        else None
    )
    return delta, artifact, baseline_path, candidate_path, confirmation_path


def test_authorization_required(tmp_path):
    delta, artifact, baseline, candidate, _ = make_inputs(tmp_path)
    result = run_script(
        "--run-id", "card_001",
        "--out-root", tmp_path / "out",
        "--recipe-name", "qwen3_file_scope_alpha_025",
        "--behavior-family", "LARQL file-scope authorization correction",
        "--model-name", "Qwen3-1.7B",
        "--base-model-path-or-id", "Qwen/Qwen3-1.7B",
        "--delta-design-packet", delta,
        "--rank1-delta-artifact-record", artifact,
        "--teacher-forced-likelihood-comparison", candidate,
        "--baseline-teacher-forced-likelihood-comparison", baseline,
    )
    assert result.returncode != 0
    assert "requires explicit opt-in authorization" in result.stdout


def test_accepted_candidate_when_all_checks_pass(tmp_path):
    delta, artifact, baseline, candidate, _ = make_inputs(tmp_path)
    card = MODULE.write_insertion_recipe_card(
        run_id="card_002",
        out_root=tmp_path / "out",
        recipe_name="qwen3_file_scope_alpha_025",
        behavior_family="LARQL file-scope authorization correction",
        model_name="Qwen3-1.7B",
        base_model_path_or_id="Qwen/Qwen3-1.7B",
        delta_design_packet_path=delta,
        rank1_delta_artifact_record_path=artifact,
        teacher_forced_likelihood_comparison_path=candidate,
        baseline_teacher_forced_likelihood_comparison_path=baseline,
        confirmation_teacher_forced_likelihood_comparison_path=None,
        author_note=None,
        authorize_larql_insertion_recipe_card=True,
    )
    assert card["recipe_status"] == "accepted_candidate"
    assert (tmp_path / "out/card_002/larql_insertion_recipe_card.json").exists()
    assert (tmp_path / "out/card_002/larql_insertion_recipe_card.md").exists()


def test_rejected_candidate_when_target_mean_does_not_beat_baseline(tmp_path):
    delta, artifact, baseline, candidate, _ = make_inputs(
        tmp_path,
        candidate={
            "original_larql_behavior_replay": 0.005,
            "adjacent_file_anti_overfit": 0.015,
            "all_files_authorized_control": 0.02,
            "unrelated_task_regression": 0.01,
        },
    )
    card = MODULE.write_insertion_recipe_card(
        run_id="card_003",
        out_root=tmp_path / "out",
        recipe_name="bad_target_mean",
        behavior_family="LARQL file-scope authorization correction",
        model_name="Qwen3-1.7B",
        base_model_path_or_id="Qwen/Qwen3-1.7B",
        delta_design_packet_path=delta,
        rank1_delta_artifact_record_path=artifact,
        teacher_forced_likelihood_comparison_path=candidate,
        baseline_teacher_forced_likelihood_comparison_path=baseline,
        confirmation_teacher_forced_likelihood_comparison_path=None,
        author_note=None,
        authorize_larql_insertion_recipe_card=True,
    )
    assert card["recipe_status"] == "rejected_candidate"
    assert "candidate target_mean did not beat baseline" in card["rejection_reasons"]


def test_rejected_candidate_when_target_min_is_negative(tmp_path):
    delta, artifact, baseline, candidate, _ = make_inputs(
        tmp_path,
        candidate={
            "original_larql_behavior_replay": -0.01,
            "adjacent_file_anti_overfit": 0.06,
            "all_files_authorized_control": 0.02,
            "unrelated_task_regression": 0.01,
        },
    )
    card = MODULE.write_insertion_recipe_card(
        run_id="card_004",
        out_root=tmp_path / "out",
        recipe_name="negative_target_min",
        behavior_family="LARQL file-scope authorization correction",
        model_name="Qwen3-1.7B",
        base_model_path_or_id="Qwen/Qwen3-1.7B",
        delta_design_packet_path=delta,
        rank1_delta_artifact_record_path=artifact,
        teacher_forced_likelihood_comparison_path=candidate,
        baseline_teacher_forced_likelihood_comparison_path=baseline,
        confirmation_teacher_forced_likelihood_comparison_path=None,
        author_note=None,
        authorize_larql_insertion_recipe_card=True,
    )
    assert "candidate target_min was not positive" in card["rejection_reasons"]


def test_rejected_candidate_when_control_min_is_worse_than_baseline(tmp_path):
    delta, artifact, baseline, candidate, _ = make_inputs(
        tmp_path,
        candidate={
            "original_larql_behavior_replay": 0.03,
            "adjacent_file_anti_overfit": 0.05,
            "all_files_authorized_control": 0.02,
            "unrelated_task_regression": -0.02,
        },
    )
    card = MODULE.write_insertion_recipe_card(
        run_id="card_005",
        out_root=tmp_path / "out",
        recipe_name="bad_control_min",
        behavior_family="LARQL file-scope authorization correction",
        model_name="Qwen3-1.7B",
        base_model_path_or_id="Qwen/Qwen3-1.7B",
        delta_design_packet_path=delta,
        rank1_delta_artifact_record_path=artifact,
        teacher_forced_likelihood_comparison_path=candidate,
        baseline_teacher_forced_likelihood_comparison_path=baseline,
        confirmation_teacher_forced_likelihood_comparison_path=None,
        author_note=None,
        authorize_larql_insertion_recipe_card=True,
    )
    assert "candidate control_min did not beat baseline" in card["rejection_reasons"]


def test_exact_confirmation_match_recorded_true(tmp_path):
    delta, artifact, baseline, candidate, confirmation = make_inputs(
        tmp_path,
        confirmation={
            "original_larql_behavior_replay": 0.03,
            "adjacent_file_anti_overfit": 0.05,
            "all_files_authorized_control": 0.02,
            "unrelated_task_regression": 0.01,
        },
    )
    card = MODULE.write_insertion_recipe_card(
        run_id="card_006",
        out_root=tmp_path / "out",
        recipe_name="confirm_match",
        behavior_family="LARQL file-scope authorization correction",
        model_name="Qwen3-1.7B",
        base_model_path_or_id="Qwen/Qwen3-1.7B",
        delta_design_packet_path=delta,
        rank1_delta_artifact_record_path=artifact,
        teacher_forced_likelihood_comparison_path=candidate,
        baseline_teacher_forced_likelihood_comparison_path=baseline,
        confirmation_teacher_forced_likelihood_comparison_path=confirmation,
        author_note=None,
        authorize_larql_insertion_recipe_card=True,
    )
    assert card["confirmation_matches_candidate"] is True


def test_confirmation_mismatch_recorded_false_and_rejected(tmp_path):
    delta, artifact, baseline, candidate, confirmation = make_inputs(
        tmp_path,
        confirmation={
            "original_larql_behavior_replay": 0.031,
            "adjacent_file_anti_overfit": 0.05,
            "all_files_authorized_control": 0.02,
            "unrelated_task_regression": 0.01,
        },
    )
    card = MODULE.write_insertion_recipe_card(
        run_id="card_007",
        out_root=tmp_path / "out",
        recipe_name="confirm_mismatch",
        behavior_family="LARQL file-scope authorization correction",
        model_name="Qwen3-1.7B",
        base_model_path_or_id="Qwen/Qwen3-1.7B",
        delta_design_packet_path=delta,
        rank1_delta_artifact_record_path=artifact,
        teacher_forced_likelihood_comparison_path=candidate,
        baseline_teacher_forced_likelihood_comparison_path=baseline,
        confirmation_teacher_forced_likelihood_comparison_path=confirmation,
        author_note=None,
        authorize_larql_insertion_recipe_card=True,
    )
    assert card["confirmation_matches_candidate"] is False
    assert card["recipe_status"] == "rejected_candidate"


def test_missing_required_probe_fails_closed(tmp_path):
    delta, artifact, baseline, candidate, _ = make_inputs(
        tmp_path,
        candidate={
            "original_larql_behavior_replay": 0.03,
            "all_files_authorized_control": 0.02,
            "unrelated_task_regression": 0.01,
        },
    )
    result = run_script(
        "--run-id", "card_008",
        "--out-root", tmp_path / "out",
        "--recipe-name", "missing_probe",
        "--behavior-family", "LARQL file-scope authorization correction",
        "--model-name", "Qwen3-1.7B",
        "--base-model-path-or-id", "Qwen/Qwen3-1.7B",
        "--delta-design-packet", delta,
        "--rank1-delta-artifact-record", artifact,
        "--teacher-forced-likelihood-comparison", candidate,
        "--baseline-teacher-forced-likelihood-comparison", baseline,
        "--authorize-larql-insertion-recipe-card",
    )
    assert result.returncode != 0
    assert "missing required probes" in result.stdout


def test_duplicate_probe_ids_fail_closed(tmp_path):
    delta, artifact, baseline, _, _ = make_inputs(tmp_path)
    dup = write_json(
        tmp_path / "dup" / "teacher_forced_likelihood_comparison.json",
        {
            "probes": [
                {"probe_id": "original_larql_behavior_replay", "margin_delta": 0.1},
                {"probe_id": "original_larql_behavior_replay", "margin_delta": 0.2},
                {"probe_id": "adjacent_file_anti_overfit", "margin_delta": 0.3},
                {"probe_id": "all_files_authorized_control", "margin_delta": 0.1},
                {"probe_id": "unrelated_task_regression", "margin_delta": 0.1},
            ]
        },
    )
    result = run_script(
        "--run-id", "card_009",
        "--out-root", tmp_path / "out",
        "--recipe-name", "dup_probe",
        "--behavior-family", "LARQL file-scope authorization correction",
        "--model-name", "Qwen3-1.7B",
        "--base-model-path-or-id", "Qwen/Qwen3-1.7B",
        "--delta-design-packet", delta,
        "--rank1-delta-artifact-record", artifact,
        "--teacher-forced-likelihood-comparison", dup,
        "--baseline-teacher-forced-likelihood-comparison", baseline,
        "--authorize-larql-insertion-recipe-card",
    )
    assert result.returncode != 0
    assert "duplicate probe id" in result.stdout


def test_missing_artifact_field_fails_closed(tmp_path):
    delta, artifact, baseline, candidate, _ = make_inputs(
        tmp_path,
        artifact_mutate={"artifact_sha256": None},
    )
    result = run_script(
        "--run-id", "card_010",
        "--out-root", tmp_path / "out",
        "--recipe-name", "missing_artifact_field",
        "--behavior-family", "LARQL file-scope authorization correction",
        "--model-name", "Qwen3-1.7B",
        "--base-model-path-or-id", "Qwen/Qwen3-1.7B",
        "--delta-design-packet", delta,
        "--rank1-delta-artifact-record", artifact,
        "--teacher-forced-likelihood-comparison", candidate,
        "--baseline-teacher-forced-likelihood-comparison", baseline,
        "--authorize-larql-insertion-recipe-card",
    )
    assert result.returncode != 0
    assert "missing required field: artifact_sha256" in result.stdout


def test_training_flag_true_fails_closed(tmp_path):
    delta, artifact, baseline, candidate, _ = make_inputs(
        tmp_path,
        artifact_mutate={"training_performed": True},
    )
    result = run_script(
        "--run-id", "card_011",
        "--out-root", tmp_path / "out",
        "--recipe-name", "bad_training",
        "--behavior-family", "LARQL file-scope authorization correction",
        "--model-name", "Qwen3-1.7B",
        "--base-model-path-or-id", "Qwen/Qwen3-1.7B",
        "--delta-design-packet", delta,
        "--rank1-delta-artifact-record", artifact,
        "--teacher-forced-likelihood-comparison", candidate,
        "--baseline-teacher-forced-likelihood-comparison", baseline,
        "--authorize-larql-insertion-recipe-card",
    )
    assert result.returncode != 0
    assert "training_performed must be false" in result.stdout


def test_promotion_flag_true_fails_closed(tmp_path):
    delta, artifact, baseline, candidate, _ = make_inputs(
        tmp_path,
        artifact_mutate={"promotion_authorized": True},
    )
    result = run_script(
        "--run-id", "card_012",
        "--out-root", tmp_path / "out",
        "--recipe-name", "bad_promotion",
        "--behavior-family", "LARQL file-scope authorization correction",
        "--model-name", "Qwen3-1.7B",
        "--base-model-path-or-id", "Qwen/Qwen3-1.7B",
        "--delta-design-packet", delta,
        "--rank1-delta-artifact-record", artifact,
        "--teacher-forced-likelihood-comparison", candidate,
        "--baseline-teacher-forced-likelihood-comparison", baseline,
        "--authorize-larql-insertion-recipe-card",
    )
    assert result.returncode != 0
    assert "promotion_authorized must be false" in result.stdout


def test_automatic_failure_to_curriculum_capture_true_fails_closed(tmp_path):
    delta, artifact, baseline, candidate, _ = make_inputs(
        tmp_path,
        artifact_mutate={"automatic_failure_to_curriculum_capture_authorized": True},
    )
    result = run_script(
        "--run-id", "card_013",
        "--out-root", tmp_path / "out",
        "--recipe-name", "bad_curriculum",
        "--behavior-family", "LARQL file-scope authorization correction",
        "--model-name", "Qwen3-1.7B",
        "--base-model-path-or-id", "Qwen/Qwen3-1.7B",
        "--delta-design-packet", delta,
        "--rank1-delta-artifact-record", artifact,
        "--teacher-forced-likelihood-comparison", candidate,
        "--baseline-teacher-forced-likelihood-comparison", baseline,
        "--authorize-larql-insertion-recipe-card",
    )
    assert result.returncode != 0
    assert "automatic_failure_to_curriculum_capture_authorized must be false" in result.stdout


def test_output_directory_exists_fails_closed(tmp_path):
    delta, artifact, baseline, candidate, _ = make_inputs(tmp_path)
    out_dir = tmp_path / "out" / "card_014"
    out_dir.mkdir(parents=True)
    result = run_script(
        "--run-id", "card_014",
        "--out-root", tmp_path / "out",
        "--recipe-name", "existing_out",
        "--behavior-family", "LARQL file-scope authorization correction",
        "--model-name", "Qwen3-1.7B",
        "--base-model-path-or-id", "Qwen/Qwen3-1.7B",
        "--delta-design-packet", delta,
        "--rank1-delta-artifact-record", artifact,
        "--teacher-forced-likelihood-comparison", candidate,
        "--baseline-teacher-forced-likelihood-comparison", baseline,
        "--authorize-larql-insertion-recipe-card",
    )
    assert result.returncode != 0
    assert "output directory already exists" in result.stdout


def test_json_authority_fields_are_false_where_required(tmp_path):
    delta, artifact, baseline, candidate, _ = make_inputs(tmp_path)
    card = MODULE.write_insertion_recipe_card(
        run_id="card_015",
        out_root=tmp_path / "out",
        recipe_name="authority_check",
        behavior_family="LARQL file-scope authorization correction",
        model_name="Qwen3-1.7B",
        base_model_path_or_id="Qwen/Qwen3-1.7B",
        delta_design_packet_path=delta,
        rank1_delta_artifact_record_path=artifact,
        teacher_forced_likelihood_comparison_path=candidate,
        baseline_teacher_forced_likelihood_comparison_path=baseline,
        confirmation_teacher_forced_likelihood_comparison_path=None,
        author_note="note",
        authorize_larql_insertion_recipe_card=True,
    )
    assert card["model_inference_performed_by_card_writer"] is False
    assert card["training_performed"] is False
    assert card["lora_or_peft_used"] is False
    assert card["weight_edit_performed_by_card_writer"] is False
    assert card["delta_artifact_written_by_card_writer"] is False
    assert card["patched_model_materialized_by_card_writer"] is False
    assert card["promotion_authorized"] is False
    assert card["registry_mutation_authorized"] is False
    assert card["install_authorized"] is False
    assert card["automatic_failure_to_curriculum_capture_authorized"] is False
