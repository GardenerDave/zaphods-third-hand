from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from local_harness.transaction_handoff import (
    NEXT_WORKER_CONTEXT_SCHEMA,
    TRANSACTION_MANIFEST_SCHEMA,
    TransactionHandoffError,
    build_transaction_handoff_artifacts,
    derive_lifecycle_state,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness" / "run_manual_supervised_attempt.py"


def run_script(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def _valid_raw_output_json() -> str:
    return json.dumps(
        {
            "allowed_targets": ["docs/reports/"],
            "held_targets": [
                "production automation",
                "automatic curriculum capture",
                "automatic promotion",
                "implementation_packet",
            ],
            "scope_expansion_required": False,
            "claims": [
                "The request is a design-planning task involving LoRA and prompt injection.",
                "docs/reports/ is the only allowed target in this packet.",
            ],
            "evidence_basis": [
                "Task summary mentions matched keywords: lora, prompt injection.",
                "Allowed Targets lists docs/reports/.",
            ],
            "unverified_claims": [],
            "format": "json",
            "required_fields_present": True,
            "reason": "The output remains bounded and supervised.",
        }
    )


def _prepare_and_accept_run(tmp_path: Path, *, timestamp: str = "20260707T101010Z") -> Path:
    out_dir = tmp_path / "runs"
    prep = run_script(
        "prepare",
        "--messy-input",
        "The LoRA and prompt injection work got messy. Build a bounded design packet.",
        "--out-dir",
        out_dir,
        "--timestamp",
        timestamp,
    )
    assert prep.returncode == 0
    run_dir = out_dir / timestamp
    raw_output = tmp_path / "raw_model_output.txt"
    raw_output.write_text(_valid_raw_output_json(), encoding="utf-8")
    ingest = run_script(
        "ingest",
        "--run-dir",
        run_dir,
        "--raw-output-file",
        raw_output,
        "--decision",
        "accepted",
        "--decision-reason",
        "Output satisfies the contract and remains within scope.",
        "--operator",
        "manual",
        "--next-worker",
        "qwen3-30b",
    )
    assert ingest.returncode == 0
    return run_dir


def _prepare_and_blocked_run(tmp_path: Path, *, timestamp: str = "20260707T111111Z") -> Path:
    out_dir = tmp_path / "runs"
    prep = run_script(
        "prepare",
        "--messy-input",
        "The LoRA and prompt injection work got messy. Build a bounded design packet.",
        "--out-dir",
        out_dir,
        "--timestamp",
        timestamp,
    )
    assert prep.returncode == 0
    run_dir = out_dir / timestamp
    raw_output = tmp_path / "raw_model_output.txt"
    raw_output.write_text(_valid_raw_output_json(), encoding="utf-8")
    ingest = run_script(
        "ingest",
        "--run-dir",
        run_dir,
        "--raw-output-file",
        raw_output,
        "--decision",
        "rejected",
        "--decision-reason",
        "Needs revisions.",
        "--operator",
        "manual",
    )
    assert ingest.returncode == 0
    return run_dir


def test_transaction_manifest_references_chain_without_replacing_records(tmp_path: Path) -> None:
    run_dir = _prepare_and_accept_run(tmp_path)
    result = build_transaction_handoff_artifacts(run_dir=run_dir, next_worker_identity="qwen3-30b")

    manifest = json.loads(result["transaction_manifest_path"].read_text(encoding="utf-8"))
    assert manifest["schema_version"] == TRANSACTION_MANIFEST_SCHEMA
    assert manifest["lifecycle_state"] == "HANDOFF"
    assert manifest["records"]["attempt_id"] is not None
    assert manifest["records"]["validation_id"] is not None
    assert manifest["records"]["decision_id"] is not None
    assert manifest["records"]["gate_id"] is not None
    assert manifest["records"]["handoff_id"] is not None
    assert manifest["evidence_references"]
    assert "supervised_model_attempt" in {item["artifact"] for item in manifest["evidence_references"]}
    assert any("sha256" in item for item in manifest["evidence_references"])


def test_next_worker_context_contains_required_handoff_information(tmp_path: Path) -> None:
    run_dir = _prepare_and_accept_run(tmp_path)
    result = build_transaction_handoff_artifacts(run_dir=run_dir, next_worker_identity="qwen3-30b")
    context = json.loads(result["next_worker_context_path"].read_text(encoding="utf-8"))

    assert context["schema_version"] == NEXT_WORKER_CONTEXT_SCHEMA
    assert context["selected_next_worker_identity"] == "qwen3-30b"
    assert context["ready_for_next_worker"] is True
    assert "# ZTH Model Prompt Packet" in context["task_request"]
    assert "The LoRA and prompt injection work got messy." in context["task_state"]["bounded_task_request"]
    assert context["review"]["decision"] == "accepted"
    assert context["validation"]["validation_status"] == "passed"
    assert context["downstream_use_gate"]["gate_status"] == "allowed"
    assert context["handoff"]["handoff_status"] == "prepared"
    assert context["constraints"]["allowed_targets"] == ["docs/reports/"]
    assert "production automation" in context["constraints"]["held_targets"]
    assert context["first_worker_identity"] == "manual_operator_provided_model_output"
    assert context["previous_attempt"]["result_reference"]["raw_output_reference"].endswith("raw_model_output.txt")
    assert context["handoff"]["handoff_packet_reference"]["path"].endswith("handoff_packet.json")


def test_transaction_id_is_stable_across_reconstruction(tmp_path: Path) -> None:
    run_dir = _prepare_and_accept_run(tmp_path)
    first = build_transaction_handoff_artifacts(run_dir=run_dir, next_worker_identity="qwen3-30b")
    second = build_transaction_handoff_artifacts(run_dir=run_dir, next_worker_identity="qwen3-30b")

    manifest_a = json.loads(first["transaction_manifest_path"].read_text(encoding="utf-8"))
    manifest_b = json.loads(second["transaction_manifest_path"].read_text(encoding="utf-8"))
    assert manifest_a["transaction_id"] == manifest_b["transaction_id"]
    assert manifest_a["run_id"] == manifest_b["run_id"]
    assert manifest_a["updated_at"]
    assert manifest_b["updated_at"]


def test_transaction_handoff_fails_closed_when_required_review_artifacts_are_missing(tmp_path: Path) -> None:
    run_dir = _prepare_and_accept_run(tmp_path)
    (run_dir / "review_decision.json").unlink()

    with pytest.raises(TransactionHandoffError, match="review_decision"):
        build_transaction_handoff_artifacts(run_dir=run_dir, next_worker_identity="qwen3-30b")


def test_transaction_handoff_fails_closed_on_chain_mismatch(tmp_path: Path) -> None:
    run_dir = _prepare_and_accept_run(tmp_path)
    validation_path = run_dir / "output_validation.json"
    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    validation["attempt_id"] = "different_attempt"
    validation_path.write_text(json.dumps(validation, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(TransactionHandoffError, match="validation attempt_id"):
        build_transaction_handoff_artifacts(run_dir=run_dir, next_worker_identity="qwen3-30b")


def test_transaction_handoff_fails_closed_on_broadened_allowed_targets(tmp_path: Path) -> None:
    run_dir = _prepare_and_accept_run(tmp_path)
    triage_path = run_dir / "triage_packet.json"
    triage = json.loads(triage_path.read_text(encoding="utf-8"))
    triage["allowed_targets"] = ["docs/reports/", "production automation"]
    triage_path.write_text(json.dumps(triage, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(TransactionHandoffError, match="allowed targets"):
        build_transaction_handoff_artifacts(run_dir=run_dir, next_worker_identity="qwen3-30b")


def test_transaction_handoff_fails_closed_on_removed_held_target(tmp_path: Path) -> None:
    run_dir = _prepare_and_accept_run(tmp_path)
    orchestration_path = run_dir / "orchestration_packet.json"
    orchestration = json.loads(orchestration_path.read_text(encoding="utf-8"))
    orchestration["held_targets"] = []
    orchestration_path.write_text(json.dumps(orchestration, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(TransactionHandoffError, match="held targets"):
        build_transaction_handoff_artifacts(run_dir=run_dir, next_worker_identity="qwen3-30b")


def test_transaction_handoff_fails_closed_on_inconsistent_handoff_scope(tmp_path: Path) -> None:
    run_dir = _prepare_and_accept_run(tmp_path)
    handoff_path = run_dir / "handoff_packet.json"
    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
    handoff["handoff_scope"] = "broadened_supervised_input_only"
    handoff_path.write_text(json.dumps(handoff, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(TransactionHandoffError, match="handoff scope"):
        build_transaction_handoff_artifacts(run_dir=run_dir, next_worker_identity="qwen3-30b")


def test_transaction_handoff_raw_output_reference_points_to_raw_model_output(tmp_path: Path) -> None:
    run_dir = _prepare_and_accept_run(tmp_path)
    result = build_transaction_handoff_artifacts(run_dir=run_dir, next_worker_identity="qwen3-30b")
    context = json.loads(result["next_worker_context_path"].read_text(encoding="utf-8"))
    reference = context["previous_attempt"]["result_reference"]["raw_output_reference"]

    assert reference.endswith("raw_model_output.txt")
    assert Path(reference).is_file()


def test_transaction_handoff_handoff_packet_reference_resolves_correctly(tmp_path: Path) -> None:
    run_dir = _prepare_and_accept_run(tmp_path)
    result = build_transaction_handoff_artifacts(run_dir=run_dir, next_worker_identity="qwen3-30b")
    context = json.loads(result["next_worker_context_path"].read_text(encoding="utf-8"))
    reference = context["handoff"]["handoff_packet_reference"]

    assert reference["path"].endswith("handoff_packet.json")
    assert Path(reference["path"]).is_file()


def test_blocked_handoff_is_not_ready_or_complete(tmp_path: Path) -> None:
    run_dir = _prepare_and_accept_run(tmp_path)
    handoff_path = run_dir / "handoff_packet.json"
    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
    handoff["handoff_status"] = "blocked"
    handoff_path.write_text(json.dumps(handoff, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    validation = json.loads((run_dir / "output_validation.json").read_text(encoding="utf-8"))
    decision = json.loads((run_dir / "review_decision.json").read_text(encoding="utf-8"))
    gate = json.loads((run_dir / "downstream_use_gate.json").read_text(encoding="utf-8"))
    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))

    lifecycle = derive_lifecycle_state(
        validation_record=validation,
        decision_record=decision,
        gate_record=gate,
        handoff_record=handoff,
    )

    assert lifecycle == "REVIEW_REQUIRED"
    assert lifecycle != "HANDOFF"
    assert lifecycle != "COMPLETE"

    with pytest.raises(TransactionHandoffError, match="prepared handoff packet"):
        build_transaction_handoff_artifacts(run_dir=run_dir, next_worker_identity="qwen3-30b")


def test_transaction_handoff_references_are_hashed(tmp_path: Path) -> None:
    run_dir = _prepare_and_accept_run(tmp_path)
    result = build_transaction_handoff_artifacts(run_dir=run_dir, next_worker_identity="qwen3-30b")
    manifest = json.loads(result["transaction_manifest_path"].read_text(encoding="utf-8"))
    reference_map = {item["artifact"]: item for item in manifest["evidence_references"]}

    assert reference_map["supervised_model_attempt"]["sha256"]
    assert reference_map["output_validation"]["sha256"]
    assert reference_map["review_decision"]["sha256"]
    assert reference_map["downstream_use_gate"]["sha256"]
    assert reference_map["handoff_packet"]["sha256"]
    assert reference_map["raw_model_output"]["sha256"]
    assert reference_map["model_prompt_packet"]["sha256"]


def test_transaction_handoff_does_not_mark_complete(tmp_path: Path) -> None:
    run_dir = _prepare_and_accept_run(tmp_path)
    result = build_transaction_handoff_artifacts(run_dir=run_dir, next_worker_identity="qwen3-30b")
    manifest = json.loads(result["transaction_manifest_path"].read_text(encoding="utf-8"))

    assert manifest["lifecycle_state"] == "HANDOFF"
    assert manifest["lifecycle_state"] != "COMPLETE"
