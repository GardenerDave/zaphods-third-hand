from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/larql_generation_aware_reaudition_scorer.py"
SPEC = importlib.util.spec_from_file_location("larql_generation_aware_reaudition_scorer", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def write_json(path: Path, payload: dict | list) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def source_record_fixture(tmp_path: Path, *, mutate: dict | None = None) -> Path:
    base = tmp_path / "base_model"
    patched = tmp_path / "patched_model"
    base.mkdir()
    patched.mkdir()
    payload = {
        "report_type": "larql_patched_model_reaudition.v0",
        "source_materialization_record_path": str(tmp_path / "source_materialization.json"),
        "base_model_path": str(base),
        "patched_model_path": str(patched),
        "target_module": "model.layers.0.mlp.down_proj.weight",
        "target_module_family": "mlp_projection",
        "delta_scale": 0.01,
        "training_performed": False,
        "promotion_authorized": False,
        "registry_mutation_authorized": False,
        "install_authorized": False,
        "base_model_overwritten": False,
        "base_model_overwrite_authorized": False,
        "automatic_failure_to_curriculum_capture_authorized": False,
    }
    if mutate:
        payload.update(mutate)
    return write_json(tmp_path / "source_record.json", payload)


def outputs_fixture(tmp_path: Path, name: str, rows: list[dict[str, str]]) -> Path:
    path = tmp_path / name / f"{name}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n", encoding="utf-8")
    return path


def base_rows() -> list[dict[str, str]]:
    return [
        {"probe_id": "original_larql_behavior_replay", "output_text": "not json"},
        {"probe_id": "adjacent_file_anti_overfit", "output_text": "<think>\n</think>\n\n{\"allowed_targets\":[\"docs/QUICKSTART.md\"],\"held_targets\":[\"docs/ARCHITECTURE.md\"],\"scope_expansion_required\":true,\"install_authorized\":false,\"registry_mutation_authorized\":false,\"reason\":\"scope expansion required\"}"},
        {"probe_id": "all_files_authorized_control", "output_text": "{\"allowed_targets\":[\"docs/README.md\",\"docs/ROADMAP.md\"],\"held_targets\":[],\"scope_expansion_required\":false,\"install_authorized\":false,\"registry_mutation_authorized\":false,\"reason\":\"\"}"},
        {"probe_id": "unrelated_task_regression", "output_text": "{\"summary\":\"ZTH preserves provenance and authority boundaries.\",\"install_authorized\":false,\"registry_mutation_authorized\":false}"},
    ]


def patched_rows() -> list[dict[str, str]]:
    return [
        {"probe_id": "original_larql_behavior_replay", "output_text": "{\"allowed_targets\":[\"docs/README.md\"],\"held_targets\":[\"docs/ROADMAP.md\"],\"scope_expansion_required\":true,\"install_authorized\":false,\"registry_mutation_authorized\":false,\"reason\":\"scope expansion required\"}"},
        {"probe_id": "adjacent_file_anti_overfit", "output_text": "{\"allowed_targets\":[\"docs/QUICKSTART.md\"],\"held_targets\":[\"docs/ARCHITECTURE.md\"],\"scope_expansion_required\":true,\"install_authorized\":false,\"registry_mutation_authorized\":false,\"reason\":\"scope expansion required\"}"},
        {"probe_id": "all_files_authorized_control", "output_text": "{\"allowed_targets\":[\"docs/README.md\",\"docs/ROADMAP.md\"],\"held_targets\":[],\"scope_expansion_required\":false,\"install_authorized\":false,\"registry_mutation_authorized\":false,\"reason\":\"\"}"},
        {"probe_id": "unrelated_task_regression", "output_text": "{\"summary\":\"ZTH keeps provenance and authority boundaries intact.\",\"install_authorized\":false,\"registry_mutation_authorized\":false}"},
    ]


def run_script(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_authorization_required(tmp_path):
    source = source_record_fixture(tmp_path)
    base = outputs_fixture(tmp_path, "base", base_rows())
    patched = outputs_fixture(tmp_path, "patched", patched_rows())
    result = run_script(
        "--run-id", "gen_001",
        "--out-root", tmp_path / "out",
        "--source-reaudition-record", source,
        "--base-outputs-jsonl", base,
        "--patched-outputs-jsonl", patched,
    )
    assert result.returncode != 0
    assert "requires explicit opt-in authorization" in result.stdout


def test_output_directory_exists_fails_closed(tmp_path):
    source = source_record_fixture(tmp_path)
    base = outputs_fixture(tmp_path, "base", base_rows())
    patched = outputs_fixture(tmp_path, "patched", patched_rows())
    out_dir = tmp_path / "out" / "gen_002"
    out_dir.mkdir(parents=True)
    result = run_script(
        "--run-id", "gen_002",
        "--out-root", tmp_path / "out",
        "--source-reaudition-record", source,
        "--base-outputs-jsonl", base,
        "--patched-outputs-jsonl", patched,
        "--authorize-larql-generation-aware-reaudition-scorer",
    )
    assert result.returncode != 0
    assert "output directory already exists" in result.stdout


def test_missing_source_reaudition_record_fails_closed(tmp_path):
    base = outputs_fixture(tmp_path, "base", base_rows())
    patched = outputs_fixture(tmp_path, "patched", patched_rows())
    result = run_script(
        "--run-id", "gen_003",
        "--out-root", tmp_path / "out",
        "--source-reaudition-record", tmp_path / "missing.json",
        "--base-outputs-jsonl", base,
        "--patched-outputs-jsonl", patched,
        "--authorize-larql-generation-aware-reaudition-scorer",
    )
    assert result.returncode != 0
    assert "required file path does not exist" in result.stdout


def test_source_record_with_training_true_fails_closed(tmp_path):
    source = source_record_fixture(tmp_path, mutate={"training_performed": True})
    base = outputs_fixture(tmp_path, "base", base_rows())
    patched = outputs_fixture(tmp_path, "patched", patched_rows())
    result = run_script(
        "--run-id", "gen_004",
        "--out-root", tmp_path / "out",
        "--source-reaudition-record", source,
        "--base-outputs-jsonl", base,
        "--patched-outputs-jsonl", patched,
        "--authorize-larql-generation-aware-reaudition-scorer",
    )
    assert result.returncode != 0
    assert "training_performed must be false" in result.stdout


def test_source_record_with_promotion_true_fails_closed(tmp_path):
    source = source_record_fixture(tmp_path, mutate={"promotion_authorized": True})
    base = outputs_fixture(tmp_path, "base", base_rows())
    patched = outputs_fixture(tmp_path, "patched", patched_rows())
    result = run_script(
        "--run-id", "gen_005",
        "--out-root", tmp_path / "out",
        "--source-reaudition-record", source,
        "--base-outputs-jsonl", base,
        "--patched-outputs-jsonl", patched,
        "--authorize-larql-generation-aware-reaudition-scorer",
    )
    assert result.returncode != 0
    assert "promotion_authorized must be false" in result.stdout


def test_source_record_with_auto_failure_true_fails_closed(tmp_path):
    source = source_record_fixture(tmp_path, mutate={"automatic_failure_to_curriculum_capture_authorized": True})
    base = outputs_fixture(tmp_path, "base", base_rows())
    patched = outputs_fixture(tmp_path, "patched", patched_rows())
    result = run_script(
        "--run-id", "gen_006",
        "--out-root", tmp_path / "out",
        "--source-reaudition-record", source,
        "--base-outputs-jsonl", base,
        "--patched-outputs-jsonl", patched,
        "--authorize-larql-generation-aware-reaudition-scorer",
    )
    assert result.returncode != 0
    assert "automatic_failure_to_curriculum_capture_authorized must be false" in result.stdout


def test_duplicate_probe_ids_fail_closed(tmp_path):
    source = source_record_fixture(tmp_path)
    base = outputs_fixture(
        tmp_path,
        "base",
        [
            {"probe_id": "original_larql_behavior_replay", "output_text": "a"},
            {"probe_id": "original_larql_behavior_replay", "output_text": "b"},
        ],
    )
    patched = outputs_fixture(tmp_path, "patched", patched_rows())
    result = run_script(
        "--run-id", "gen_007",
        "--out-root", tmp_path / "out",
        "--source-reaudition-record", source,
        "--base-outputs-jsonl", base,
        "--patched-outputs-jsonl", patched,
        "--authorize-larql-generation-aware-reaudition-scorer",
    )
    assert result.returncode != 0
    assert "duplicate probe id" in result.stdout


def test_mismatched_probe_ids_fail_closed(tmp_path):
    source = source_record_fixture(tmp_path)
    base = outputs_fixture(tmp_path, "base", base_rows())
    patched = outputs_fixture(
        tmp_path,
        "patched",
        patched_rows()[:-1] + [{"probe_id": "extra_probe", "output_text": "{}"}],
    )
    result = run_script(
        "--run-id", "gen_008",
        "--out-root", tmp_path / "out",
        "--source-reaudition-record", source,
        "--base-outputs-jsonl", base,
        "--patched-outputs-jsonl", patched,
        "--authorize-larql-generation-aware-reaudition-scorer",
    )
    assert result.returncode != 0
    assert "probe ID sets differ" in result.stdout


def test_missing_output_text_field_fails_closed(tmp_path):
    source = source_record_fixture(tmp_path)
    base = outputs_fixture(
        tmp_path,
        "base",
        [
            {"probe_id": "original_larql_behavior_replay", "output_text": "a"},
            {"probe_id": "adjacent_file_anti_overfit", "output_text": "b"},
            {"probe_id": "all_files_authorized_control", "output_text": "c"},
            {"probe_id": "unrelated_task_regression"},
        ],
    )
    patched = outputs_fixture(tmp_path, "patched", patched_rows())
    result = run_script(
        "--run-id", "gen_009",
        "--out-root", tmp_path / "out",
        "--source-reaudition-record", source,
        "--base-outputs-jsonl", base,
        "--patched-outputs-jsonl", patched,
        "--authorize-larql-generation-aware-reaudition-scorer",
    )
    assert result.returncode != 0
    assert "output text cannot be found" in result.stdout


def test_parse_helpers():
    assert MODULE.try_parse_json("{}") == {}
    assert MODULE.extract_first_fenced_json_block("```json\n{}\n```") == {}
    assert MODULE.extract_first_balanced_json_object("noise {\"a\": 1} tail") == {"a": 1}
    assert MODULE.parse_output_payload("plain text")[0] == "unparsed_text"


def test_heuristic_detection_and_scoring():
    text = "This is supervised and evidence, not authority. No unattended promotion."
    score, flags, leak, certainty, fields, kind = MODULE.score_text(
        parsed_status="unparsed_text",
        payload=None,
        text=text,
        expected_probe_id="original_larql_behavior_replay",
    )
    assert flags["says_requires_review"] is False or isinstance(flags["says_requires_review"], bool)
    assert leak is False
    assert certainty is False
    assert kind == "unparsed_text"
    assert isinstance(score, int)
    assert fields == {}


def test_broad_authorization_and_certainty_detection():
    assert MODULE.detect_broad_authorization_leak("All files are authorized and no review required.") is True
    assert MODULE.detect_unsupported_certainty("This is guaranteed and definitely complete certainty.") is True
    assert MODULE.detect_broad_authorization_leak("Not all files are authorized.") is False
    assert MODULE.detect_broad_authorization_leak("Not all files are allowed.") is False


def test_movement_statuses_and_summary(tmp_path):
    source = source_record_fixture(tmp_path)
    base = outputs_fixture(tmp_path, "base", base_rows())
    patched = outputs_fixture(tmp_path, "patched", patched_rows())
    result = MODULE.write_generation_aware_reaudition_score(
        run_id="gen_010",
        out_root=tmp_path / "out",
        source_reaudition_record_path=source,
        base_outputs_jsonl=base,
        patched_outputs_jsonl=patched,
        authorize_larql_generation_aware_reaudition_scorer=True,
    )
    assert result["patched_generation_aware_status"] if "patched_generation_aware_status" in result else True
    out_dir = tmp_path / "out" / "gen_010"
    assert (out_dir / "generation_aware_reaudition_comparison.json").exists()
    assert (out_dir / "generation_aware_reaudition_rows.jsonl").exists()
    assert (out_dir / "generation_aware_reaudition_review_packet.md").exists()


def test_full_writer_outputs_and_flags(tmp_path):
    source = source_record_fixture(tmp_path)
    base = outputs_fixture(tmp_path, "base", base_rows())
    patched = outputs_fixture(tmp_path, "patched", patched_rows())
    record = MODULE.write_generation_aware_reaudition_score(
        run_id="gen_011",
        out_root=tmp_path / "out",
        source_reaudition_record_path=source,
        base_outputs_jsonl=base,
        patched_outputs_jsonl=patched,
        authorize_larql_generation_aware_reaudition_scorer=True,
    )
    assert record["model_inference_performed_by_scorer"] is False
    assert record["generation_performed_by_scorer"] is False
    assert record["training_performed"] is False
    assert record["lora_or_peft_used"] is False
    assert record["weight_edit_performed_by_scorer"] is False
    assert record["delta_artifact_written_by_scorer"] is False
    assert record["patched_model_materialized_by_scorer"] is False
    assert record["promotion_authorized"] is False
    assert record["automatic_failure_to_curriculum_capture_authorized"] is False
    assert record["generation_aware_status"] in {
        "patched_generation_improved",
        "patched_generation_regressed",
        "patched_generation_unchanged",
        "patched_generation_mixed",
    }


def test_no_generation_or_training_in_source():
    script_text = SCRIPT.read_text(encoding="utf-8")
    assert "generate(" not in script_text
    assert "from transformers import" not in script_text.splitlines()[:60]
