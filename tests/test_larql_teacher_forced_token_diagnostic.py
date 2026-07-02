from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/larql_teacher_forced_token_diagnostic.py"
SPEC = importlib.util.spec_from_file_location("larql_teacher_forced_token_diagnostic", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def write_json(path: Path, payload: dict | list) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def materialization_record_fixture(tmp_path: Path, *, mutate: dict | None = None) -> Path:
    base_model = tmp_path / "base_model"
    patched_model = tmp_path / "patched_model"
    base_model.mkdir()
    patched_model.mkdir()
    payload = {
        "report_type": "larql_patched_model_materialization.v0",
        "base_model_path": str(base_model),
        "patched_model_path": str(patched_model),
        "target_module": "model.layers.0.mlp.down_proj.weight",
        "target_layer": "0",
        "target_module_family": "mlp_projection",
        "delta_scale": 0.001,
        "base_tensor_sha256_before": "base-sha",
        "patched_tensor_sha256_after": "patched-sha",
        "patched_model_materialized": True,
        "weight_edit_performed": True,
        "base_model_overwritten": False,
        "model_inference_performed": False,
        "training_performed": False,
        "promotion_authorized": False,
        "base_model_overwrite_authorized": False,
        "registry_mutation_authorized": False,
        "install_authorized": False,
        "automatic_failure_to_curriculum_capture_authorized": False,
    }
    if mutate:
        payload.update(mutate)
    return write_json(tmp_path / "materialization_record.json", payload)


def rows_for_probe(
    probe_id: str,
    corrected: list[tuple[int, str, float, str]],
    failure: list[tuple[int, str, float, str]],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for token_index, token_text, logprob, category in corrected:
        rows.append(
            {
                "probe_id": probe_id,
                "continuation_type": "corrected",
                "token_index": token_index,
                "token_id": 10 + token_index,
                "token_text": token_text,
                "logprob": logprob,
                "is_special_token": category == "special_or_chat_template",
                "token_category": category,
            }
        )
    for token_index, token_text, logprob, category in failure:
        rows.append(
            {
                "probe_id": probe_id,
                "continuation_type": "failure",
                "token_index": token_index,
                "token_id": 20 + token_index,
                "token_text": token_text,
                "logprob": logprob,
                "is_special_token": category == "special_or_chat_template",
                "token_category": category,
            }
        )
    return rows


def token_rows_fixture() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    rows.extend(
        rows_for_probe(
            "original_larql_behavior_replay",
            corrected=[
                (0, "<|im_start|>", -1.0, "special_or_chat_template"),
                (1, "{", -0.5, "structural_json"),
                (2, "allow", -0.1, "semantic_text"),
            ],
            failure=[
                (0, "<|im_start|>", -1.2, "special_or_chat_template"),
                (1, "{", -0.6, "structural_json"),
                (2, "deny", -0.4, "semantic_text"),
            ],
        )
    )
    rows.extend(
        rows_for_probe(
            "adjacent_file_anti_overfit",
            corrected=[
                (0, " ", -0.2, "whitespace_or_punctuation"),
                (1, '"', -0.3, "structural_json"),
            ],
            failure=[
                (0, " ", -0.1, "whitespace_or_punctuation"),
                (1, '"', -0.2, "structural_json"),
            ],
        )
    )
    rows.extend(
        rows_for_probe(
            "all_files_authorized_control",
            corrected=[
                (0, "done", -0.4, "semantic_text"),
                (1, "1", -0.2, "numeric_or_literal"),
            ],
            failure=[
                (0, "done", -0.2, "semantic_text"),
                (1, "1", -0.1, "numeric_or_literal"),
            ],
        )
    )
    rows.extend(
        rows_for_probe(
            "unrelated_task_regression",
            corrected=[
                (0, "summary", -0.1, "semantic_text"),
            ],
            failure=[
                (0, "summary", -0.3, "semantic_text"),
            ],
        )
    )
    return rows


def run_script(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_authorization_required(tmp_path):
    record = materialization_record_fixture(tmp_path)
    result = run_script(
        "--run-id", "tok_001",
        "--out-root", tmp_path / "out",
        "--materialization-record", record,
    )
    assert result.returncode != 0
    assert "requires explicit opt-in authorization" in result.stdout


def test_output_directory_exists_fails_closed(tmp_path):
    record = materialization_record_fixture(tmp_path)
    out_dir = tmp_path / "out" / "tok_002"
    out_dir.mkdir(parents=True)
    result = run_script(
        "--run-id", "tok_002",
        "--out-root", tmp_path / "out",
        "--materialization-record", record,
        "--authorize-larql-teacher-forced-token-diagnostic",
    )
    assert result.returncode != 0
    assert "output directory already exists" in result.stdout


def test_missing_materialization_record_path_fails_closed(tmp_path):
    result = run_script(
        "--run-id", "tok_003",
        "--out-root", tmp_path / "out",
        "--materialization-record", tmp_path / "missing.json",
        "--authorize-larql-teacher-forced-token-diagnostic",
    )
    assert result.returncode != 0
    assert "required file path does not exist" in result.stdout


def test_materialization_record_with_training_true_fails_closed(tmp_path):
    record = materialization_record_fixture(tmp_path, mutate={"training_performed": True})
    result = run_script(
        "--run-id", "tok_004",
        "--out-root", tmp_path / "out",
        "--materialization-record", record,
        "--authorize-larql-teacher-forced-token-diagnostic",
    )
    assert result.returncode != 0
    assert "training_performed must be false" in result.stdout


def test_materialization_record_with_promotion_true_fails_closed(tmp_path):
    record = materialization_record_fixture(tmp_path, mutate={"promotion_authorized": True})
    result = run_script(
        "--run-id", "tok_005",
        "--out-root", tmp_path / "out",
        "--materialization-record", record,
        "--authorize-larql-teacher-forced-token-diagnostic",
    )
    assert result.returncode != 0
    assert "promotion_authorized must be false" in result.stdout


def test_materialization_record_with_auto_failure_true_fails_closed(tmp_path):
    record = materialization_record_fixture(tmp_path, mutate={"automatic_failure_to_curriculum_capture_authorized": True})
    result = run_script(
        "--run-id", "tok_006",
        "--out-root", tmp_path / "out",
        "--materialization-record", record,
        "--authorize-larql-teacher-forced-token-diagnostic",
    )
    assert result.returncode != 0
    assert "automatic_failure_to_curriculum_capture_authorized must be false" in result.stdout


def test_token_categorization_helpers():
    assert MODULE.categorize_token("<|im_start|>", token_id=1, special_token_ids={1}) == "special_or_chat_template"
    assert MODULE.categorize_token('{"', token_id=2, special_token_ids=set()) == "structural_json"
    assert MODULE.categorize_token(" allow ", token_id=3, special_token_ids=set()) == "semantic_text"
    assert MODULE.categorize_token("   ", token_id=4, special_token_ids=set()) == "whitespace_or_punctuation"


def test_margin_direction_helpers():
    assert MODULE.margin_direction_for_token("corrected", 0.5) is True
    assert MODULE.margin_direction_for_token("corrected", -0.5) is False
    assert MODULE.margin_direction_for_token("failure", -0.5) is True
    assert MODULE.margin_direction_for_token("failure", 0.5) is False


def test_compare_and_score_summary_counts():
    base_rows = token_rows_fixture()
    patched_rows = []
    for row in base_rows:
        patched_row = dict(row)
        if row["continuation_type"] == "corrected":
            patched_row["logprob"] = float(row["logprob"]) + 0.5
        else:
            patched_row["logprob"] = float(row["logprob"]) - 0.5
        patched_rows.append(patched_row)
    diagnostic, rows = MODULE.compare_and_score(base_rows, patched_rows)
    assert diagnostic["summary"]["corrected_token_count"] > 0
    assert diagnostic["summary"]["failure_token_count"] > 0
    assert diagnostic["summary"]["probes_semantic_improvement_count"] >= 1
    assert diagnostic["summary"]["semantic_token_delta_sum"] != 0
    assert rows


def test_authorized_run_writes_outputs(tmp_path, monkeypatch):
    record = materialization_record_fixture(tmp_path)
    out_root = tmp_path / "out"
    base_rows = token_rows_fixture()
    patched_rows = []
    for row in base_rows:
        patched_row = dict(row)
        patched_row["logprob"] = float(row["logprob"]) + (0.25 if row["continuation_type"] == "corrected" else -0.25)
        patched_rows.append(patched_row)
    counter = {"calls": 0}

    def fake_run_token_position_scoring_for_model_path(**kwargs):
        counter["calls"] += 1
        return base_rows if counter["calls"] == 1 else patched_rows

    monkeypatch.setattr(MODULE, "inference_stack_available", lambda: True)
    monkeypatch.setattr(
        MODULE,
        "run_token_position_scoring_for_model_path",
        fake_run_token_position_scoring_for_model_path,
    )
    rec = MODULE.write_token_diagnostic(
        run_id="tok_007",
        out_root=out_root,
        materialization_record_path=record,
        authorize_larql_teacher_forced_token_diagnostic=True,
        device="cpu",
        top_n=20,
    )
    out_dir = out_root / "tok_007"
    assert rec["report_type"] == "larql_teacher_forced_token_diagnostic.v0"
    assert (out_dir / "larql_teacher_forced_token_diagnostic_record.json").exists()
    assert (out_dir / "token_position_diagnostic.json").exists()
    assert (out_dir / "token_position_rows.jsonl").exists()
    assert (out_dir / "token_position_diagnostic_review_packet.md").exists()


def test_generation_training_promotion_and_capture_flags_false(tmp_path, monkeypatch):
    record = materialization_record_fixture(tmp_path)
    out_root = tmp_path / "out"
    base_rows = token_rows_fixture()
    patched_rows = [dict(row) for row in base_rows]

    def fake_run_token_position_scoring_for_model_path(**kwargs):
        return base_rows if kwargs["model_path"].name == "base_model" else patched_rows

    monkeypatch.setattr(MODULE, "inference_stack_available", lambda: True)
    monkeypatch.setattr(
        MODULE,
        "run_token_position_scoring_for_model_path",
        fake_run_token_position_scoring_for_model_path,
    )
    rec = MODULE.write_token_diagnostic(
        run_id="tok_008",
        out_root=out_root,
        materialization_record_path=record,
        authorize_larql_teacher_forced_token_diagnostic=True,
        device="cpu",
        top_n=20,
    )
    assert rec["generation_performed"] is False
    assert rec["training_performed"] is False
    assert rec["weight_edit_performed"] is False
    assert rec["delta_artifact_written"] is False
    assert rec["patched_model_materialized"] is False
    assert rec["base_model_overwritten"] is False
    assert rec["promotion_authorized"] is False
    assert rec["automatic_failure_to_curriculum_capture_authorized"] is False


def test_no_real_inference_or_heavy_imports_in_tests():
    script_text = SCRIPT.read_text(encoding="utf-8")
    assert "generate(" not in script_text
    assert "import torch" not in script_text.splitlines()[:40]
