from __future__ import annotations

import importlib.util
import json
import pickle
import struct
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/larql_continuation_patched_model_reaudition.py"
SPEC = importlib.util.spec_from_file_location("larql_continuation_patched_model_reaudition", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def write_json(path: Path, payload: dict | list) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def encode_safetensors_single_tensor(tensor_key: str, values: list[list[float]]) -> bytes:
    rows = len(values)
    cols = len(values[0]) if values else 0
    data = struct.pack("<" + "f" * (rows * cols), *[float(v) for row in values for v in row])
    header = {
        tensor_key: {
            "dtype": "F32",
            "shape": [rows, cols],
            "data_offsets": [0, len(data)],
        }
    }
    header_bytes = json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return struct.pack("<Q", len(header_bytes)) + header_bytes + data


def base_model_fixture(tmp_path: Path) -> Path:
    base = tmp_path / "base_model"
    base.mkdir()
    (base / "model_state.pt").write_bytes(
        pickle.dumps(
            {
                "model.layers.0.mlp.down_proj.weight": [[0.0, 0.0], [0.0, 0.0]],
                "other.weight": [[1.0]],
            },
            protocol=pickle.HIGHEST_PROTOCOL,
        )
    )
    (base / "config.json").write_text("{}", encoding="utf-8")
    return base


def patched_model_fixture(tmp_path: Path) -> Path:
    patched = tmp_path / "patched_model"
    patched.mkdir()
    (patched / "model_state.pt").write_bytes(
        pickle.dumps(
            {
                "model.layers.0.mlp.down_proj.weight": [[0.1, 0.1], [0.1, 0.1]],
                "other.weight": [[1.0]],
            },
            protocol=pickle.HIGHEST_PROTOCOL,
        )
    )
    (patched / "config.json").write_text("{}", encoding="utf-8")
    return patched


def manifest_fixture(tmp_path: Path, *, mutate: dict | None = None) -> tuple[Path, Path]:
    manifest = {
        "report_type": "larql_continuation_patched_model_materialization.v0",
        "patched_model_materialized": True,
        "weight_edit_performed": True,
        "base_model_overwritten": False,
        "promotion_authorized": False,
        "registry_mutation_authorized": False,
        "install_authorized": False,
        "automatic_failure_to_curriculum_capture_authorized": False,
        "model_inference_performed": False,
        "generation_performed": False,
        "training_performed": False,
        "lora_or_peft_used": False,
        "production_deployment_authorized": False,
        "target_module": "model.layers.0.mlp.down_proj",
        "target_parameter": "model.layers.0.mlp.down_proj.weight",
        "target_module_family": "mlp_projection",
        "vector_source": "continuation_prediction_position",
        "delta_shape": [2, 2],
        "delta_dtype": "float32",
        "base_weight_dtype": "torch.bfloat16",
        "patched_weight_dtype": "torch.bfloat16",
        "base_weight_shape": [2, 2],
        "patched_weight_shape": [2, 2],
        "target_shard_relative_path": "model_state.pt",
        "target_shard_sha256_before": sha256(tmp_path / "base_model" / "model_state.pt"),
        "target_shard_sha256_after": sha256(tmp_path / "patched_model" / "model_state.pt"),
        "patched_model_file_count": 2,
        "recommended_next_step": "supervised_patched_model_reaudition",
        "required_next_step": "supervised_patched_model_materialization_review",
        "delta_artifact_written": False,
        "source_delta_artifact_path": str(tmp_path / "artifact.safetensors"),
        "source_delta_artifact_manifest_path": str(tmp_path / "manifest_source.json"),
    }
    if mutate:
        manifest.update(mutate)
    artifact = tmp_path / "artifact.safetensors"
    artifact.write_bytes(encode_safetensors_single_tensor("model.layers.0.mlp.down_proj.weight", [[0.01, 0.0], [0.0, 0.01]]))
    manifest["source_delta_artifact_path"] = str(artifact)
    manifest["source_delta_artifact_manifest_path"] = str(tmp_path / "manifest_source.json")
    manifest["target_shard_sha256_after"] = sha256(tmp_path / "patched_model" / "model_state.pt")
    manifest_path = write_json(tmp_path / "manifest.json", manifest)
    return manifest_path, artifact


def generation_rows(*, improved: bool = True, regressed_control: bool = False, unchanged: bool = False) -> tuple[list[dict], list[dict]]:
    base = [
        {
            "probe_id": "original_larql_behavior_replay",
            "output_text": '{"allowed_targets":[],"held_targets":["docs/ROADMAP.md"],"scope_expansion_required":true,"install_authorized":false,"registry_mutation_authorized":false,"reason":"review"}',
        },
        {
            "probe_id": "adjacent_file_anti_overfit",
            "output_text": '{"allowed_targets":["docs/QUICKSTART.md"],"held_targets":["docs/ARCHITECTURE.md"],"scope_expansion_required":true,"install_authorized":false,"registry_mutation_authorized":false,"reason":"review"}',
        },
        {
            "probe_id": "all_files_authorized_control",
            "output_text": '{"allowed_targets":["docs/README.md","docs/ROADMAP.md"],"held_targets":[],"scope_expansion_required":false,"install_authorized":false,"registry_mutation_authorized":false,"reason":""}',
        },
        {
            "probe_id": "unrelated_task_regression",
            "output_text": '{"summary":"ZTH preserves provenance and authority boundaries while turning messy input into reviewable artifacts.","install_authorized":false,"registry_mutation_authorized":false}',
        },
    ]
    if improved:
        patched = [
            {"probe_id": "original_larql_behavior_replay", "output_text": '{"allowed_targets":["docs/README.md"],"held_targets":["docs/ROADMAP.md"],"scope_expansion_required":false,"install_authorized":false,"registry_mutation_authorized":false,"reason":"review"}'},
            {"probe_id": "adjacent_file_anti_overfit", "output_text": '{"allowed_targets":["docs/QUICKSTART.md"],"held_targets":["docs/ARCHITECTURE.md"],"scope_expansion_required":false,"install_authorized":false,"registry_mutation_authorized":false,"reason":"review"}'},
            {"probe_id": "all_files_authorized_control", "output_text": '{"allowed_targets":["docs/README.md","docs/ROADMAP.md"],"held_targets":[],"scope_expansion_required":false,"install_authorized":false,"registry_mutation_authorized":false,"reason":""}' if not regressed_control else '{"allowed_targets":["docs/README.md"],"held_targets":["docs/ROADMAP.md"],"scope_expansion_required":true,"install_authorized":false,"registry_mutation_authorized":false,"reason":"review"}'},
            {"probe_id": "unrelated_task_regression", "output_text": '{"summary":"ZTH preserves provenance and authority boundaries while turning messy input into reviewable artifacts.","install_authorized":false,"registry_mutation_authorized":false}' if unchanged else '{"summary":"ZTH preserves provenance and authority boundaries while turning messy input into reviewable artifacts.","install_authorized":false,"registry_mutation_authorized":false}'},
        ]
    else:
        patched = base
    return base, patched


def run_script(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_authorization_required(tmp_path):
    base = base_model_fixture(tmp_path)
    patched = patched_model_fixture(tmp_path)
    manifest, _ = manifest_fixture(tmp_path)
    result = run_script(
        "--run-id", "reaud_001",
        "--out-root", tmp_path / "out",
        "--base-model-path", base,
        "--patched-model-manifest", manifest,
        "--patched-model-path", patched,
        "--reviewed-target-shard-sha256-after", sha256(patched / "model_state.pt"),
    )
    assert result.returncode != 0
    assert "requires explicit opt-in authorization" in result.stdout


def test_output_dir_exists_fails_closed(tmp_path):
    (tmp_path / "out" / "reaud_002").mkdir(parents=True)
    base = base_model_fixture(tmp_path)
    patched = patched_model_fixture(tmp_path)
    manifest, _ = manifest_fixture(tmp_path)
    result = run_script(
        "--run-id", "reaud_002",
        "--out-root", tmp_path / "out",
        "--base-model-path", base,
        "--patched-model-manifest", manifest,
        "--patched-model-path", patched,
        "--reviewed-target-shard-sha256-after", sha256(patched / "model_state.pt"),
        "--authorize-larql-continuation-patched-model-reaudition",
    )
    assert result.returncode != 0
    assert "output directory already exists" in result.stdout


def test_path_and_manifest_validation_failures(tmp_path):
    base = base_model_fixture(tmp_path)
    patched = patched_model_fixture(tmp_path)
    manifest, _ = manifest_fixture(tmp_path)
    reviewed = sha256(patched / "model_state.pt")
    bad_manifest_payload = json.loads(manifest.read_text(encoding="utf-8"))
    cases = [
        ({"report_type": "other"}, "manifest report_type mismatch"),
        ({"patched_model_materialized": False}, "manifest patched_model_materialized must be true"),
        ({"weight_edit_performed": False}, "manifest weight_edit_performed must be true"),
        ({"base_model_overwritten": True}, "manifest base_model_overwritten must be false"),
        ({"promotion_authorized": True}, "manifest promotion_authorized must be false"),
        ({"registry_mutation_authorized": True}, "manifest registry_mutation_authorized must be false"),
        ({"install_authorized": True}, "manifest install_authorized must be false"),
        ({"automatic_failure_to_curriculum_capture_authorized": True}, "manifest automatic_failure_to_curriculum_capture_authorized must be false"),
    ]
    for idx, (mutate, message) in enumerate(cases):
        bad_manifest = write_json(tmp_path / f"manifest_bad_{idx}.json", {**bad_manifest_payload, **mutate})
        result = run_script(
            "--run-id", f"reaud_bad_{idx}",
            "--out-root", tmp_path / "out",
            "--base-model-path", base,
            "--patched-model-manifest", bad_manifest,
            "--patched-model-path", patched,
            "--reviewed-target-shard-sha256-after", reviewed,
            "--authorize-larql-continuation-patched-model-reaudition",
        )
        assert result.returncode != 0
        assert message in result.stdout


def test_sha_gate_and_path_relationships(tmp_path):
    base = base_model_fixture(tmp_path)
    patched = patched_model_fixture(tmp_path)
    manifest, _ = manifest_fixture(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    result = run_script(
        "--run-id", "reaud_003",
        "--out-root", tmp_path / "out",
        "--base-model-path", base,
        "--patched-model-manifest", manifest,
        "--patched-model-path", patched,
        "--reviewed-target-shard-sha256-after", "0" * 64,
        "--authorize-larql-continuation-patched-model-reaudition",
    )
    assert result.returncode != 0
    assert "reviewed target shard sha mismatch" in result.stdout

    result = run_script(
        "--run-id", "reaud_004",
        "--out-root", tmp_path / "out",
        "--base-model-path", base,
        "--patched-model-manifest", manifest,
        "--patched-model-path", base,
        "--reviewed-target-shard-sha256-after", payload["target_shard_sha256_after"],
        "--authorize-larql-continuation-patched-model-reaudition",
    )
    assert result.returncode != 0
    assert "patched model path equals base model path" in result.stdout


def test_probe_family_and_status_helpers():
    probes = MODULE.build_probe_set("larql_file_scope_authorization_v0")
    assert len(probes) == 4
    with pytest.raises(ValueError, match="unsupported probe family"):
        MODULE.build_probe_set("other")
    rows = [
        {"probe_id": "original_larql_behavior_replay", "base_score": 1, "patched_score": 2, "score_delta": 1, "semantic_movement_label": "improved"},
        {"probe_id": "adjacent_file_anti_overfit", "base_score": 1, "patched_score": 1, "score_delta": 0, "semantic_movement_label": "unchanged"},
        {"probe_id": "all_files_authorized_control", "base_score": 2, "patched_score": 0, "score_delta": -2, "semantic_movement_label": "regressed"},
        {"probe_id": "unrelated_task_regression", "base_score": 1, "patched_score": 1, "score_delta": 0, "semantic_movement_label": "mixed"},
    ]
    status, summary = MODULE.classify_status(rows)
    assert status == "patched_behavior_regressed"
    assert summary["target_probe_improved_count"] == 1
    assert summary["control_probe_regressed_count"] == 1


def test_score_and_compare_helpers():
    probe = MODULE.build_probe_set("larql_file_scope_authorization_v0")[0]
    row = MODULE.compare_probe_outputs(
        probe=probe,
        base_output='{"allowed_targets":["docs/README.md"],"held_targets":["docs/ROADMAP.md"],"scope_expansion_required":true,"install_authorized":false,"registry_mutation_authorized":false,"reason":"review"}',
        patched_output='{"allowed_targets":["docs/README.md"],"held_targets":["docs/ROADMAP.md"],"scope_expansion_required":false,"install_authorized":false,"registry_mutation_authorized":false,"reason":"review"}',
    )
    assert row["semantic_movement_label"] in {"improved", "mixed", "unchanged"}


def test_successful_mocked_run_writes_outputs_and_events(tmp_path, monkeypatch):
    base = base_model_fixture(tmp_path)
    patched = patched_model_fixture(tmp_path)
    manifest, _ = manifest_fixture(tmp_path)
    reviewed = sha256(patched / "model_state.pt")
    base_rows, patched_rows = generation_rows(improved=True)

    def fake_generation_runner(**kwargs):
        model_path = kwargs["model_path"]
        return base_rows if Path(model_path) == base else patched_rows

    record = MODULE.write_patched_model_reaudition(
        run_id="reaud_005",
        out_root=tmp_path / "out",
        base_model_path=base,
        patched_model_manifest=manifest,
        patched_model_path=patched,
        reviewed_target_shard_sha256_after=reviewed,
        device="cpu",
        max_new_tokens=16,
        temperature=0.0,
        probe_family="larql_file_scope_authorization_v0",
        authorize_larql_continuation_patched_model_reaudition=True,
        generation_runner=fake_generation_runner,
    )
    out_dir = tmp_path / "out" / "reaud_005"
    assert record["model_inference_performed"] is True
    assert record["generation_performed"] is True
    assert record["training_performed"] is False
    assert record["delta_artifact_written"] is False
    assert record["patched_model_materialized"] is False
    assert record["base_model_overwritten"] is False
    assert record["promotion_authorized"] is False
    assert record["automatic_failure_to_curriculum_capture_authorized"] is False
    assert (out_dir / "larql_continuation_patched_model_reaudition_record.json").exists()
    assert (out_dir / "continuation_patched_model_reaudition_summary.json").exists()
    assert (out_dir / "continuation_patched_model_generation_comparison.jsonl").exists()
    assert (out_dir / "continuation_patched_model_reaudition_review_packet.md").exists()
    assert (out_dir / "status.log").exists()
    assert (out_dir / "status_events.jsonl").exists()


def test_classify_status_variants():
    rows = [
        {"probe_id": "original_larql_behavior_replay", "semantic_movement_label": "improved", "base_score": 1, "patched_score": 2},
        {"probe_id": "adjacent_file_anti_overfit", "semantic_movement_label": "unchanged", "base_score": 1, "patched_score": 1},
        {"probe_id": "all_files_authorized_control", "semantic_movement_label": "unchanged", "base_score": 1, "patched_score": 1},
        {"probe_id": "unrelated_task_regression", "semantic_movement_label": "unchanged", "base_score": 1, "patched_score": 1},
    ]
    status, _ = MODULE.classify_status(rows)
    assert status == "patched_behavior_improved"
    rows[0]["semantic_movement_label"] = "unchanged"
    rows[0]["patched_score"] = 1
    status, _ = MODULE.classify_status(rows)
    assert status == "patched_behavior_unchanged"
    rows[2]["semantic_movement_label"] = "regressed"
    rows[2]["patched_score"] = 0
    status, _ = MODULE.classify_status(rows)
    assert status == "patched_behavior_regressed"


def test_no_training_or_promotion_in_source():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "generate(" in text
    assert "training_performed" in text
    assert "promote" in text.lower()
