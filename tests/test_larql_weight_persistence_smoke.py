from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/larql_weight_persistence_smoke.py"


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
            "persistence_mechanism_selected": False,
            "opt_in": True,
            "synthetic": True,
            "do_not_auto_promote": True,
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


def test_missing_authorization_exits_nonzero_and_writes_no_training_files(tmp_path):
    candidate = write_json(tmp_path, "candidate.json", candidate_payload())
    behavior = write_jsonl(tmp_path, "behavior.jsonl", behavior_preview_payload())
    out_root = tmp_path / "out"
    result = run_script(
        "--candidate", candidate,
        "--behavior-jsonl", behavior,
        "--run-id", "smoke_001",
        "--out-root", out_root,
    )
    assert result.returncode != 0
    assert "requires explicit opt-in authorization" in result.stdout
    assert not (out_root / "smoke_001/training_input.jsonl").exists()


def test_authorized_run_writes_expected_files(tmp_path):
    candidate = write_json(tmp_path, "candidate.json", candidate_payload())
    behavior = write_jsonl(tmp_path, "behavior.jsonl", behavior_preview_payload())
    out_root = tmp_path / "out"
    result = run_script(
        "--candidate", candidate,
        "--behavior-jsonl", behavior,
        "--run-id", "smoke_001",
        "--out-root", out_root,
        "--authorize-larql-weight-persistence-smoke",
    )
    assert result.returncode == 0
    out_dir = out_root / "smoke_001"
    assert (out_dir / "larql_weight_persistence_smoke.json").exists()
    assert (out_dir / "training_input.jsonl").exists()
    assert (out_dir / "training_stack_preflight.json").exists()
    assert (out_dir / "weight_persistence_handoff.md").exists()
    assert (out_dir / "reaudition_plan.md").exists()


def test_rejects_candidate_if_model_modification_method_is_not_larql(tmp_path):
    candidate = candidate_payload()
    candidate["model_modification_method"] = "wrong"
    candidate_path = write_json(tmp_path, "candidate.json", candidate)
    behavior_path = write_jsonl(tmp_path, "behavior.jsonl", behavior_preview_payload())
    result = run_script(
        "--candidate", candidate_path,
        "--behavior-jsonl", behavior_path,
        "--run-id", "smoke_001",
        "--out-root", tmp_path / "out",
        "--authorize-larql-weight-persistence-smoke",
    )
    assert result.returncode != 0


def test_rejects_candidate_if_training_run_authorized_is_already_true(tmp_path):
    candidate = candidate_payload()
    candidate["training_run_authorized"] = True
    candidate_path = write_json(tmp_path, "candidate2.json", candidate)
    behavior_path = write_jsonl(tmp_path, "behavior.jsonl", behavior_preview_payload())
    result = run_script(
        "--candidate", candidate_path,
        "--behavior-jsonl", behavior_path,
        "--run-id", "smoke_002",
        "--out-root", tmp_path / "out2",
        "--authorize-larql-weight-persistence-smoke",
    )
    assert result.returncode != 0


def test_rejects_candidate_if_model_weight_mutation_authorized_is_already_true(tmp_path):
    candidate = candidate_payload()
    candidate["model_weight_mutation_authorized"] = True
    candidate_path = write_json(tmp_path, "candidate3.json", candidate)
    behavior_path = write_jsonl(tmp_path, "behavior.jsonl", behavior_preview_payload())
    result = run_script(
        "--candidate", candidate_path,
        "--behavior-jsonl", behavior_path,
        "--run-id", "smoke_003",
        "--out-root", tmp_path / "out3",
        "--authorize-larql-weight-persistence-smoke",
    )
    assert result.returncode != 0


def test_rejects_jsonl_if_opt_in_is_not_true(tmp_path):
    bad_preview = behavior_preview_payload()
    bad_preview["metadata"]["opt_in"] = False
    behavior_path = write_jsonl(tmp_path, "behavior_bad.jsonl", bad_preview)
    result = run_script(
        "--candidate", write_json(tmp_path, "candidate4.json", candidate_payload()),
        "--behavior-jsonl", behavior_path,
        "--run-id", "smoke_004",
        "--out-root", tmp_path / "out4",
        "--authorize-larql-weight-persistence-smoke",
    )
    assert result.returncode != 0


def test_rejects_jsonl_if_assistant_authorizes_install(tmp_path):
    bad_preview = behavior_preview_payload()
    assistant = json.loads(bad_preview["messages"][2]["content"])
    assistant["install_authorized"] = True
    bad_preview["messages"][2]["content"] = json.dumps(assistant)
    behavior_path = write_jsonl(tmp_path, "behavior_bad2.jsonl", bad_preview)
    result = run_script(
        "--candidate", write_json(tmp_path, "candidate5.json", candidate_payload()),
        "--behavior-jsonl", behavior_path,
        "--run-id", "smoke_005",
        "--out-root", tmp_path / "out5",
        "--authorize-larql-weight-persistence-smoke",
    )
    assert result.returncode != 0


def test_smoke_json_fields_and_boundaries(tmp_path):
    from local_harness.larql_weight_persistence_smoke import write_smoke

    candidate = write_json(tmp_path, "candidate.json", candidate_payload())
    behavior = write_jsonl(tmp_path, "behavior.jsonl", behavior_preview_payload())
    smoke = write_smoke(
        candidate,
        behavior,
        "smoke_001",
        tmp_path / "out",
        authorize_larql_weight_persistence_smoke=True,
    )
    assert smoke["report_type"] == "larql_weight_persistence_smoke.v0"
    assert smoke["model_modification_method"] == "LARQL"
    assert smoke["persistence_mechanism"] == "adapter_weight_delta_smoke"
    assert smoke["persistence_mechanism_selected"] is True
    assert smoke["persistence_mechanism_selection_scope"] == "single smoke run only"
    assert smoke["training_run_requested"] is False
    assert smoke["training_run_performed"] is False
    assert smoke["runtime_rule_install_authorized"] is False
    assert smoke["registry_mutation_authorized"] is False
    assert smoke["install_authorized"] is False
    assert smoke["dataset_release_authorized"] is False
    assert smoke["automatic_failure_to_curriculum_capture_authorized"] is False
    assert smoke["base_model_overwrite_authorized"] is False
    assert smoke["adapter_merge_authorized"] is False
    assert smoke["production_deployment_authorized"] is False


def test_training_input_and_preflight_written_without_training(tmp_path):
    candidate = write_json(tmp_path, "candidate.json", candidate_payload())
    behavior = write_jsonl(tmp_path, "behavior.jsonl", behavior_preview_payload())
    out_root = tmp_path / "out"
    result = run_script(
        "--candidate", candidate,
        "--behavior-jsonl", behavior,
        "--run-id", "smoke_001",
        "--out-root", out_root,
        "--authorize-larql-weight-persistence-smoke",
    )
    assert result.returncode == 0
    out_dir = out_root / "smoke_001"
    preview_line = (out_dir / "training_input.jsonl").read_text(encoding="utf-8").strip()
    preview_payload = json.loads(preview_line)
    assert preview_payload["metadata"]["model_modification_method"] == "LARQL"
    assert preview_payload["metadata"]["persistence_mechanism_selected"] is False
    assert preview_payload["metadata"]["opt_in"] is True
    assert preview_payload["metadata"]["synthetic"] is True
    assert preview_payload["metadata"]["do_not_auto_promote"] is True
    assert preview_payload["metadata"]["not_a_dataset_release"] is True
    assert preview_payload["metadata"]["not_a_training_run"] is True
    assistant = json.loads(preview_payload["messages"][2]["content"])
    assert "docs/ROADMAP.md" in assistant["held_targets"]
    assert assistant["install_authorized"] is False
    assert assistant["registry_mutation_authorized"] is False
    preflight = json.loads((out_dir / "training_stack_preflight.json").read_text(encoding="utf-8"))
    assert "torch_available" in preflight
    assert "transformers_available" in preflight
    assert "datasets_available" in preflight
    assert "peft_available" in preflight


def test_run_training_without_base_model_writes_blocked_summary(tmp_path):
    candidate = write_json(tmp_path, "candidate.json", candidate_payload())
    behavior = write_jsonl(tmp_path, "behavior.jsonl", behavior_preview_payload())
    out_root = tmp_path / "out"
    result = run_script(
        "--candidate", candidate,
        "--behavior-jsonl", behavior,
        "--run-id", "smoke_001",
        "--out-root", out_root,
        "--authorize-larql-weight-persistence-smoke",
        "--run-training",
    )
    assert result.returncode == 0
    summary = json.loads((out_root / "smoke_001/training_run_summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "blocked_missing_base_model"
    assert summary["training_run_performed"] is False
