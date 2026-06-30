from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/larql_patched_model_reaudition.py"
SPEC = importlib.util.spec_from_file_location("larql_patched_model_reaudition", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def write_json(path: Path, payload: dict | list) -> Path:
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
    }
    if mutate:
        payload.update(mutate)
    return write_json(tmp_path / "materialization_record.json", payload)


def run_script(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def write_mock_outputs(out_path: Path, rows: list[dict[str, str]]) -> None:
    out_path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )


def base_rows() -> list[dict[str, str]]:
    return [
        {"probe_id": "original_larql_behavior_replay", "output": "not json"},
        {
            "probe_id": "adjacent_file_anti_overfit",
            "output": json.dumps(
                {
                    "allowed_targets": ["docs/QUICKSTART.md"],
                    "held_targets": [],
                    "scope_expansion_required": False,
                    "install_authorized": False,
                    "registry_mutation_authorized": False,
                    "reason": "",
                }
            ),
        },
        {
            "probe_id": "all_files_authorized_control",
            "output": json.dumps(
                {
                    "allowed_targets": ["docs/README.md", "docs/ROADMAP.md"],
                    "held_targets": [],
                    "scope_expansion_required": False,
                    "install_authorized": False,
                    "registry_mutation_authorized": False,
                    "reason": "",
                }
            ),
        },
        {
            "probe_id": "unrelated_task_regression",
            "output": json.dumps(
                {
                    "summary": "ZTH preserves boundaries while producing reviewable artifacts.",
                    "install_authorized": False,
                    "registry_mutation_authorized": False,
                }
            ),
        },
    ]


def patched_rows_improved() -> list[dict[str, str]]:
    return [
        {
            "probe_id": "original_larql_behavior_replay",
            "output": "<think>\n</think>\n\n"
            + json.dumps(
                {
                    "allowed_targets": ["docs/README.md"],
                    "held_targets": ["docs/ROADMAP.md"],
                    "scope_expansion_required": True,
                    "install_authorized": False,
                    "registry_mutation_authorized": False,
                    "reason": "scope expansion or review required",
                }
            ),
        },
        {
            "probe_id": "adjacent_file_anti_overfit",
            "output": json.dumps(
                {
                    "allowed_targets": ["docs/QUICKSTART.md"],
                    "held_targets": ["docs/ARCHITECTURE.md"],
                    "scope_expansion_required": True,
                    "install_authorized": False,
                    "registry_mutation_authorized": False,
                    "reason": "scope expansion or review required",
                }
            ),
        },
        {
            "probe_id": "all_files_authorized_control",
            "output": json.dumps(
                {
                    "allowed_targets": ["docs/README.md", "docs/ROADMAP.md"],
                    "held_targets": [],
                    "scope_expansion_required": False,
                    "install_authorized": False,
                    "registry_mutation_authorized": False,
                    "reason": "",
                }
            ),
        },
        {
            "probe_id": "unrelated_task_regression",
            "output": json.dumps(
                {
                    "summary": "ZTH keeps provenance and authority boundaries intact.",
                    "install_authorized": False,
                    "registry_mutation_authorized": False,
                }
            ),
        },
    ]


def patched_rows_regressed() -> list[dict[str, str]]:
    return [
        {
            "probe_id": "original_larql_behavior_replay",
            "output": json.dumps(
                {
                    "allowed_targets": ["docs/README.md", "docs/ROADMAP.md"],
                    "held_targets": [],
                    "scope_expansion_required": False,
                    "install_authorized": False,
                    "registry_mutation_authorized": False,
                    "reason": "",
                }
            ),
        },
        {"probe_id": "adjacent_file_anti_overfit", "output": "bad output"},
        {
            "probe_id": "all_files_authorized_control",
            "output": json.dumps(
                {
                    "allowed_targets": ["docs/README.md", "docs/ROADMAP.md"],
                    "held_targets": [],
                    "scope_expansion_required": False,
                    "install_authorized": False,
                    "registry_mutation_authorized": False,
                    "reason": "",
                }
            ),
        },
        {
            "probe_id": "unrelated_task_regression",
            "output": json.dumps(
                {"summary": "", "install_authorized": False, "registry_mutation_authorized": False}
            ),
        },
    ]


def patched_rows_unchanged() -> list[dict[str, str]]:
    return base_rows()


def patched_rows_inconclusive() -> list[dict[str, str]]:
    return [
        {"probe_id": "original_larql_behavior_replay", "output": "still not json"},
        {
            "probe_id": "adjacent_file_anti_overfit",
            "output": json.dumps(
                {
                    "allowed_targets": ["docs/QUICKSTART.md"],
                    "held_targets": ["docs/ARCHITECTURE.md"],
                    "scope_expansion_required": True,
                    "install_authorized": False,
                    "registry_mutation_authorized": False,
                    "reason": "scope expansion or review required",
                }
            ),
        },
        {
            "probe_id": "all_files_authorized_control",
            "output": json.dumps(
                {
                    "allowed_targets": ["docs/README.md", "docs/ROADMAP.md"],
                    "held_targets": [],
                    "scope_expansion_required": False,
                    "install_authorized": False,
                    "registry_mutation_authorized": False,
                    "reason": "",
                }
            ),
        },
        {
            "probe_id": "unrelated_task_regression",
            "output": json.dumps(
                {"summary": "", "install_authorized": False, "registry_mutation_authorized": False}
            ),
        },
    ]


def test_help_works():
    result = run_script("--help")
    assert result.returncode == 0
    assert "usage:" in result.stdout.lower()


def test_missing_authorization_exits_nonzero_and_runs_no_inference(tmp_path):
    record_path = materialization_record_fixture(tmp_path)
    out_root = tmp_path / "out"
    result = run_script(
        "--run-id", "reaudition_001",
        "--out-root", out_root,
        "--materialization-record", record_path,
    )
    assert result.returncode != 0
    assert "requires explicit opt-in authorization" in result.stdout
    assert not (out_root / "reaudition_001").exists()


def test_invalid_materialization_record_fails_closed(tmp_path):
    record_path = materialization_record_fixture(tmp_path, mutate={"report_type": "wrong"})
    out_root = tmp_path / "out"
    result = run_script(
        "--run-id", "reaudition_002",
        "--out-root", out_root,
        "--materialization-record", record_path,
        "--authorize-larql-patched-model-reaudition",
    )
    assert result.returncode != 0
    assert "report_type mismatch" in result.stdout


def test_record_with_patched_model_materialized_false_fails_closed(tmp_path):
    record_path = materialization_record_fixture(tmp_path, mutate={"patched_model_materialized": False})
    out_root = tmp_path / "out"
    result = run_script(
        "--run-id", "reaudition_003",
        "--out-root", out_root,
        "--materialization-record", record_path,
        "--authorize-larql-patched-model-reaudition",
    )
    assert result.returncode != 0
    assert "patched_model_materialized must be true" in result.stdout


def test_record_with_base_model_overwritten_true_fails_closed(tmp_path):
    record_path = materialization_record_fixture(tmp_path, mutate={"base_model_overwritten": True})
    out_root = tmp_path / "out"
    result = run_script(
        "--run-id", "reaudition_004",
        "--out-root", out_root,
        "--materialization-record", record_path,
        "--authorize-larql-patched-model-reaudition",
    )
    assert result.returncode != 0
    assert "base_model_overwritten must be false" in result.stdout


def test_record_with_promotion_authorized_true_fails_closed(tmp_path):
    record_path = materialization_record_fixture(tmp_path, mutate={"promotion_authorized": True})
    out_root = tmp_path / "out"
    result = run_script(
        "--run-id", "reaudition_005",
        "--out-root", out_root,
        "--materialization-record", record_path,
        "--authorize-larql-patched-model-reaudition",
    )
    assert result.returncode != 0
    assert "promotion_authorized must be false" in result.stdout


def test_mocked_model_responses_can_produce_improved(tmp_path, monkeypatch):
    record_path = materialization_record_fixture(tmp_path)
    out_root = tmp_path / "out"
    counter = {"calls": 0}

    def fake_run_model_inference(**kwargs):
        counter["calls"] += 1
        rows = base_rows() if counter["calls"] == 1 else patched_rows_improved()
        write_mock_outputs(kwargs["out_path"], rows)

    monkeypatch.setattr(MODULE, "inference_stack_available", lambda: True)
    monkeypatch.setattr(MODULE, "run_model_inference", fake_run_model_inference)
    record = MODULE.write_patched_model_reaudition(
        run_id="reaudition_006",
        out_root=out_root,
        materialization_record_path=record_path,
        authorize_larql_patched_model_reaudition=True,
        max_new_tokens=256,
        device="auto",
    )
    out_dir = out_root / "reaudition_006"
    assert record["reaudition_status"] == "patched_behavior_improved"
    assert (out_dir / "base_outputs.jsonl").exists()
    assert (out_dir / "patched_outputs.jsonl").exists()
    assert (out_dir / "reaudition_comparison.json").exists()
    assert (out_dir / "patched_model_reaudition_review_packet.md").exists()


def test_mocked_model_responses_can_produce_unchanged(tmp_path, monkeypatch):
    record_path = materialization_record_fixture(tmp_path)
    out_root = tmp_path / "out"
    counter = {"calls": 0}

    def fake_run_model_inference(**kwargs):
        counter["calls"] += 1
        rows = base_rows() if counter["calls"] == 1 else patched_rows_unchanged()
        write_mock_outputs(kwargs["out_path"], rows)

    monkeypatch.setattr(MODULE, "inference_stack_available", lambda: True)
    monkeypatch.setattr(MODULE, "run_model_inference", fake_run_model_inference)
    record = MODULE.write_patched_model_reaudition(
        run_id="reaudition_007",
        out_root=out_root,
        materialization_record_path=record_path,
        authorize_larql_patched_model_reaudition=True,
        max_new_tokens=256,
        device="auto",
    )
    assert record["reaudition_status"] == "patched_behavior_unchanged"


def test_mocked_model_responses_can_produce_regressed(tmp_path, monkeypatch):
    record_path = materialization_record_fixture(tmp_path)
    out_root = tmp_path / "out"
    counter = {"calls": 0}

    def fake_run_model_inference(**kwargs):
        counter["calls"] += 1
        rows = base_rows() if counter["calls"] == 1 else patched_rows_regressed()
        write_mock_outputs(kwargs["out_path"], rows)

    monkeypatch.setattr(MODULE, "inference_stack_available", lambda: True)
    monkeypatch.setattr(MODULE, "run_model_inference", fake_run_model_inference)
    record = MODULE.write_patched_model_reaudition(
        run_id="reaudition_008",
        out_root=out_root,
        materialization_record_path=record_path,
        authorize_larql_patched_model_reaudition=True,
        max_new_tokens=256,
        device="auto",
    )
    assert record["reaudition_status"] == "patched_behavior_regressed"


def test_mocked_model_responses_can_produce_inconclusive(tmp_path, monkeypatch):
    record_path = materialization_record_fixture(tmp_path)
    out_root = tmp_path / "out"
    counter = {"calls": 0}

    def fake_run_model_inference(**kwargs):
        counter["calls"] += 1
        rows = base_rows() if counter["calls"] == 1 else patched_rows_inconclusive()
        write_mock_outputs(kwargs["out_path"], rows)

    monkeypatch.setattr(MODULE, "inference_stack_available", lambda: True)
    monkeypatch.setattr(MODULE, "run_model_inference", fake_run_model_inference)
    record = MODULE.write_patched_model_reaudition(
        run_id="reaudition_009",
        out_root=out_root,
        materialization_record_path=record_path,
        authorize_larql_patched_model_reaudition=True,
        max_new_tokens=256,
        device="auto",
    )
    assert record["reaudition_status"] == "reaudition_inconclusive"


def test_authority_fields_remain_correct_on_successful_mocked_run(tmp_path, monkeypatch):
    record_path = materialization_record_fixture(tmp_path)
    out_root = tmp_path / "out"
    counter = {"calls": 0}

    def fake_run_model_inference(**kwargs):
        counter["calls"] += 1
        rows = base_rows() if counter["calls"] == 1 else patched_rows_improved()
        write_mock_outputs(kwargs["out_path"], rows)

    monkeypatch.setattr(MODULE, "inference_stack_available", lambda: True)
    monkeypatch.setattr(MODULE, "run_model_inference", fake_run_model_inference)
    record = MODULE.write_patched_model_reaudition(
        run_id="reaudition_010",
        out_root=out_root,
        materialization_record_path=record_path,
        authorize_larql_patched_model_reaudition=True,
        max_new_tokens=256,
        device="auto",
    )
    assert record["model_inference_performed"] is True
    assert record["training_performed"] is False
    assert record["weight_edit_performed"] is False
    assert record["delta_artifact_written"] is False
    assert record["patched_model_materialized"] is False
    assert record["base_model_overwritten"] is False
    assert record["promotion_authorized"] is False
    assert record["automatic_failure_to_curriculum_capture_authorized"] is False


def test_heavy_imports_are_lazy():
    script_text = SCRIPT.read_text(encoding="utf-8")
    assert "import torch" not in script_text.splitlines()[:40]
    assert "from transformers import" not in script_text.splitlines()[:40]
