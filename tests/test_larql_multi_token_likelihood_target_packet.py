from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/larql_multi_token_likelihood_target_packet.py"
SPEC = importlib.util.spec_from_file_location("larql_multi_token_likelihood_target_packet", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def write_json(path: Path, payload: dict | list) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def write_jsonl(path: Path, rows: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n", encoding="utf-8")
    return path


def token_diagnostic_fixture(tmp_path: Path) -> Path:
    payload = {
        "probe_summaries": [
            {"probe_id": "original_larql_behavior_replay"},
            {"probe_id": "adjacent_file_anti_overfit"},
            {"probe_id": "all_files_authorized_control"},
            {"probe_id": "unrelated_task_regression"},
        ],
        "summary": {
            "generation_aware_status": "patched_generation_unchanged",
        },
    }
    return write_json(tmp_path / "token_position_diagnostic.json", payload)


def generation_aware_fixture(tmp_path: Path, *, mutate: dict | None = None) -> Path:
    payload = {
        "evidence_only": True,
        "promotion_authorized": False,
        "automatic_failure_to_curriculum_capture_authorized": False,
        "summary": {
            "generation_aware_status": "patched_generation_unchanged",
        },
    }
    if mutate:
        payload.update(mutate)
    return write_json(tmp_path / "generation_aware_comparison.json", payload)


def rows_fixture(tmp_path: Path) -> Path:
    rows = [
        {
            "probe_id": "original_larql_behavior_replay",
            "continuation_type": "corrected",
            "token_index": 0,
            "token_id": 1,
            "token_text": "target",
            "token_category": "semantic_text",
            "patched_minus_base_logprob": 0.5,
            "absolute_delta": 0.5,
            "contributes_to_margin_direction": True,
        },
        {
            "probe_id": "original_larql_behavior_replay",
            "continuation_type": "failure",
            "token_index": 0,
            "token_id": 2,
            "token_text": "fail",
            "token_category": "semantic_text",
            "patched_minus_base_logprob": -0.4,
            "absolute_delta": 0.4,
            "contributes_to_margin_direction": True,
        },
        {
            "probe_id": "adjacent_file_anti_overfit",
            "continuation_type": "corrected",
            "token_index": 0,
            "token_id": 3,
            "token_text": "{\"",
            "token_category": "structural_json",
            "patched_minus_base_logprob": 0.2,
            "absolute_delta": 0.2,
            "contributes_to_margin_direction": True,
        },
        {
            "probe_id": "adjacent_file_anti_overfit",
            "continuation_type": "failure",
            "token_index": 0,
            "token_id": 4,
            "token_text": "scope",
            "token_category": "semantic_text",
            "patched_minus_base_logprob": -0.3,
            "absolute_delta": 0.3,
            "contributes_to_margin_direction": True,
        },
        {
            "probe_id": "all_files_authorized_control",
            "continuation_type": "corrected",
            "token_index": 0,
            "token_id": 5,
            "token_text": "control",
            "token_category": "semantic_text",
            "patched_minus_base_logprob": -0.6,
            "absolute_delta": 0.6,
            "contributes_to_margin_direction": False,
        },
        {
            "probe_id": "all_files_authorized_control",
            "continuation_type": "failure",
            "token_index": 0,
            "token_id": 6,
            "token_text": "control",
            "token_category": "semantic_text",
            "patched_minus_base_logprob": 0.7,
            "absolute_delta": 0.7,
            "contributes_to_margin_direction": False,
        },
        {
            "probe_id": "unrelated_task_regression",
            "continuation_type": "corrected",
            "token_index": 0,
            "token_id": 7,
            "token_text": "other",
            "token_category": "semantic_text",
            "patched_minus_base_logprob": -0.1,
            "absolute_delta": 0.1,
            "contributes_to_margin_direction": False,
        },
        {
            "probe_id": "unrelated_task_regression",
            "continuation_type": "failure",
            "token_index": 0,
            "token_id": 8,
            "token_text": "other",
            "token_category": "semantic_text",
            "patched_minus_base_logprob": 0.1,
            "absolute_delta": 0.1,
            "contributes_to_margin_direction": False,
        },
        {
            "probe_id": "unrelated_task_regression",
            "continuation_type": "corrected",
            "token_index": 1,
            "token_id": 9,
            "token_text": "<think>",
            "token_category": "special_or_chat_template",
            "patched_minus_base_logprob": 0.05,
            "absolute_delta": 0.05,
            "contributes_to_margin_direction": None,
        },
        {
            "probe_id": "all_files_authorized_control",
            "continuation_type": "failure",
            "token_index": 1,
            "token_id": 10,
            "token_text": ",",
            "token_category": "whitespace_or_punctuation",
            "patched_minus_base_logprob": -0.05,
            "absolute_delta": 0.05,
            "contributes_to_margin_direction": None,
        },
    ]
    return write_jsonl(tmp_path / "token_position_rows.jsonl", rows)


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
        "--run-id", "mt_001",
        "--out-root", tmp_path / "out",
        "--token-position-diagnostic", token_diagnostic_fixture(tmp_path),
        "--token-position-rows-jsonl", rows_fixture(tmp_path),
        "--generation-aware-comparison", generation_aware_fixture(tmp_path),
    )
    assert result.returncode != 0
    assert "requires explicit opt-in authorization" in result.stdout


def test_output_directory_exists_fails_closed(tmp_path):
    out_dir = tmp_path / "out" / "mt_002"
    out_dir.mkdir(parents=True)
    result = run_script(
        "--run-id", "mt_002",
        "--out-root", tmp_path / "out",
        "--token-position-diagnostic", token_diagnostic_fixture(tmp_path),
        "--token-position-rows-jsonl", rows_fixture(tmp_path),
        "--generation-aware-comparison", generation_aware_fixture(tmp_path),
        "--authorize-larql-multi-token-likelihood-target-packet",
    )
    assert result.returncode != 0
    assert "output directory already exists" in result.stdout


def test_missing_required_inputs_fail_closed(tmp_path):
    result = run_script(
        "--run-id", "mt_003",
        "--out-root", tmp_path / "out",
        "--token-position-diagnostic", tmp_path / "missing.json",
        "--token-position-rows-jsonl", rows_fixture(tmp_path),
        "--generation-aware-comparison", generation_aware_fixture(tmp_path),
        "--authorize-larql-multi-token-likelihood-target-packet",
    )
    assert result.returncode != 0
    assert "required file path does not exist" in result.stdout


def test_generation_aware_comparison_provenance_checks(tmp_path):
    bad = generation_aware_fixture(tmp_path, mutate={"promotion_authorized": True})
    result = run_script(
        "--run-id", "mt_004",
        "--out-root", tmp_path / "out",
        "--token-position-diagnostic", token_diagnostic_fixture(tmp_path),
        "--token-position-rows-jsonl", rows_fixture(tmp_path),
        "--generation-aware-comparison", bad,
        "--authorize-larql-multi-token-likelihood-target-packet",
    )
    assert result.returncode != 0
    assert "must not authorize promotion" in result.stdout


def test_duplicate_token_row_identity_fails_closed(tmp_path):
    rows_path = tmp_path / "dup.jsonl"
    payload = [
        {
            "probe_id": "original_larql_behavior_replay",
            "continuation_type": "corrected",
            "token_index": 0,
            "token_id": 1,
            "token_text": "a",
            "token_category": "semantic_text",
            "patched_minus_base_logprob": 0.1,
            "absolute_delta": 0.1,
            "contributes_to_margin_direction": True,
        },
        {
            "probe_id": "original_larql_behavior_replay",
            "continuation_type": "corrected",
            "token_index": 0,
            "token_id": 1,
            "token_text": "a",
            "token_category": "semantic_text",
            "patched_minus_base_logprob": 0.2,
            "absolute_delta": 0.2,
            "contributes_to_margin_direction": True,
        },
    ]
    write_jsonl(rows_path, payload)
    result = run_script(
        "--run-id", "mt_005",
        "--out-root", tmp_path / "out",
        "--token-position-diagnostic", token_diagnostic_fixture(tmp_path),
        "--token-position-rows-jsonl", rows_path,
        "--generation-aware-comparison", generation_aware_fixture(tmp_path),
        "--authorize-larql-multi-token-likelihood-target-packet",
    )
    assert result.returncode != 0
    assert "duplicate token row identity exists" in result.stdout


def test_automatic_failure_capture_true_fails_closed(tmp_path):
    result = run_script(
        "--run-id", "mt_006",
        "--out-root", tmp_path / "out",
        "--token-position-diagnostic", token_diagnostic_fixture(tmp_path),
        "--token-position-rows-jsonl", rows_fixture(tmp_path),
        "--generation-aware-comparison", generation_aware_fixture(
            tmp_path, mutate={"automatic_failure_to_curriculum_capture_authorized": True}
        ),
        "--authorize-larql-multi-token-likelihood-target-packet",
    )
    assert result.returncode != 0
    assert "must not authorize automatic failure-to-curriculum capture" in result.stdout


def test_selection_and_outputs(tmp_path):
    source_recipe = write_json(
        tmp_path / "recipe.json",
        {
            "training_performed": False,
            "promotion_authorized": False,
            "registry_mutation_authorized": False,
            "install_authorized": False,
            "base_model_overwritten": False,
            "automatic_failure_to_curriculum_capture_authorized": False,
        },
    )
    source_materialization = write_json(
        tmp_path / "mat.json",
        {
            "training_performed": False,
            "promotion_authorized": False,
            "registry_mutation_authorized": False,
            "install_authorized": False,
            "base_model_overwritten": False,
            "automatic_failure_to_curriculum_capture_authorized": False,
        },
    )
    record = MODULE.write_multi_token_likelihood_target_packet(
        run_id="mt_007",
        out_root=tmp_path / "out",
        token_position_diagnostic_path=token_diagnostic_fixture(tmp_path),
        token_position_rows_jsonl=rows_fixture(tmp_path),
        generation_aware_comparison_path=generation_aware_fixture(tmp_path),
        source_recipe_card_path=source_recipe,
        source_materialization_record_path=source_materialization,
        top_n=1,
        authorize_larql_multi_token_likelihood_target_packet=True,
    )
    assert record["recommended_next_step"] == "continuation_activation_capture"
    assert record["generation_was_unchanged"] is True
    out_dir = tmp_path / "out" / "mt_007"
    assert (out_dir / "larql_multi_token_likelihood_target_packet_record.json").exists()
    assert (out_dir / "multi_token_likelihood_target_packet.json").exists()
    assert (out_dir / "multi_token_likelihood_target_rows.jsonl").exists()
    assert (out_dir / "multi_token_likelihood_target_review_packet.md").exists()
    assert record["selected_boost_count"] == 1
    assert record["selected_suppress_count"] == 1
    assert record["selected_control_protection_count"] == 1
    rows = (out_dir / "multi_token_likelihood_target_rows.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(rows) == 3


def test_selection_actions_from_rows(tmp_path):
    rows_path = rows_fixture(tmp_path)
    boost, suppress, control, summary = MODULE.select_tokens(
        [json.loads(line) for line in rows_path.read_text(encoding="utf-8").splitlines() if line.strip()],
        top_n=24,
        generation_aware_status="patched_generation_unchanged",
    )
    assert boost and boost[0]["selection_action"] == "boost_corrected_semantic_token"
    assert suppress and suppress[0]["selection_action"] == "suppress_failure_semantic_token"
    assert any(row["selection_action"] == "protect_control_corrected_token" for row in control)
    assert any(row["selection_action"] == "protect_control_failure_token" for row in control)
    assert all(row["token_category"] == "semantic_text" for row in boost + suppress + control)
    assert summary["generation_was_unchanged"] is True


def test_no_inference_or_training_in_source():
    script_text = SCRIPT.read_text(encoding="utf-8")
    assert "generate(" not in script_text
    assert "from transformers import" not in script_text.splitlines()[:60]
