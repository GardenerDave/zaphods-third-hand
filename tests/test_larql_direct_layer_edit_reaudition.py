from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/larql_direct_layer_edit_reaudition.py"


def smoke_payload() -> dict:
    return {
        "report_type": "larql_direct_layer_edit_smoke.v0",
        "smoke_status": "completed_patched_model_copy",
        "model_modification_method": "LARQL",
        "persistence_mechanism": "direct_layer_weight_edit",
        "selected_mechanism": "single_module_projection_delta",
        "selected_module_family": "mlp_projection",
        "target_tensor_key": "model.layers.0.mlp.down_proj.weight",
        "direct_delta_artifact_written": True,
        "weight_edit_performed": True,
        "model_artifact_written": True,
        "effective_patch_applied": True,
        "patched_model_path": "patched/model",
        "direct_delta_path": "delta/direct_delta.safetensors",
        "base_model_overwrite_authorized": False,
        "irreversible_patch_authorized": False,
        "adapter_merge_authorized": False,
        "production_deployment_authorized": False,
        "runtime_rule_install_authorized": False,
        "registry_mutation_authorized": False,
        "install_authorized": False,
        "dataset_release_authorized": False,
        "automatic_failure_to_curriculum_capture_authorized": False,
        "required_next_step": "supervised_direct_layer_edit_reaudition",
        "base_model_path": "base/model",
    }


def write_json(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


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


def test_missing_authorization_exits_nonzero_and_writes_no_files(tmp_path):
    smoke = write_json(tmp_path / "smoke.json", smoke_payload())
    out_root = tmp_path / "out"
    result = run_script(
        "--direct-layer-edit-smoke", smoke,
        "--run-id", "reaudition_001",
        "--out-root", out_root,
    )
    assert result.returncode != 0
    assert "requires explicit opt-in authorization" in result.stdout
    assert not (out_root / "reaudition_001/larql_direct_layer_edit_reaudition.json").exists()


def test_rejects_source_smoke_when_effective_patch_applied_false(tmp_path):
    payload = smoke_payload()
    payload["effective_patch_applied"] = False
    result = run_script(
        "--direct-layer-edit-smoke", write_json(tmp_path / "smoke.json", payload),
        "--run-id", "reaudition_002",
        "--out-root", tmp_path / "out",
        "--authorize-larql-direct-layer-edit-reaudition",
    )
    assert result.returncode != 0


def test_rejects_source_smoke_when_model_artifact_written_false(tmp_path):
    payload = smoke_payload()
    payload["model_artifact_written"] = False
    result = run_script(
        "--direct-layer-edit-smoke", write_json(tmp_path / "smoke.json", payload),
        "--run-id", "reaudition_003",
        "--out-root", tmp_path / "out",
        "--authorize-larql-direct-layer-edit-reaudition",
    )
    assert result.returncode != 0


def test_rejects_source_smoke_when_status_not_completed_patched_model_copy(tmp_path):
    payload = smoke_payload()
    payload["smoke_status"] = "completed_direct_delta_artifact"
    result = run_script(
        "--direct-layer-edit-smoke", write_json(tmp_path / "smoke.json", payload),
        "--run-id", "reaudition_004",
        "--out-root", tmp_path / "out",
        "--authorize-larql-direct-layer-edit-reaudition",
    )
    assert result.returncode != 0


def test_authorized_packet_only_run_writes_all_required_packet_files(tmp_path):
    smoke = write_json(tmp_path / "smoke.json", smoke_payload())
    out_root = tmp_path / "out"
    result = run_script(
        "--direct-layer-edit-smoke", smoke,
        "--run-id", "reaudition_005",
        "--out-root", out_root,
        "--authorize-larql-direct-layer-edit-reaudition",
    )
    assert result.returncode == 0
    out_dir = out_root / "reaudition_005"
    for name in [
        "larql_direct_layer_edit_reaudition.json",
        "probe_set.json",
        "scoring_plan.json",
        "reaudition_packet.md",
        "boundary.md",
    ]:
        assert (out_dir / name).exists()
    record = json.loads((out_dir / "larql_direct_layer_edit_reaudition.json").read_text(encoding="utf-8"))
    assert record["reaudition_status"] == "packet_prepared"
    assert record["model_inference_performed"] is False


def test_run_inference_without_authorization_sets_blocked_status(tmp_path):
    smoke = write_json(tmp_path / "smoke.json", smoke_payload())
    out_root = tmp_path / "out"
    result = run_script(
        "--direct-layer-edit-smoke", smoke,
        "--run-id", "reaudition_006",
        "--out-root", out_root,
        "--run-inference",
        "--authorize-larql-direct-layer-edit-reaudition",
    )
    assert result.returncode == 0
    record = json.loads((out_root / "reaudition_006/larql_direct_layer_edit_reaudition.json").read_text(encoding="utf-8"))
    assert record["reaudition_status"] == "blocked_inference_not_authorized"


def test_all_authority_flags_remain_false(tmp_path):
    from local_harness.larql_direct_layer_edit_reaudition import write_reaudition

    record = write_reaudition(
        write_json(tmp_path / "smoke.json", smoke_payload()),
        "reaudition_007",
        tmp_path / "out",
        authorize_larql_direct_layer_edit_reaudition=True,
    )
    for key in [
        "promotion_authorized",
        "base_model_overwrite_authorized",
        "adapter_merge_authorized",
        "production_deployment_authorized",
        "runtime_rule_install_authorized",
        "registry_mutation_authorized",
        "install_authorized",
        "dataset_release_authorized",
        "automatic_failure_to_curriculum_capture_authorized",
    ]:
        assert record[key] is False


def test_probe_set_contains_four_required_probes(tmp_path):
    from local_harness.larql_direct_layer_edit_reaudition import write_reaudition

    write_reaudition(
        write_json(tmp_path / "smoke.json", smoke_payload()),
        "reaudition_008",
        tmp_path / "out",
        authorize_larql_direct_layer_edit_reaudition=True,
    )
    probes = json.loads((tmp_path / "out/reaudition_008/probe_set.json").read_text(encoding="utf-8"))
    ids = {probe["probe_id"] for probe in probes}
    assert {
        "original_larql_behavior_replay",
        "adjacent_file_anti_overfit",
        "all_files_authorized_control",
        "unrelated_task_regression",
    } <= ids


def test_file_scope_probes_require_json_output():
    from local_harness.larql_direct_layer_edit_reaudition import build_probe_set

    probes = {probe["probe_id"]: probe for probe in build_probe_set()}
    for probe_id in [
        "original_larql_behavior_replay",
        "adjacent_file_anti_overfit",
        "all_files_authorized_control",
    ]:
        prompt = probes[probe_id]["prompt"]
        assert "Return only valid JSON" in prompt
        assert '"allowed_targets"' in prompt
        assert '"held_targets"' in prompt


def test_unrelated_regression_probe_requires_json_output():
    from local_harness.larql_direct_layer_edit_reaudition import build_probe_set

    probes = {probe["probe_id"]: probe for probe in build_probe_set()}
    prompt = probes["unrelated_task_regression"]["prompt"]
    assert "Return only valid JSON" in prompt
    assert '"summary"' in prompt


def test_scoring_plan_includes_evidence_not_authority_language(tmp_path):
    from local_harness.larql_direct_layer_edit_reaudition import write_reaudition

    write_reaudition(
        write_json(tmp_path / "smoke.json", smoke_payload()),
        "reaudition_009",
        tmp_path / "out",
        authorize_larql_direct_layer_edit_reaudition=True,
    )
    plan = json.loads((tmp_path / "out/reaudition_009/scoring_plan.json").read_text(encoding="utf-8"))
    assert "evidence, not authority" in plan["note"]


def test_scoring_report_path_present_after_inference(tmp_path, monkeypatch):
    from local_harness import larql_direct_layer_edit_reaudition as mod

    base_model = tmp_path / "base_model"
    patched_model = tmp_path / "patched_model"
    base_model.mkdir()
    patched_model.mkdir()

    smoke = smoke_payload()
    smoke["base_model_path"] = str(base_model)
    smoke["patched_model_path"] = str(patched_model)

    monkeypatch.setattr(mod, "inference_stack_available", lambda: True)
    monkeypatch.setattr(
        mod,
        "run_model_inference",
        lambda *, model_path, probe_set, out_path: out_path.write_text(
            "\n".join(
                json.dumps(
                    {
                        "probe_id": probe["probe_id"],
                        "output": json.dumps(
                            {
                                "allowed_targets": ["docs/README.md", "docs/ROADMAP.md"],
                                "held_targets": [],
                                "scope_expansion_required": False,
                                "install_authorized": False,
                                "registry_mutation_authorized": False,
                                "reason": "ok",
                            }
                            if probe["probe_id"] != "unrelated_task_regression"
                            else {
                                "summary": "ok",
                                "install_authorized": False,
                                "registry_mutation_authorized": False,
                            }
                        ),
                    },
                    sort_keys=True,
                )
                for probe in probe_set
            )
            + "\n",
            encoding="utf-8",
        ),
    )

    record = mod.write_reaudition(
        write_json(tmp_path / "smoke.json", smoke),
        "reaudition_009b",
        tmp_path / "out",
        authorize_larql_direct_layer_edit_reaudition=True,
        base_model_path=base_model,
        patched_model_path=patched_model,
        run_inference=True,
        authorize_model_inference=True,
    )
    assert record["scoring_report_path"] is not None


def test_mocked_inference_path_writes_outputs_and_comparison_report(tmp_path, monkeypatch):
    from local_harness import larql_direct_layer_edit_reaudition as mod

    base_model = tmp_path / "base_model"
    patched_model = tmp_path / "patched_model"
    base_model.mkdir()
    patched_model.mkdir()

    smoke = smoke_payload()
    smoke["base_model_path"] = str(base_model)
    smoke["patched_model_path"] = str(patched_model)

    def fake_stack():
        return True

    def fake_run_model_inference(*, model_path: Path, probe_set: list[dict[str, Any]], out_path: Path) -> None:
        tag = "base" if model_path == base_model else "patched"
        rows = []
        for probe in probe_set:
            if probe["probe_id"] == "unrelated_task_regression":
                payload = {
                    "summary": f"{tag} summary",
                    "install_authorized": False,
                    "registry_mutation_authorized": False,
                }
            elif probe["probe_id"] == "all_files_authorized_control":
                payload = {
                    "allowed_targets": ["docs/README.md", "docs/ROADMAP.md"],
                    "held_targets": [],
                    "scope_expansion_required": False,
                    "install_authorized": False,
                    "registry_mutation_authorized": False,
                    "reason": f"{tag} ok",
                }
            else:
                payload = {
                    "allowed_targets": ["docs/README.md"] if probe["probe_id"] == "original_larql_behavior_replay" else ["docs/QUICKSTART.md"],
                    "held_targets": ["docs/ROADMAP.md", "adjacent docs", "generated files"] if probe["probe_id"] == "original_larql_behavior_replay" else ["docs/ARCHITECTURE.md"],
                    "scope_expansion_required": True,
                    "install_authorized": False,
                    "registry_mutation_authorized": False,
                    "reason": f"{tag} constrained",
                }
            rows.append({"probe_id": probe["probe_id"], "output": json.dumps(payload)})
        out_path.write_text(
            "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
            encoding="utf-8",
        )

    monkeypatch.setattr(mod, "inference_stack_available", fake_stack)
    monkeypatch.setattr(mod, "run_model_inference", fake_run_model_inference)

    record = mod.write_reaudition(
        write_json(tmp_path / "smoke.json", smoke),
        "reaudition_010",
        tmp_path / "out",
        authorize_larql_direct_layer_edit_reaudition=True,
        base_model_path=base_model,
        patched_model_path=patched_model,
        run_inference=True,
        authorize_model_inference=True,
    )
    assert record["reaudition_status"] == "completed_model_comparison"
    assert record["model_inference_performed"] is True
    assert record["base_outputs_path"] is not None
    assert record["patched_outputs_path"] is not None
    assert record["comparison_report_path"] is not None
    assert record["scoring_report_path"] is not None
    assert Path(record["base_outputs_path"]).exists()
    assert Path(record["patched_outputs_path"]).exists()
    assert Path(record["comparison_report_path"]).exists()
    assert Path(record["scoring_report_path"]).exists()
    scoring = json.loads(Path(record["scoring_report_path"]).read_text(encoding="utf-8"))
    assert scoring["evidence_only"] is True
    assert scoring["promotion_authorized"] is False
    assert scoring["automatic_failure_to_curriculum_capture_authorized"] is False
