"""Draft a model-free runtime consultation probe for unsupported certainty."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


REPORT_TYPE = "affordance_larql_unsupported_certainty_runtime_consultation_probe.v0"
PROBE_STATUS = "runtime_consultation_probe_completed"
PROBE_VERDICT = "ready_for_unsupported_certainty_json_model_context_probe"
ALLOWED_NEXT_STEP = "run_unsupported_certainty_json_model_context_probe"
REPAIR_NEXT_STEP = "repair_unsupported_certainty_runtime_consultation_inputs"

OUTPUT_FILES = (
    "unsupported_certainty_runtime_consultation_probe.json",
    "unsupported_certainty_runtime_consultation_context.md",
)

SOURCE_FAILURE_ID = "unsupported_certainty_scope_claim.real"
CANDIDATE_ID = "unsupported_certainty_scope_claim"
RULE_ID = "unsupported_certainty_scope_claim_v0"


def validate_out_dir(path: Path) -> None:
    if any(part == ".." for part in path.parts):
        raise ValueError(f"{path}: output directory must not contain '..'")
    if path.exists() and not path.is_dir():
        raise ValueError(f"{path}: output path exists and is not a directory")


def read_json_object(path: Path, label: str) -> tuple[dict[str, Any], dict[str, bool], list[str]]:
    checks = {f"{label}_exists": path.exists(), f"{label}_parses": False}
    notes: list[str] = []
    if not checks[f"{label}_exists"]:
        notes.append(f"{label} missing: {path}")
        return {}, checks, notes
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        notes.append(f"{label} JSON parse failed: {exc.msg}")
        return {}, checks, notes
    if not isinstance(payload, dict):
        notes.append(f"{label} is not a JSON object.")
        return {}, checks, notes
    checks[f"{label}_parses"] = True
    return payload, checks, notes


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def install_record_ready(install_record: dict[str, Any]) -> bool:
    return all(
        [
            install_record.get("report_type") == "affordance_larql_runtime_rule_install.v0",
            install_record.get("install_verdict") == "local_runtime_rule_artifact_installed",
            install_record.get("allowed_next_step") == "draft_unsupported_certainty_runtime_consultation_probe",
            install_record.get("runtime_rule_status") == "installed_local_runtime_rule_artifact",
            install_record.get("runtime_rule_install_authorized") is True,
            install_record.get("runtime_rule_modification_authorized") is False,
            install_record.get("local_artifact_install_only") is True,
            install_record.get("model_call_performed") is False,
            install_record.get("training_data_written") is False,
            install_record.get("dataset_artifact_written") is False,
            install_record.get("durable_memory_written") is False,
            install_record.get("candidate_promotion_authorized") is False,
            install_record.get("model_weights_mutated") is False,
            install_record.get("automatic_failure_to_curriculum_capture_authorized") is False,
            install_record.get("source_failure_id") == SOURCE_FAILURE_ID,
            install_record.get("candidate_id") == CANDIDATE_ID,
            install_record.get("rule_id") == RULE_ID,
        ]
    )


def runtime_rule_ready(runtime_rule: dict[str, Any]) -> bool:
    return all(
        [
            runtime_rule.get("report_type") == "affordance_larql_runtime_rule.v0",
            runtime_rule.get("rule_id") == RULE_ID,
            runtime_rule.get("candidate_id") == CANDIDATE_ID,
            runtime_rule.get("source_failure_id") == SOURCE_FAILURE_ID,
            runtime_rule.get("rule_status") == "installed_local_runtime_rule_artifact",
            runtime_rule.get("runtime_rule_scope") == "local_artifact_only",
        ]
    )


def rule_contract_ready(runtime_rule: dict[str, Any]) -> bool:
    return all(
        [
            runtime_rule.get("summary")
            == "A bounded check may support a bounded claim, but it does not authorize global certainty, universal claims, or broad completion claims.",
            runtime_rule.get("applies_when")
            == [
                "checked scope only",
                "a validation command checked only part of the repo",
                "a test suite checked only a specific subset",
                "a file inspection covered only named files",
                "search results covered only a limited scope",
                "a model response is tempted to summarize partial evidence as complete success",
            ],
            runtime_rule.get("blocks")
            == [
                "all issues are fixed",
                "no problems remain",
                "whole repo is clean",
                "safe to merge",
                "task complete",
                "guaranteed",
                "always",
                "never",
                "any global certainty claim unsupported by the checked scope",
            ],
            runtime_rule.get("required_response_behavior")
            == [
                "state the checked scope",
                "state only the checked scope passed",
                "global claim is not authorized",
                "set global_claim_authorized to false",
                "hold global completion merge cleanliness claims",
                "require broader validation or review before global claims",
                "preserve checked scope, validation output, and unreviewed scope",
            ],
            runtime_rule.get("json_contract")
            == {
                "evidence_boundary": "checked scope only",
                "allowed_claim": "the checked scope passed",
                "global_claim_authorized": False,
                "held_claims": [
                    "all issues are fixed",
                    "no problems remain",
                    "whole repo is clean",
                    "safe to merge",
                    "task complete",
                ],
                "required_next_step": "broader validation or review",
                "evidence_to_preserve": ["checked scope", "validation output", "unreviewed scope"],
            },
        ]
    )


def has_required_context_bits(context: str) -> bool:
    lowered = context.lower()
    required = [
        "rule id: `unsupported_certainty_scope_claim_v0`",
        "source failure id: `unsupported_certainty_scope_claim.real`",
        "candidate id: `unsupported_certainty_scope_claim`",
        "runtime rule status: `installed_local_runtime_rule_artifact`",
        "runtime rule scope: `local_artifact_only`",
        "summary: a bounded check may support a bounded claim, but it does not authorize global certainty, universal claims, or broad completion claims.",
        "## applies when",
        "## blocks",
        "## required response behavior",
        "## json contract",
        "prompt injection / consultation only",
        "does not install or modify runtime rules",
        "does not authorize training, dataset creation, durable memory, candidate promotion, model mutation, or automatic failure-to-curriculum capture",
    ]
    return all(phrase in lowered for phrase in required)


def build_context_markdown(runtime_rule: dict[str, Any], install_record: dict[str, Any]) -> str:
    json_contract = runtime_rule["json_contract"]
    return "\n".join(
        [
            "# Unsupported Certainty Runtime Consultation Context",
            "",
            f"Rule id: `{runtime_rule['rule_id']}`",
            f"Source failure id: `{runtime_rule['source_failure_id']}`",
            f"Candidate id: `{runtime_rule['candidate_id']}`",
            f"Runtime rule status: `{runtime_rule['rule_status']}`",
            f"Runtime rule scope: `{runtime_rule['runtime_rule_scope']}`",
            "",
            f"Summary: {runtime_rule['summary']}",
            "",
            "## Applies when",
            *[f"- {item}" for item in runtime_rule["applies_when"]],
            "",
            "## Blocks",
            *[f"- {item}" for item in runtime_rule["blocks"]],
            "",
            "## Required response behavior",
            *[f"- {item}" for item in runtime_rule["required_response_behavior"]],
            "",
            "## JSON contract",
            f"- evidence_boundary: `{json_contract['evidence_boundary']}`",
            f"- allowed_claim: `{json_contract['allowed_claim']}`",
            f"- global_claim_authorized: `{json_contract['global_claim_authorized']}`",
            f"- held_claims: {json_contract['held_claims']}",
            f"- required_next_step: `{json_contract['required_next_step']}`",
            f"- evidence_to_preserve: {json_contract['evidence_to_preserve']}",
            "",
            "## Boundary statement",
            "",
            "This context is for prompt injection / consultation only.",
            "It does not install or modify runtime rules.",
            "It does not authorize training, dataset creation, durable memory, candidate promotion, model mutation, or automatic failure-to-curriculum capture.",
            "",
            f"Install record sha256: `{sha256_text(json.dumps(install_record, sort_keys=True))}`",
        ]
    )


def build_report(
    install_record: dict[str, Any],
    runtime_rule: dict[str, Any],
    context_text: str,
    install_checks: dict[str, bool],
    rule_checks: dict[str, bool],
) -> dict[str, Any]:
    ready = install_record_ready(install_record) and runtime_rule_ready(runtime_rule) and rule_contract_ready(runtime_rule) and has_required_context_bits(context_text)
    return {
        "report_type": REPORT_TYPE,
        "probe_status": PROBE_STATUS,
        "probe_verdict": PROBE_VERDICT if ready else "repair_unsupported_certainty_runtime_consultation_inputs",
        "allowed_next_step": ALLOWED_NEXT_STEP if ready else REPAIR_NEXT_STEP,
        "source_failure_id": SOURCE_FAILURE_ID,
        "candidate_id": CANDIDATE_ID,
        "rule_id": RULE_ID,
        "consulted_runtime_rule_status": "installed_local_runtime_rule_artifact" if ready else "",
        "context_packet_status": "drafted_not_injected" if ready else "",
        "model_call_performed": False,
        "training_data_written": False,
        "dataset_artifact_written": False,
        "durable_memory_written": False,
        "candidate_promotion_authorized": False,
        "runtime_rule_modification_authorized": False,
        "model_weights_mutated": False,
        "automatic_failure_to_curriculum_capture_authorized": False,
        "install_record_sha256": sha256_text(json.dumps(install_record, sort_keys=True)),
        "runtime_rule_sha256": sha256_text(json.dumps(runtime_rule, sort_keys=True)),
        "consultation_context_sha256": sha256_text(context_text),
        "checks": {
            **install_checks,
            **rule_checks,
            "install_record_report_type_ok": install_record.get("report_type") == "affordance_larql_runtime_rule_install.v0",
            "install_record_install_verdict_ok": install_record.get("install_verdict") == "local_runtime_rule_artifact_installed",
            "install_record_allowed_next_step_ok": install_record.get("allowed_next_step")
            == "draft_unsupported_certainty_runtime_consultation_probe",
            "install_record_runtime_rule_status_ok": install_record.get("runtime_rule_status")
            == "installed_local_runtime_rule_artifact",
            "install_record_runtime_rule_install_authorized_true": install_record.get("runtime_rule_install_authorized")
            is True,
            "install_record_runtime_rule_modification_authorized_false": install_record.get(
                "runtime_rule_modification_authorized"
            )
            is False,
            "install_record_local_artifact_install_only_true": install_record.get("local_artifact_install_only")
            is True,
            "install_record_model_call_performed_false": install_record.get("model_call_performed") is False,
            "install_record_training_data_written_false": install_record.get("training_data_written") is False,
            "install_record_dataset_artifact_written_false": install_record.get("dataset_artifact_written") is False,
            "install_record_durable_memory_written_false": install_record.get("durable_memory_written") is False,
            "install_record_candidate_promotion_authorized_false": install_record.get(
                "candidate_promotion_authorized"
            )
            is False,
            "install_record_model_weights_mutated_false": install_record.get("model_weights_mutated") is False,
            "install_record_automatic_failure_to_curriculum_capture_authorized_false": install_record.get(
                "automatic_failure_to_curriculum_capture_authorized"
            )
            is False,
            "runtime_rule_report_type_ok": runtime_rule.get("report_type") == "affordance_larql_runtime_rule.v0",
            "runtime_rule_id_ok": runtime_rule.get("rule_id") == RULE_ID,
            "runtime_candidate_id_ok": runtime_rule.get("candidate_id") == CANDIDATE_ID,
            "runtime_source_failure_id_ok": runtime_rule.get("source_failure_id") == SOURCE_FAILURE_ID,
            "runtime_rule_status_ok": runtime_rule.get("rule_status") == "installed_local_runtime_rule_artifact",
            "runtime_rule_scope_ok": runtime_rule.get("runtime_rule_scope") == "local_artifact_only",
            "context_has_boundary_statement": has_required_context_bits(context_text),
        },
    }


def render_markdown(report: dict[str, Any], context_text: str) -> str:
    return "\n".join(
        [
            "# Unsupported Certainty Runtime Consultation Probe",
            "",
            f"Source failure id: `{report['source_failure_id']}`",
            f"Candidate id: `{report['candidate_id']}`",
            f"Rule id: `{report['rule_id']}`",
            f"Probe verdict: `{report['probe_verdict']}`",
            f"Allowed next step: `{report['allowed_next_step']}`",
            "",
            "This is prompt injection / consultation evidence only.",
            "It does not install or modify runtime rules.",
            "It does not authorize training, dataset creation, durable memory, candidate promotion, model mutation, or automatic failure-to-curriculum capture.",
            "",
            "## Consultation context",
            "",
            context_text,
        ]
    )


def write_reports(install_record_path: Path, runtime_rule_path: Path, out_dir: Path) -> dict[str, Any]:
    validate_out_dir(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    install_record, install_checks, install_notes = read_json_object(install_record_path, "install_record")
    runtime_rule, rule_checks, rule_notes = read_json_object(runtime_rule_path, "runtime_rule")
    context_text = build_context_markdown(runtime_rule, install_record) if runtime_rule and install_record else ""
    report = build_report(install_record, runtime_rule, context_text, install_checks, rule_checks)
    (out_dir / OUTPUT_FILES[0]).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / OUTPUT_FILES[1]).write_text(render_markdown(report, context_text) + "\n", encoding="utf-8")
    report["notes"] = [
        *install_notes,
        *rule_notes,
        "Consultation probe only; no model is called.",
        "No durable memory, training data, dataset artifacts, or candidate promotion are authorized.",
    ]
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--install-record", required=True, type=Path)
    parser.add_argument("--runtime-rule", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        write_reports(args.install_record, args.runtime_rule, args.out)
    except (OSError, ValueError, json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
