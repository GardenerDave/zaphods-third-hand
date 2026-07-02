from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/larql_continuation_direction_packet.py"
SPEC = importlib.util.spec_from_file_location("larql_continuation_direction_packet", SCRIPT)
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


def vectors_fixture(tmp_path: Path, *, mutate: dict | None = None) -> Path:
    rows = [
        {
            "probe_id": "original_larql_behavior_replay",
            "continuation_type": "corrected",
            "selection_action": "boost_corrected_semantic_token",
            "token_category": "semantic_text",
            "token_index": 0,
            "token_id": 1,
            "token_text": "boost",
            "patched_minus_base_logprob": 0.5,
            "absolute_delta": 0.5,
            "contributes_to_margin_direction": True,
            "target_module": "model.layers.0.mlp.down_proj",
            "target_module_family": "mlp_projection",
            "vector_source": "continuation_prediction_position",
            "prediction_position": 1,
            "module_input_vector": [3.0, 1.0, 0.0],
            "module_output_vector": [1.0, 2.0],
        },
        {
            "probe_id": "adjacent_file_anti_overfit",
            "continuation_type": "corrected",
            "selection_action": "boost_corrected_semantic_token",
            "token_category": "semantic_text",
            "token_index": 1,
            "token_id": 2,
            "token_text": "boost2",
            "patched_minus_base_logprob": 0.4,
            "absolute_delta": 0.4,
            "contributes_to_margin_direction": True,
            "target_module": "model.layers.0.mlp.down_proj",
            "target_module_family": "mlp_projection",
            "vector_source": "continuation_prediction_position",
            "prediction_position": 2,
            "module_input_vector": [5.0, 1.0, 0.0],
            "module_output_vector": [2.0, 1.0],
        },
        {
            "probe_id": "original_larql_behavior_replay",
            "continuation_type": "failure",
            "selection_action": "suppress_failure_semantic_token",
            "token_category": "semantic_text",
            "token_index": 0,
            "token_id": 3,
            "token_text": "suppress",
            "patched_minus_base_logprob": -0.2,
            "absolute_delta": 0.2,
            "contributes_to_margin_direction": True,
            "target_module": "model.layers.0.mlp.down_proj",
            "target_module_family": "mlp_projection",
            "vector_source": "continuation_prediction_position",
            "prediction_position": 1,
            "module_input_vector": [1.0, 2.0, 0.0],
            "module_output_vector": [0.5, 0.5],
        },
        {
            "probe_id": "adjacent_file_anti_overfit",
            "continuation_type": "failure",
            "selection_action": "suppress_failure_semantic_token",
            "token_category": "semantic_text",
            "token_index": 1,
            "token_id": 4,
            "token_text": "suppress2",
            "patched_minus_base_logprob": -0.3,
            "absolute_delta": 0.3,
            "contributes_to_margin_direction": True,
            "target_module": "model.layers.0.mlp.down_proj",
            "target_module_family": "mlp_projection",
            "vector_source": "continuation_prediction_position",
            "prediction_position": 2,
            "module_input_vector": [2.0, 2.0, 0.0],
            "module_output_vector": [0.0, 1.0],
        },
        {
            "probe_id": "all_files_authorized_control",
            "continuation_type": "corrected",
            "selection_action": "protect_control_corrected_token",
            "token_category": "semantic_text",
            "token_index": 0,
            "token_id": 5,
            "token_text": "control",
            "patched_minus_base_logprob": -0.6,
            "absolute_delta": 0.6,
            "contributes_to_margin_direction": False,
            "target_module": "model.layers.0.mlp.down_proj",
            "target_module_family": "mlp_projection",
            "vector_source": "continuation_prediction_position",
            "prediction_position": 1,
            "module_input_vector": [2.0, 3.0, 0.0],
            "module_output_vector": [1.0, 0.0],
        },
        {
            "probe_id": "unrelated_task_regression",
            "continuation_type": "failure",
            "selection_action": "protect_control_failure_token",
            "token_category": "semantic_text",
            "token_index": 0,
            "token_id": 6,
            "token_text": "control2",
            "patched_minus_base_logprob": 0.7,
            "absolute_delta": 0.7,
            "contributes_to_margin_direction": False,
            "target_module": "model.layers.0.mlp.down_proj",
            "target_module_family": "mlp_projection",
            "vector_source": "continuation_prediction_position",
            "prediction_position": 1,
            "module_input_vector": [4.0, 2.0, 0.0],
            "module_output_vector": [0.0, 1.0],
        },
    ]
    if mutate:
        for row in rows:
            row.update(mutate)
    return write_jsonl(tmp_path / "continuation_activation_vectors.jsonl", rows)


def summary_fixture(tmp_path: Path, *, mutate: dict | None = None) -> Path:
    payload = {
        "capture_status": "completed",
        "vector_source": "continuation_prediction_position",
        "selected_token_count": 6,
        "captured_vector_count": 6,
    }
    if mutate:
        payload.update(mutate)
    return write_json(tmp_path / "continuation_activation_capture_summary.json", payload)


def capture_record_fixture(tmp_path: Path, *, mutate: dict | None = None) -> Path:
    payload = {
        "training_performed": False,
        "generation_performed": False,
        "promotion_authorized": False,
        "registry_mutation_authorized": False,
        "install_authorized": False,
        "base_model_overwritten": False,
        "automatic_failure_to_curriculum_capture_authorized": False,
        "target_module": "model.layers.0.mlp.down_proj",
        "target_module_family": "mlp_projection",
        "captured_vector_count": 6,
    }
    if mutate:
        payload.update(mutate)
    return write_json(tmp_path / "larql_continuation_activation_capture_record.json", payload)


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
        "--run-id", "cd_001",
        "--out-root", tmp_path / "out",
        "--continuation-activation-vectors", vectors_fixture(tmp_path),
        "--continuation-activation-summary", summary_fixture(tmp_path),
    )
    assert result.returncode != 0
    assert "requires explicit opt-in authorization" in result.stdout


def test_output_directory_exists_fails_closed(tmp_path):
    (tmp_path / "out" / "cd_002").mkdir(parents=True)
    result = run_script(
        "--run-id", "cd_002",
        "--out-root", tmp_path / "out",
        "--continuation-activation-vectors", vectors_fixture(tmp_path),
        "--continuation-activation-summary", summary_fixture(tmp_path),
        "--authorize-larql-continuation-direction-packet",
    )
    assert result.returncode != 0
    assert "output directory already exists" in result.stdout


def test_missing_inputs_fail_closed(tmp_path):
    result = run_script(
        "--run-id", "cd_003",
        "--out-root", tmp_path / "out",
        "--continuation-activation-vectors", tmp_path / "missing.jsonl",
        "--continuation-activation-summary", summary_fixture(tmp_path),
        "--authorize-larql-continuation-direction-packet",
    )
    assert result.returncode != 0
    assert "required file path does not exist" in result.stdout


def test_validation_failures(tmp_path):
    for mutate, message in [
        ({"capture_status": "rejected"}, "capture_status must be completed or completed_with_warnings"),
        ({"vector_source": "other"}, "vector_source must be continuation_prediction_position"),
    ]:
        result = run_script(
            "--run-id", f"cd_{abs(hash(message)) % 1000}",
            "--out-root", tmp_path / "out",
            "--continuation-activation-vectors", vectors_fixture(tmp_path),
            "--continuation-activation-summary", summary_fixture(tmp_path, mutate=mutate),
            "--authorize-larql-continuation-direction-packet",
        )
        assert result.returncode != 0
        assert message in result.stdout


def test_missing_rows_and_inconsistent_rows_fail_closed(tmp_path):
    empty_vectors = write_jsonl(tmp_path / "empty.jsonl", [])
    result = run_script(
        "--run-id", "cd_010",
        "--out-root", tmp_path / "out",
        "--continuation-activation-vectors", empty_vectors,
        "--continuation-activation-summary", summary_fixture(tmp_path),
        "--authorize-larql-continuation-direction-packet",
    )
    assert result.returncode != 0
    assert "no vector rows" in result.stdout

    bad_vectors = vectors_fixture(tmp_path, mutate={})
    rows = [json.loads(line) for line in bad_vectors.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows[0]["target_module"] = "other"
    write_jsonl(bad_vectors, rows)
    result = run_script(
        "--run-id", "cd_011",
        "--out-root", tmp_path / "out",
        "--continuation-activation-vectors", bad_vectors,
        "--continuation-activation-summary", summary_fixture(tmp_path),
        "--authorize-larql-continuation-direction-packet",
    )
    assert result.returncode != 0
    assert "target_module is missing or inconsistent across rows" in result.stdout or "vector lengths are inconsistent" in result.stdout


def test_inconsistent_vector_lengths_fail_closed(tmp_path):
    bad_vectors = vectors_fixture(tmp_path)
    rows = [json.loads(line) for line in bad_vectors.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows[0]["module_input_vector"] = [1.0, 2.0]
    write_jsonl(bad_vectors, rows)
    result = run_script(
        "--run-id", "cd_012",
        "--out-root", tmp_path / "out",
        "--continuation-activation-vectors", bad_vectors,
        "--continuation-activation-summary", summary_fixture(tmp_path),
        "--authorize-larql-continuation-direction-packet",
    )
    assert result.returncode != 0
    assert "module_input_vector lengths are inconsistent" in result.stdout


def test_missing_required_selection_action_fail_closed(tmp_path):
    bad_vectors = vectors_fixture(tmp_path)
    rows = [json.loads(line) for line in bad_vectors.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows = [row for row in rows if row["selection_action"] != "suppress_failure_semantic_token"]
    write_jsonl(bad_vectors, rows)
    result = run_script(
        "--run-id", "cd_013",
        "--out-root", tmp_path / "out",
        "--continuation-activation-vectors", bad_vectors,
        "--continuation-activation-summary", summary_fixture(tmp_path),
        "--authorize-larql-continuation-direction-packet",
    )
    assert result.returncode != 0
    assert "missing suppress rows" in result.stdout


def test_direction_math_and_outputs(tmp_path):
    vectors = vectors_fixture(tmp_path)
    summary = summary_fixture(tmp_path)
    capture = capture_record_fixture(tmp_path)
    record = MODULE.write_continuation_direction_packet(
        run_id="cd_014",
        out_root=tmp_path / "out",
        continuation_activation_vectors=vectors,
        continuation_activation_summary=summary,
        source_capture_record=capture,
        direction_mode="target_minus_control",
        authorize_larql_continuation_direction_packet=True,
    )
    out_dir = tmp_path / "out" / "cd_014"
    assert (out_dir / "larql_continuation_direction_packet_record.json").exists()
    assert (out_dir / "continuation_direction_packet.json").exists()
    assert (out_dir / "continuation_direction_vectors.json").exists()
    assert (out_dir / "continuation_direction_review_packet.md").exists()
    vector_payload = json.loads((out_dir / "continuation_direction_vectors.json").read_text(encoding="utf-8"))
    assert vector_payload["report_type"] == "larql_continuation_direction_vectors.v0"
    assert len(vector_payload["continuation_output_direction"]) == 2
    assert len(vector_payload["continuation_input_direction"]) == 3
    output_norm = MODULE.l2_norm(vector_payload["continuation_output_direction"])
    input_norm = MODULE.l2_norm(vector_payload["continuation_input_direction"])
    assert abs(output_norm - 1.0) < 1e-6
    assert abs(input_norm - 1.0) < 1e-6
    assert record["recommended_next_step"] == "continuation_rank1_delta_design"
    assert record["required_next_step"] == "supervised_continuation_direction_review"
    assert record["source_capture_record_missing_warning"] is False
    assert record["model_inference_performed"] is False
    assert record["generation_performed"] is False
    assert record["training_performed"] is False
    assert record["weight_edit_performed"] is False
    assert record["delta_artifact_written"] is False
    assert record["patched_model_materialized"] is False
    assert record["promotion_authorized"] is False
    assert record["automatic_failure_to_curriculum_capture_authorized"] is False


def test_zero_norm_direction_fails_closed(tmp_path):
    rows = vectors_fixture(tmp_path)
    parsed = [json.loads(line) for line in rows.read_text(encoding="utf-8").splitlines() if line.strip()]
    for row in parsed:
        if row["selection_action"] in {"boost_corrected_semantic_token", "suppress_failure_semantic_token"}:
            row["module_output_vector"] = [1.0, 1.0]
            row["module_input_vector"] = [1.0, 1.0, 1.0]
        else:
            row["module_output_vector"] = [1.0, 1.0]
            row["module_input_vector"] = [1.0, 1.0, 1.0]
    write_jsonl(rows, parsed)
    result = run_script(
        "--run-id", "cd_015",
        "--out-root", tmp_path / "out",
        "--continuation-activation-vectors", rows,
        "--continuation-activation-summary", summary_fixture(tmp_path),
        "--authorize-larql-continuation-direction-packet",
    )
    assert result.returncode != 0
    assert "zero-norm output direction" in result.stdout or "zero-norm input direction" in result.stdout


def test_missing_prediction_position_fails_closed(tmp_path):
    vectors = vectors_fixture(tmp_path)
    rows = [json.loads(line) for line in vectors.read_text(encoding="utf-8").splitlines() if line.strip()]
    del rows[0]["prediction_position"]
    write_jsonl(vectors, rows)
    result = run_script(
        "--run-id", "cd_016",
        "--out-root", tmp_path / "out",
        "--continuation-activation-vectors", vectors,
        "--continuation-activation-summary", summary_fixture(tmp_path),
        "--source-capture-record", capture_record_fixture(tmp_path),
        "--authorize-larql-continuation-direction-packet",
    )
    assert result.returncode != 0
    assert "prediction positions missing" in result.stdout


def test_capture_record_authority_and_mismatch_checks(tmp_path):
    vectors = vectors_fixture(tmp_path)
    summary = summary_fixture(tmp_path)
    bad_authority = capture_record_fixture(tmp_path, mutate={"promotion_authorized": True})
    result = run_script(
        "--run-id", "cd_017",
        "--out-root", tmp_path / "out",
        "--continuation-activation-vectors", vectors,
        "--continuation-activation-summary", summary,
        "--source-capture-record", bad_authority,
        "--authorize-larql-continuation-direction-packet",
    )
    assert result.returncode != 0
    assert "promotion_authorized must be false" in result.stdout

    bad_target = capture_record_fixture(tmp_path, mutate={"target_module": "other"})
    result = run_script(
        "--run-id", "cd_018",
        "--out-root", tmp_path / "out",
        "--continuation-activation-vectors", vectors,
        "--continuation-activation-summary", summary,
        "--source-capture-record", bad_target,
        "--authorize-larql-continuation-direction-packet",
    )
    assert result.returncode != 0
    assert "target_module in source capture record does not match vector rows" in result.stdout

    bad_count = capture_record_fixture(tmp_path, mutate={"captured_vector_count": 3})
    result = run_script(
        "--run-id", "cd_019",
        "--out-root", tmp_path / "out",
        "--continuation-activation-vectors", vectors,
        "--continuation-activation-summary", summary,
        "--source-capture-record", bad_count,
        "--authorize-larql-continuation-direction-packet",
    )
    assert result.returncode != 0
    assert "captured_vector_count in source capture record does not match row count" in result.stdout


def test_no_inference_or_training_in_source():
    script_text = SCRIPT.read_text(encoding="utf-8")
    assert "generate(" not in script_text
    assert "from transformers import" not in script_text[:1200]
