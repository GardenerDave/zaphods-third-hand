from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

import local_harness.run_manual_supervised_attempt as manual_attempt
from local_harness.transaction_handoff import (
    NEXT_WORKER_CONTEXT_SCHEMA,
    TRANSACTION_MANIFEST_SCHEMA,
    TransactionHandoffError,
    build_authority_bound_semantic_result,
    build_worker_b_preflight,
    build_next_worker_continuation_context,
    build_worker_b_recipient_run_artifacts,
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


def _prepare_and_accept_run(
    tmp_path: Path,
    *,
    timestamp: str = "20260707T101010Z",
    next_worker_objective: str | None = None,
) -> Path:
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
        *(
            ["--next-worker-objective", next_worker_objective]
            if next_worker_objective is not None
            else []
        ),
    )
    assert ingest.returncode == 0
    return run_dir


def _prepare_and_accept_model_run(
    tmp_path: Path,
    *,
    timestamp: str = "20260707T111213Z",
    next_worker_objective: str | None = None,
) -> Path:
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
    prompt_text = (run_dir / "model_prompt_packet.md").read_text(encoding="utf-8")
    (run_dir / "prompt_to_paste.md").write_text(prompt_text, encoding="utf-8")
    raw_text = _valid_raw_output_json()
    raw_output = tmp_path / "raw_model_output.txt"
    raw_output.write_text(raw_text, encoding="utf-8")
    metadata = {
        "source": "local_openai_compatible_endpoint",
        "endpoint": "http://192.168.1.16:8081/v1",
        "model": "Qwen_Qwen3-1.7B-Q4_K_M.gguf",
        "temperature": 0,
        "max_tokens": 1024,
        "prompt_path": "model_prompt_packet.md",
        "prompt_sha256": manual_attempt._sha256_text(prompt_text),
        "prompt_length": len(prompt_text),
        "raw_output_path": "raw_model_output.txt",
        "raw_output_sha256": manual_attempt._sha256_text(raw_text),
        "raw_output_length": len(raw_text),
        "call_status": "completed",
        "review_required": True,
        "request_provenance": {
            "api": "openai-chat",
            "endpoint": "http://192.168.1.16:8081/v1",
            "request_url": "http://192.168.1.16:8081/v1/chat/completions",
            "model": "Qwen_Qwen3-1.7B-Q4_K_M.gguf",
            "configured_model": "Qwen_Qwen3-1.7B-Q4_K_M.gguf",
            "resolved_model": "Qwen_Qwen3-1.7B-Q4_K_M.gguf",
            "prompt_path": "model_prompt_packet.md",
            "prompt_sha256": manual_attempt._sha256_text(prompt_text),
            "prompt_length": len(prompt_text),
            "max_tokens": 1024,
            "temperature": 0,
        },
        "response_provenance": {
            "raw_output_path": "raw_model_output.txt",
            "raw_output_sha256": manual_attempt._sha256_text(raw_text),
            "raw_output_length": len(raw_text),
            "model": "Qwen_Qwen3-1.7B-Q4_K_M.gguf",
        },
        "authority_boundaries": [
            "Local model call is not command execution authority.",
            "Local model call is not file modification authority.",
            "No automatic patch promotion authority is granted.",
            "No automatic training authority is granted.",
            "No default failure-to-curriculum capture authority is granted.",
            "Ingest and explicit review are required before downstream use.",
        ],
    }
    metadata_path = tmp_path / "local_model_call.json"
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    ingest = run_script(
        "ingest",
        "--run-dir",
        run_dir,
        "--raw-output-file",
        raw_output,
        "--model-call-metadata-file",
        metadata_path,
        "--decision",
        "accepted",
        "--decision-reason",
        "Output satisfies the contract and remains within scope.",
        "--operator",
        "manual",
        "--next-worker",
        "qwen3-30b",
        *(
            ["--next-worker-objective", next_worker_objective]
            if next_worker_objective is not None
            else []
        ),
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
    run_dir = _prepare_and_accept_run(
        tmp_path,
        next_worker_objective="Produce a bounded downstream comparison report.",
    )
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
    run_dir = _prepare_and_accept_run(
        tmp_path,
        next_worker_objective="Produce a bounded downstream comparison report.",
    )
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
    assert context["transaction_binding"]["transaction_id"] == context["transaction_id"]
    assert context["transaction_binding"]["run_id"] == context["run_id"]
    assert context["transaction_binding"]["attempt_id"] == context["previous_attempt"]["attempt_id"]
    assert context["transaction_binding"]["handoff_id"] == context["handoff"]["handoff_id"]
    assert context["transaction_binding"]["raw_output_sha256"] == context["previous_attempt"]["result_reference"]["raw_output_sha256"]
    assert context["constraints"]["allowed_targets"] == ["docs/reports/"]
    assert "production automation" in context["constraints"]["held_targets"]
    assert context["first_worker_identity"] == "manual_operator_provided_model_output"
    assert context["previous_attempt"]["result_reference"]["raw_output_reference"].endswith("raw_model_output.txt")
    assert context["handoff"]["handoff_packet_reference"]["path"].endswith("handoff_packet.json")


def test_transaction_id_is_stable_across_reconstruction(tmp_path: Path) -> None:
    run_dir = _prepare_and_accept_run(
        tmp_path,
        next_worker_objective="Produce a bounded downstream comparison report.",
    )
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
    run_dir = _prepare_and_accept_run(
        tmp_path,
        next_worker_objective="Produce a bounded downstream comparison report.",
    )
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


def test_transaction_handoff_preserves_actual_worker_identity_from_model_ingest(tmp_path: Path) -> None:
    run_dir = _prepare_and_accept_model_run(
        tmp_path,
        next_worker_objective="Produce a bounded downstream comparison report.",
    )
    result = build_transaction_handoff_artifacts(run_dir=run_dir, next_worker_identity="qwen3-30b")
    context = json.loads(result["next_worker_context_path"].read_text(encoding="utf-8"))
    attempt = json.loads((run_dir / "supervised_model_attempt.json").read_text(encoding="utf-8"))
    continuation = build_next_worker_continuation_context(
        transaction_manifest=json.loads(result["transaction_manifest_path"].read_text(encoding="utf-8")),
        next_worker_context=context,
        output_dir=run_dir,
    )

    assert attempt["model_metadata"]["model_id"] == "Qwen_Qwen3-1.7B-Q4_K_M.gguf"
    assert context["first_worker_identity"] == "Qwen_Qwen3-1.7B-Q4_K_M.gguf"
    assert context["previous_attempt"]["result_reference"]["raw_output_sha256"] == manual_attempt._sha256_text(
        _valid_raw_output_json()
    )
    assert "The LoRA and prompt injection work got messy." in continuation["continuation_text"]


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


def test_next_worker_continuation_contains_actual_previous_result_body(tmp_path: Path) -> None:
    run_dir = _prepare_and_accept_run(
        tmp_path,
        next_worker_objective="Produce a bounded downstream comparison report.",
    )
    handoff_result = build_transaction_handoff_artifacts(run_dir=run_dir, next_worker_identity="qwen3-30b")
    continuation_result = build_next_worker_continuation_context(
        transaction_manifest=handoff_result["transaction_manifest"],
        next_worker_context=handoff_result["next_worker_context"],
        output_dir=run_dir,
    )
    continuation_text = continuation_result["continuation_text"]
    raw_output_text = (run_dir / "raw_model_output.txt").read_text(encoding="utf-8").strip()

    assert continuation_result["transaction_id"] == handoff_result["transaction_manifest"]["transaction_id"]
    assert continuation_text.startswith(
        "Continue from the accepted previous-worker result. Do not redo the original worker task."
    )
    assert "## Next-Worker Directive" in continuation_text
    assert raw_output_text in continuation_text
    assert "The LoRA and prompt injection work got messy." in continuation_text
    assert "validation_status" in continuation_text
    assert "handoff_scope" not in continuation_text
    assert "manual_operator_provided_model_output" in continuation_text
    context_markdown = (run_dir / "next_worker_context.md").read_text(encoding="utf-8")
    assert "## Transaction Binding" in context_markdown
    assert "raw_output_sha256" in context_markdown


def test_next_worker_continuation_preserves_authority_and_is_not_first_worker_prompt_dominant(tmp_path: Path) -> None:
    run_dir = _prepare_and_accept_run(
        tmp_path,
        next_worker_objective="Produce a bounded downstream comparison report.",
    )
    handoff_result = build_transaction_handoff_artifacts(run_dir=run_dir, next_worker_identity="qwen3-30b")
    continuation_result = build_next_worker_continuation_context(
        transaction_manifest=handoff_result["transaction_manifest"],
        next_worker_context=handoff_result["next_worker_context"],
        output_dir=run_dir,
    )
    continuation_text = continuation_result["continuation_text"]

    assert "allowed_targets" in continuation_text
    assert "held_targets" in continuation_text
    assert "Inherited Authority Boundaries" in continuation_text
    assert "This prompt authorizes only the stated downstream task." in continuation_text
    assert continuation_text.index("## Next-Worker Directive") < continuation_text.index("### Bounded Original Task")
    assert continuation_text.index("## Next-Worker Directive") < continuation_text.index("### Accepted Previous-Worker Result")
    assert continuation_text.index("### Second-Worker Output Contract") < continuation_text.index("### Provenance")


def test_next_worker_continuation_perform_now_contains_concrete_objective_not_scope(tmp_path: Path) -> None:
    run_dir = _prepare_and_accept_run(
        tmp_path,
        next_worker_objective="Produce a bounded downstream comparison report.",
    )
    handoff_result = build_transaction_handoff_artifacts(run_dir=run_dir, next_worker_identity="qwen3-30b")
    continuation_result = build_next_worker_continuation_context(
        transaction_manifest=handoff_result["transaction_manifest"],
        next_worker_context=handoff_result["next_worker_context"],
        output_dir=run_dir,
    )
    continuation_text = continuation_result["continuation_text"]

    assert "Perform Now" in continuation_text
    assert "Use reviewed output as bounded input for the next supervised step." in continuation_text
    assert "bounded_supervised_input_only" in continuation_text
    assert continuation_text.index("### Perform Now") < continuation_text.index("### Authorized Scope")
    assert "bounded_supervised_input_only" in continuation_text.split("### Perform Now", 1)[1]


def test_next_worker_continuation_fails_closed_on_missing_or_tampered_previous_result(tmp_path: Path) -> None:
    run_dir = _prepare_and_accept_run(
        tmp_path,
        next_worker_objective="Produce a bounded downstream comparison report.",
    )
    handoff_result = build_transaction_handoff_artifacts(run_dir=run_dir, next_worker_identity="qwen3-30b")
    raw_output_path = run_dir / "raw_model_output.txt"
    original_text = raw_output_path.read_text(encoding="utf-8")

    raw_output_path.write_text(original_text + "\nmutated\n", encoding="utf-8")
    with pytest.raises(TransactionHandoffError, match="bytes do not match recorded sha256|previous result bytes do not match recorded sha256"):
        build_next_worker_continuation_context(
            transaction_manifest=handoff_result["transaction_manifest"],
            next_worker_context=handoff_result["next_worker_context"],
            output_dir=run_dir,
        )

    raw_output_path.unlink()
    with pytest.raises(TransactionHandoffError, match="missing raw model output"):
        build_next_worker_continuation_context(
            transaction_manifest=handoff_result["transaction_manifest"],
            next_worker_context=handoff_result["next_worker_context"],
            output_dir=run_dir,
        )


def test_next_worker_continuation_round_trips_with_same_transaction_id_and_does_not_complete(tmp_path: Path) -> None:
    run_dir = _prepare_and_accept_run(
        tmp_path,
        next_worker_objective="Produce a bounded downstream comparison report.",
    )
    handoff_result = build_transaction_handoff_artifacts(run_dir=run_dir, next_worker_identity="qwen3-30b")
    continuation_result = build_next_worker_continuation_context(
        transaction_manifest=handoff_result["transaction_manifest"],
        next_worker_context=handoff_result["next_worker_context"],
        output_dir=run_dir,
    )

    assert continuation_result["transaction_id"] == handoff_result["transaction_manifest"]["transaction_id"]
    assert continuation_result["ready_for_continuation"] is True
    assert "COMPLETE" not in continuation_result["continuation_text"]


def test_next_worker_continuation_fails_closed_without_explicit_objective(tmp_path: Path) -> None:
    run_dir = _prepare_and_accept_run(tmp_path)
    handoff_result = build_transaction_handoff_artifacts(run_dir=run_dir, next_worker_identity="qwen3-30b")

    with pytest.raises(TransactionHandoffError, match="next_step_objective"):
        build_next_worker_continuation_context(
            transaction_manifest=handoff_result["transaction_manifest"],
            next_worker_context=handoff_result["next_worker_context"],
            output_dir=run_dir,
        )


def test_worker_b_preflight_passes_and_writes_artifact(tmp_path: Path) -> None:
    run_dir = _prepare_and_accept_run(
        tmp_path,
        next_worker_objective=(
            "Using the accepted previous-worker result as completed work, produce the actual "
            "review-ready downstream cleanup implementation plan now. The plan must contain: "
            "(1) an ordered sequence of concrete cleanup actions, (2) the specific files/"
            "components or artifact classes each action affects, (3) a validation criterion "
            "for each action, and (4) unresolved or held work that must not be activated. "
            "Do not recommend that another worker create this plan. Produce the plan itself "
            "in this response."
        ),
    )
    build_transaction_handoff_artifacts(run_dir=run_dir, next_worker_identity="qwen3-30b")
    build_next_worker_continuation_context(
        transaction_manifest=json.loads((run_dir / "transaction_manifest.json").read_text(encoding="utf-8")),
        next_worker_context=json.loads((run_dir / "next_worker_context.json").read_text(encoding="utf-8")),
        output_dir=run_dir,
    )

    result = build_worker_b_preflight(run_dir=run_dir, expected_next_worker_identity="qwen3-30b", output_dir=run_dir)

    assert result["status"] == "passed"
    assert (run_dir / "worker_b_preflight.json").is_file()
    assert any(check["check_id"] == "objective_propagation" for check in result["checks"])
    assert any(check["check_id"] == "authority" for check in result["checks"])


def test_worker_b_preflight_fails_on_objective_mismatch(tmp_path: Path) -> None:
    run_dir = _prepare_and_accept_run(tmp_path, next_worker_objective="Produce a bounded downstream comparison report.")
    build_transaction_handoff_artifacts(run_dir=run_dir, next_worker_identity="qwen3-30b")
    context_path = run_dir / "next_worker_context.json"
    context = json.loads(context_path.read_text(encoding="utf-8"))
    context["handoff"]["next_step_objective"] = "Something else"
    context_path.write_text(json.dumps(context, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = build_worker_b_preflight(run_dir=run_dir, expected_next_worker_identity="qwen3-30b")

    assert result["status"] == "failed"
    assert any(check["check_id"] == "preflight" for check in result["checks"])


def test_worker_b_preflight_derives_authority_from_transaction_artifacts(tmp_path: Path) -> None:
    run_dir = _prepare_and_accept_run(tmp_path, next_worker_objective="Produce a bounded downstream comparison report.")
    build_transaction_handoff_artifacts(run_dir=run_dir, next_worker_identity="qwen3-30b")
    continuation_path = run_dir / "next_worker_continuation.md"
    context_path = run_dir / "next_worker_context.json"
    triage_path = run_dir / "triage_packet.json"
    orchestration_path = run_dir / "orchestration_packet.json"

    new_allowed = ["docs/reports/", "docs/notes/"]
    new_held = ["production automation", "automatic curriculum capture", "automatic promotion", "implementation_packet", "implementation notes"]

    triage = json.loads(triage_path.read_text(encoding="utf-8"))
    triage["allowed_targets"] = new_allowed
    triage_path.write_text(json.dumps(triage, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    orchestration = json.loads(orchestration_path.read_text(encoding="utf-8"))
    orchestration["held_targets"] = new_held
    orchestration_path.write_text(json.dumps(orchestration, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    context = json.loads(context_path.read_text(encoding="utf-8"))
    context["task_state"]["allowed_targets"] = new_allowed
    context["task_state"]["held_targets"] = new_held
    context["constraints"]["allowed_targets"] = new_allowed
    context["constraints"]["held_targets"] = new_held
    context_path.write_text(json.dumps(context, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    continuation_text = continuation_path.read_text(encoding="utf-8")
    continuation_text = continuation_text.replace(
        json.dumps(["docs/reports/"], indent=2, sort_keys=True),
        json.dumps(new_allowed, indent=2, sort_keys=True),
    )
    continuation_text = continuation_text.replace(
        json.dumps(
            [
                "production automation",
                "automatic curriculum capture",
                "automatic promotion",
                "implementation_packet",
            ],
            indent=2,
            sort_keys=True,
        ),
        json.dumps(new_held, indent=2, sort_keys=True),
    )
    continuation_path.write_text(continuation_text, encoding="utf-8")

    result = build_worker_b_preflight(run_dir=run_dir, expected_next_worker_identity="qwen3-30b")

    assert result["status"] == "passed"
    assert any(check["check_id"] == "authority" for check in result["checks"])


def test_worker_b_preflight_writes_failed_artifact_when_reference_missing(tmp_path: Path) -> None:
    run_dir = _prepare_and_accept_run(tmp_path, next_worker_objective="Produce a bounded downstream comparison report.")
    build_transaction_handoff_artifacts(run_dir=run_dir, next_worker_identity="qwen3-30b")
    (run_dir / "raw_model_output.txt").unlink()

    result = build_worker_b_preflight(run_dir=run_dir, expected_next_worker_identity="qwen3-30b", output_dir=run_dir)

    assert result["status"] == "failed"
    assert (run_dir / "worker_b_preflight.json").is_file()
    preflight = json.loads((run_dir / "worker_b_preflight.json").read_text(encoding="utf-8"))
    assert preflight["status"] == "failed"


def test_worker_b_recipient_run_artifacts_write_separate_run_prompt_and_manifest(tmp_path: Path) -> None:
    run_dir = _prepare_and_accept_run(
        tmp_path,
        next_worker_objective="Produce a bounded downstream comparison report.",
    )
    handoff_result = build_transaction_handoff_artifacts(run_dir=run_dir, next_worker_identity="qwen3-30b")
    continuation_result = build_next_worker_continuation_context(
        transaction_manifest=handoff_result["transaction_manifest"],
        next_worker_context=handoff_result["next_worker_context"],
        output_dir=run_dir,
    )

    recipient_dir = tmp_path / "recipient"
    result = build_worker_b_recipient_run_artifacts(
        source_run_dir=run_dir,
        recipient_run_dir=recipient_dir,
        recipient_identity="qwen3-30b",
        continuation_path=continuation_result["continuation_path"],
    )

    assert result["recipient_run_dir"] == recipient_dir
    assert (recipient_dir / "prompt_to_paste.md").read_text(encoding="utf-8") == (
        run_dir / "next_worker_continuation.md"
    ).read_text(encoding="utf-8")
    recipient_manifest = json.loads((recipient_dir / "recipient_run_manifest.json").read_text(encoding="utf-8"))
    assert recipient_manifest["recipient_identity"] == "qwen3-30b"
    assert recipient_manifest["continuation_sha256"] == result["continuation_sha256"]
    assert recipient_manifest["prompt_sha256"] == result["prompt_sha256"]
    assert recipient_manifest["source_transaction_binding"]["handoff_id"] == handoff_result["next_worker_context"]["transaction_binding"]["handoff_id"]
    continuation_text = (run_dir / "next_worker_continuation.md").read_text(encoding="utf-8")
    assert "Return the downstream semantic result only." in continuation_text
    assert "Do not reproduce allowed_targets, held_targets" in continuation_text


def test_authority_bound_semantic_result_keeps_authority_out_of_model_output(tmp_path: Path) -> None:
    run_dir = _prepare_and_accept_run(tmp_path, next_worker_objective="Produce a bounded downstream comparison report.")
    handoff_result = build_transaction_handoff_artifacts(run_dir=run_dir, next_worker_identity="qwen3-30b")
    build_next_worker_continuation_context(
        transaction_manifest=handoff_result["transaction_manifest"],
        next_worker_context=handoff_result["next_worker_context"],
        output_dir=run_dir,
    )

    semantic_output = {
        "findings": [{"claim": "structured output enforcement was not active", "evidence": []}],
        "reason": "bounded diagnosis",
    }
    result = build_authority_bound_semantic_result(
        semantic_output=semantic_output,
        raw_output_path=run_dir / "raw_model_output.txt",
        transaction_manifest=handoff_result["transaction_manifest"],
        next_worker_context=handoff_result["next_worker_context"],
        output_dir=run_dir,
    )

    assert result["semantic_output"] == semantic_output
    assert result["authority"]["allowed_targets"] == handoff_result["next_worker_context"]["task_state"]["allowed_targets"]
    assert result["authority"]["held_targets"] == handoff_result["next_worker_context"]["task_state"]["held_targets"]
    assert result["derived"]["scope_expansion_required"] is False
    assert (run_dir / "authority_bound_semantic_result.json").is_file()


def test_authority_bound_semantic_result_rejects_authority_contamination(tmp_path: Path) -> None:
    run_dir = _prepare_and_accept_run(tmp_path, next_worker_objective="Produce a bounded downstream comparison report.")
    handoff_result = build_transaction_handoff_artifacts(run_dir=run_dir, next_worker_identity="qwen3-30b")
    build_next_worker_continuation_context(
        transaction_manifest=handoff_result["transaction_manifest"],
        next_worker_context=handoff_result["next_worker_context"],
        output_dir=run_dir,
    )

    semantic_output = {
        "findings": [{"claim": "structured output enforcement was not active", "evidence": []}],
        "reason": "bounded diagnosis",
        "allowed_targets": ["docs/reports/"],
    }
    with pytest.raises(TransactionHandoffError, match="must not contain authoritative target fields"):
        build_authority_bound_semantic_result(
            semantic_output=semantic_output,
            raw_output_path=run_dir / "raw_model_output.txt",
            transaction_manifest=handoff_result["transaction_manifest"],
            next_worker_context=handoff_result["next_worker_context"],
        )


def test_transaction_handoff_supports_semantic_worker_raw_output_without_authority_fields(tmp_path: Path) -> None:
    run_dir = _prepare_and_accept_run(tmp_path, next_worker_objective="Produce a bounded downstream comparison report.")
    raw_path = run_dir / "raw_model_output.txt"
    raw_path.write_text(
        json.dumps(
            {
                "findings": [
                    {
                        "claim": "structured output enforcement was not active",
                        "evidence": [{"path": "fresh/local_model_call.json", "detail": "structured_output_enabled: false"}],
                    }
                ],
                "reason": "bounded diagnosis",
            }
        ),
        encoding="utf-8",
    )
    handoff_result = build_transaction_handoff_artifacts(run_dir=run_dir, next_worker_identity="qwen3-30b")
    context = json.loads(handoff_result["next_worker_context_path"].read_text(encoding="utf-8"))
    assert context["transaction_binding"]["raw_output_sha256"]
    assert context["task_state"]["allowed_targets"] == json.loads((run_dir / "triage_packet.json").read_text(encoding="utf-8"))["allowed_targets"]
