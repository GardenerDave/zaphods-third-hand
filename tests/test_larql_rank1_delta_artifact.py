from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/larql_rank1_delta_artifact.py"


def write_json(path: Path, payload: dict | list) -> Path:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def activation_capture_record_payload() -> dict:
    return {
        "report_type": "larql_activation_capture_probe.v0",
        "compact_vectors_written": True,
    }


def delta_design_packet_payload(*, status: str = "delta_design_reviewable") -> dict:
    return {
        "report_type": "larql_delta_design_packet.v0",
        "delta_design_status": status,
        "selected_vector_source": "prompt_mean_pool",
        "target_module": "model.layers.0.mlp.down_proj.weight",
        "target_layer": "0",
        "target_module_family": "mlp_projection",
        "target_module_override_used": False,
        "source_vector_target_module": "model.layers.0.mlp.down_proj.weight",
        "source_vector_target_layer": "0",
        "source_vector_target_module_family": "mlp_projection",
        "output_vector_length": 2,
        "input_vector_length": 3,
        "proposed_delta_shape": [2, 3],
    }


def rank1_delta_design_payload() -> dict:
    return {
        "rank": 1,
        "writes_tensor_artifact": False,
    }


def compact_rows() -> list[dict]:
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
    }
    rows = []
    for probe_id, spec in probe_specs.items():
        rows.append(
            {
                "probe_id": probe_id,
                "side": "failure",
                "prompt_mean_pool_vector": spec["failure_out"],
                "prompt_mean_pool_input_vector": spec["failure_in"],
            }
        )
        rows.append(
            {
                "probe_id": probe_id,
                "side": "correction",
                "prompt_mean_pool_vector": spec["correction_out"],
                "prompt_mean_pool_input_vector": spec["failure_in"],
            }
        )
    return rows


def prepare_inputs(tmp_path: Path, *, design_status: str = "delta_design_reviewable") -> tuple[Path, Path, Path, Path]:
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    capture = write_json(input_dir / "larql_activation_capture_probe.json", activation_capture_record_payload())
    packet = write_json(input_dir / "larql_delta_design_packet.json", delta_design_packet_payload(status=design_status))
    design = write_json(input_dir / "rank1_delta_design.json", rank1_delta_design_payload())
    compact = input_dir / "compact_prompt_vectors.jsonl"
    compact.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in compact_rows()) + "\n",
        encoding="utf-8",
    )
    return capture, packet, design, compact


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


def test_missing_authorization_exits_nonzero_and_writes_no_artifact(tmp_path):
    capture, packet, design, compact = prepare_inputs(tmp_path)
    out_root = tmp_path / "out"
    result = run_script(
        "--run-id", "artifact_001",
        "--out-root", out_root,
        "--compact-vectors", compact,
        "--delta-design-packet", packet,
        "--rank1-delta-design", design,
        "--source-activation-capture-record", capture,
        "--delta-scale", "0.01",
    )
    assert result.returncode != 0
    assert "requires explicit opt-in authorization" in result.stdout
    assert not (out_root / "artifact_001/larql_rank1_delta_artifact_record.json").exists()


def test_zero_or_negative_delta_scale_is_rejected(tmp_path):
    capture, packet, design, compact = prepare_inputs(tmp_path)
    out_root = tmp_path / "out"
    for scale in ["0", "-0.1"]:
        result = run_script(
            "--run-id", f"artifact_bad_{scale.replace('-', 'n').replace('.', '_')}",
            "--out-root", out_root,
            "--compact-vectors", compact,
            "--delta-design-packet", packet,
            "--rank1-delta-design", design,
            "--source-activation-capture-record", capture,
            "--delta-scale", scale,
            "--authorize-larql-rank1-delta-artifact",
        )
        assert result.returncode != 0
        assert "delta scale must be positive" in result.stdout


def test_non_reviewable_delta_design_is_rejected(tmp_path):
    capture, packet, design, compact = prepare_inputs(tmp_path, design_status="delta_design_unclear")
    out_root = tmp_path / "out"
    result = run_script(
        "--run-id", "artifact_002",
        "--out-root", out_root,
        "--compact-vectors", compact,
        "--delta-design-packet", packet,
        "--rank1-delta-design", design,
        "--source-activation-capture-record", capture,
        "--delta-scale", "0.01",
        "--authorize-larql-rank1-delta-artifact",
    )
    assert result.returncode != 0
    assert "delta design packet must be reviewable" in result.stdout


def test_valid_fixture_writes_record_and_one_tensor_artifact(tmp_path):
    capture, packet, design, compact = prepare_inputs(tmp_path)
    out_root = tmp_path / "out"
    result = run_script(
        "--run-id", "artifact_003",
        "--out-root", out_root,
        "--compact-vectors", compact,
        "--delta-design-packet", packet,
        "--rank1-delta-design", design,
        "--source-activation-capture-record", capture,
        "--delta-scale", "0.01",
        "--authorize-larql-rank1-delta-artifact",
    )
    assert result.returncode == 0
    out_dir = out_root / "artifact_003"
    record = json.loads((out_dir / "larql_rank1_delta_artifact_record.json").read_text(encoding="utf-8"))
    assert record["report_type"] == "larql_rank1_delta_artifact.v0"
    assert record["delta_artifact_written"] is True
    assert record["model_inference_performed"] is False
    assert record["weight_edit_performed"] is False
    assert record["patched_model_materialized"] is False
    assert record["training_performed"] is False
    assert record["adapter_baseline_path"] is False
    assert record["promotion_authorized"] is False
    assert record["base_model_overwrite_authorized"] is False
    assert record["automatic_failure_to_curriculum_capture_authorized"] is False
    assert record["delta_shape"] == [2, 3]
    assert record["delta_rank"] == 1
    assert record["artifact_sha256"]
    artifact_path = Path(record["artifact_path"])
    assert artifact_path.exists()
    assert artifact_path.parent == out_dir
    assert not (out_dir / "patched_model").exists()


def test_artifact_writer_carries_overridden_target_module_into_record(tmp_path):
    capture, packet, design, compact = prepare_inputs(tmp_path)
    packet_payload = json.loads(packet.read_text(encoding="utf-8"))
    packet_payload["target_module"] = "model.layers.14.mlp.down_proj.weight"
    packet_payload["target_layer"] = "14"
    packet_payload["target_module_override_used"] = True
    write_json(packet, packet_payload)
    out_root = tmp_path / "out"
    result = run_script(
        "--run-id", "artifact_003_override",
        "--out-root", out_root,
        "--compact-vectors", compact,
        "--delta-design-packet", packet,
        "--rank1-delta-design", design,
        "--source-activation-capture-record", capture,
        "--delta-scale", "0.01",
        "--authorize-larql-rank1-delta-artifact",
    )
    assert result.returncode == 0
    record = json.loads((out_root / "artifact_003_override/larql_rank1_delta_artifact_record.json").read_text(encoding="utf-8"))
    assert record["target_module"] == "model.layers.14.mlp.down_proj.weight"
    assert record["target_layer"] == "14"
    assert record["target_module_family"] == "mlp_projection"


def test_no_real_inference_or_model_directory_is_written():
    script_text = SCRIPT.read_text(encoding="utf-8")
    assert "transformers" not in script_text
