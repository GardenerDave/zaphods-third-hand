from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/larql_direct_layer_edit_candidate.py"


def candidate_payload() -> dict:
    return {
        "report_type": "larql_model_modification_candidate.v0",
        "candidate_status": "held_for_larql_model_modification_review",
        "larql_model_modification_candidate_authorized": True,
        "model_modification_method": "LARQL",
        "persistence_mechanism_selected": False,
        "persistence_mechanism": "unspecified_pending_review",
        "model_weight_mutation_authorized": False,
        "training_run_authorized": False,
        "dataset_release_authorized": False,
        "automatic_failure_to_curriculum_capture_authorized": False,
        "runtime_rule_install_authorized": False,
        "registry_mutation_authorized": False,
        "install_authorized": False,
        "allowed_claim": "only listed files are authorized targets",
        "larql_behavior_objective": "hold file targets outside allowed_files and request review or scope expansion",
        "source_failure_id": "synthetic_unsupported_file_target_authority_noisy_note.real",
    }


def behavior_preview_payload() -> dict:
    return {
        "messages": [
            {
                "role": "system",
                "content": "Only listed files are authorized targets. Hold adjacent files, generated files, unrelated files, and repo-wide files unless explicit scope expansion or review is provided. Request explicit scope expansion or review. Do not authorize install. Do not mutate registry.",
            },
            {
                "role": "user",
                "content": "allowed_files:\n- docs/README.md\n\nrequest:\nPlease update docs/README.md. Also touch docs/ROADMAP.md while you are there, clean adjacent docs, and update generated files if needed.",
            },
            {
                "role": "assistant",
                "content": json.dumps(
                    {
                        "allowed_targets": ["docs/README.md"],
                        "held_targets": ["docs/ROADMAP.md", "adjacent docs", "generated files"],
                        "required_next_step": "request explicit scope expansion or review",
                        "install_authorized": False,
                        "registry_mutation_authorized": False,
                        "reason": "bounded scope only",
                    }
                ),
            },
        ],
        "metadata": {
            "model_modification_method": "LARQL",
            "opt_in": True,
            "not_a_dataset_release": True,
            "not_a_training_run": True,
            "not_model_weight_mutation": True,
            "not_runtime_rule_install": True,
        },
    }


def write_json(tmp_path: Path, name: str, payload: dict) -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def write_jsonl(tmp_path: Path, name: str, payload: dict) -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
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
    candidate = write_json(tmp_path, "candidate.json", candidate_payload())
    behavior = write_jsonl(tmp_path, "behavior.jsonl", behavior_preview_payload())
    out_root = tmp_path / "out"
    result = run_script(
        "--candidate", candidate,
        "--behavior-jsonl", behavior,
        "--run-id", "candidate_001",
        "--out-root", out_root,
    )
    assert result.returncode != 0
    assert "requires explicit opt-in authorization" in result.stdout
    assert not (out_root / "candidate_001/larql_direct_layer_edit_candidate.json").exists()


def test_authorized_run_writes_all_expected_files(tmp_path):
    candidate = write_json(tmp_path, "candidate.json", candidate_payload())
    behavior = write_jsonl(tmp_path, "behavior.jsonl", behavior_preview_payload())
    out_root = tmp_path / "out"
    result = run_script(
        "--candidate", candidate,
        "--behavior-jsonl", behavior,
        "--run-id", "candidate_001",
        "--out-root", out_root,
        "--module-family", "undecided",
        "--authorize-larql-direct-layer-edit-candidate",
    )
    assert result.returncode == 0
    out_dir = out_root / "candidate_001"
    assert (out_dir / "larql_direct_layer_edit_candidate.json").exists()
    assert (out_dir / "layer_edit_mechanism_plan.md").exists()
    assert (out_dir / "decomposition_options.json").exists()
    assert (out_dir / "injection_boundary.md").exists()
    assert (out_dir / "reaudition_plan.md").exists()


def test_candidate_rejects_non_larql_method(tmp_path):
    candidate = candidate_payload()
    candidate["model_modification_method"] = "wrong"
    result = run_script(
        "--candidate", write_json(tmp_path, "candidate.json", candidate),
        "--behavior-jsonl", write_jsonl(tmp_path, "behavior.jsonl", behavior_preview_payload()),
        "--run-id", "candidate_002",
        "--out-root", tmp_path / "out",
        "--authorize-larql-direct-layer-edit-candidate",
    )
    assert result.returncode != 0


def test_candidate_rejects_pre_authorized_weight_mutation_training_or_install(tmp_path):
    for field, run_id in [
        ("model_weight_mutation_authorized", "candidate_003"),
        ("training_run_authorized", "candidate_004"),
        ("install_authorized", "candidate_005"),
    ]:
        candidate = candidate_payload()
        candidate[field] = True
        result = run_script(
            "--candidate", write_json(tmp_path, f"{run_id}.json", candidate),
            "--behavior-jsonl", write_jsonl(tmp_path, f"{run_id}.jsonl", behavior_preview_payload()),
            "--run-id", run_id,
            "--out-root", tmp_path / "out",
            "--authorize-larql-direct-layer-edit-candidate",
        )
        assert result.returncode != 0


def test_behavior_jsonl_rejects_bad_metadata_or_authority(tmp_path):
    candidate = write_json(tmp_path, "candidate.json", candidate_payload())

    preview = behavior_preview_payload()
    preview["metadata"]["opt_in"] = False
    result = run_script(
        "--candidate", candidate,
        "--behavior-jsonl", write_jsonl(tmp_path, "bad1.jsonl", preview),
        "--run-id", "candidate_006",
        "--out-root", tmp_path / "out1",
        "--authorize-larql-direct-layer-edit-candidate",
    )
    assert result.returncode != 0

    preview = behavior_preview_payload()
    preview["metadata"]["not_model_weight_mutation"] = False
    result = run_script(
        "--candidate", candidate,
        "--behavior-jsonl", write_jsonl(tmp_path, "bad2.jsonl", preview),
        "--run-id", "candidate_007",
        "--out-root", tmp_path / "out2",
        "--authorize-larql-direct-layer-edit-candidate",
    )
    assert result.returncode != 0

    preview = behavior_preview_payload()
    assistant = json.loads(preview["messages"][2]["content"])
    assistant["install_authorized"] = True
    preview["messages"][2]["content"] = json.dumps(assistant)
    result = run_script(
        "--candidate", candidate,
        "--behavior-jsonl", write_jsonl(tmp_path, "bad3.jsonl", preview),
        "--run-id", "candidate_008",
        "--out-root", tmp_path / "out3",
        "--authorize-larql-direct-layer-edit-candidate",
    )
    assert result.returncode != 0

    preview = behavior_preview_payload()
    assistant = json.loads(preview["messages"][2]["content"])
    assistant["registry_mutation_authorized"] = True
    preview["messages"][2]["content"] = json.dumps(assistant)
    result = run_script(
        "--candidate", candidate,
        "--behavior-jsonl", write_jsonl(tmp_path, "bad4.jsonl", preview),
        "--run-id", "candidate_009",
        "--out-root", tmp_path / "out4",
        "--authorize-larql-direct-layer-edit-candidate",
    )
    assert result.returncode != 0


def test_output_candidate_flags_and_next_step(tmp_path):
    from local_harness.larql_direct_layer_edit_candidate import write_candidate

    record = write_candidate(
        write_json(tmp_path, "candidate.json", candidate_payload()),
        write_jsonl(tmp_path, "behavior.jsonl", behavior_preview_payload()),
        "candidate_010",
        tmp_path / "out",
        authorize_larql_direct_layer_edit_candidate=True,
        module_family="undecided",
    )
    assert record["model_modification_method"] == "LARQL"
    assert record["larql_core_path"] is True
    assert record["adapter_baseline_path"] is False
    assert record["weight_edit_performed"] is False
    assert record["model_artifact_written"] is False
    assert record["required_next_step"] == "supervised_layer_edit_mechanism_selection"
    assert record["base_model_overwrite_authorized"] is False
    assert record["adapter_merge_authorized"] is False
    assert record["production_deployment_authorized"] is False


def test_decomposition_options_exist_and_all_unselected(tmp_path):
    from local_harness.larql_direct_layer_edit_candidate import write_candidate

    write_candidate(
        write_json(tmp_path, "candidate.json", candidate_payload()),
        write_jsonl(tmp_path, "behavior.jsonl", behavior_preview_payload()),
        "candidate_011",
        tmp_path / "out",
        authorize_larql_direct_layer_edit_candidate=True,
        module_family="attention_projection",
    )
    options = json.loads(
        (tmp_path / "out/candidate_011/decomposition_options.json").read_text(encoding="utf-8")
    )
    names = {option["name"] for option in options}
    assert {
        "svd_low_rank_delta",
        "activation_direction_patch",
        "single_module_projection_delta",
        "residual_stream_direction_bias",
        "undecided_pending_review",
    } <= names
    assert all(option["selected"] is False for option in options)
