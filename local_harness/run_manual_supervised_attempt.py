#!/usr/bin/env python3
"""Manual supervised model-attempt runner with prepare and ingest phases."""

from __future__ import annotations

import argparse
import json
import math
import sys
import socket
import shutil
import hashlib
import urllib.error
import urllib.request
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from local_harness.orchestration_packet import assemble_orchestration_packet, validate_orchestration_packet
from local_harness.prompt_patch_library import PromptPatchLibrary, render_prompt_deltas
from local_harness.render_model_prompt_packet import (
    build_model_prompt_output_contract,
    render_model_prompt_packet,
)
from local_harness.render_supervised_attempt_output_validation import (
    render_supervised_attempt_output_validation,
)
from local_harness.transaction_handoff import (
    build_next_worker_continuation_context,
    build_transaction_handoff_artifacts,
)
from local_harness.supervised_attempt_output_validator import (
    validate_supervised_attempt_output_against_contract,
)
from local_harness.supervised_downstream_use_gate import build_supervised_downstream_use_gate_record
from local_harness.supervised_handoff_packet import build_supervised_handoff_packet
from local_harness.supervised_model_attempt import build_supervised_model_attempt_record
from local_harness.supervised_review_decision import (
    ALLOWED_DECISIONS,
    build_supervised_review_decision_record,
)
from local_harness.triage_packet_schema import validate_triage_packet
from local_harness.triage_router_rules import route_messy_input


EVIDENCE_OUTPUT_CONTRACT = {
    "format": "json",
    "required_fields": [
        "findings",
        "reason",
    ],
    "requires_reason": True,
}
EVIDENCE_RESPONSE_SCHEMA_PATH = Path(__file__).resolve().parent / "schemas" / "repo_observation_output_schema.json"


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_messy_input(*, messy_input: str | None, messy_input_file: Path | None) -> str:
    if bool(messy_input) == bool(messy_input_file):
        raise ValueError("provide exactly one of --messy-input or --messy-input-file")
    if messy_input is not None:
        value = messy_input.strip()
        if not value:
            raise ValueError("--messy-input must be non-empty")
        return value
    assert messy_input_file is not None
    if not messy_input_file.is_file():
        raise ValueError(f"--messy-input-file does not exist: {messy_input_file}")
    value = messy_input_file.read_text(encoding="utf-8").strip()
    if not value:
        raise ValueError("--messy-input-file must contain non-empty text")
    return value


def _project_prompt_packet(
    packet: dict[str, Any],
    patch_library: PromptPatchLibrary,
    *,
    include_prompt_patches: list[str] | None = None,
    exclude_prompt_patches: list[str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    canonical_selected = list(packet.get("selected_prompt_patches", []))
    included_ids: list[str] = []
    included_seen: set[str] = set()
    for patch_id in include_prompt_patches or []:
        if not isinstance(patch_id, str):
            continue
        normalized = patch_id.strip()
        if not normalized or normalized in included_seen:
            continue
        included_seen.add(normalized)
        included_ids.append(normalized)
    excluded_ids = {
        patch_id.strip()
        for patch_id in (exclude_prompt_patches or [])
        if isinstance(patch_id, str) and patch_id.strip()
    }

    projected = deepcopy(packet)
    final_selected: list[str] = []
    seen: set[str] = set()
    for patch_id in canonical_selected + included_ids:
        if patch_id in excluded_ids or patch_id in seen:
            continue
        if patch_id not in patch_library.patch_ids:
            raise ValueError(f"unknown prompt patch id in projection: {patch_id}")
        seen.add(patch_id)
        final_selected.append(patch_id)

    projected["selected_prompt_patches"] = final_selected
    selected_patches = [patch_library.get(patch_id) for patch_id in final_selected]
    projected["rendered_patch_deltas"] = (
        render_prompt_deltas(selected_patches) if selected_patches else "No prompt patches selected.\n"
    )
    projected["output_contract"] = build_model_prompt_output_contract(projected, patch_library)
    provenance = deepcopy(projected.get("provenance", {}))
    provenance["prompt_projection"] = {
        "canonical_selected_prompt_patches": canonical_selected,
        "explicitly_included_prompt_patches": included_ids,
        "explicitly_excluded_prompt_patches": sorted(excluded_ids),
        "final_selected_prompt_patches": final_selected,
    }
    projected["provenance"] = provenance
    projection_summary = {
        "canonical_selected_prompt_patches": canonical_selected,
        "explicitly_included_prompt_patches": included_ids,
        "explicitly_excluded_prompt_patches": sorted(excluded_ids),
        "final_selected_prompt_patches": final_selected,
    }
    return projected, projection_summary


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_json(path: Path, *, kind: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"missing {kind}: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {kind}: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{kind} must be a JSON object")
    return payload


def _sha256_text(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_bytes(data: bytes) -> str:
    import hashlib

    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json_object_file(path: Path, *, kind: str) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"missing {kind}: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {kind}: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{kind} must be a JSON object")
    return payload


def _parse_field_list_from_text(text: str, prefix: str) -> list[str]:
    if not text.startswith(prefix):
        return []
    return [field.strip() for field in text[len(prefix):].split(",") if field.strip()]


def _derive_missing_required_fields(validation_payload: dict[str, Any]) -> list[str]:
    missing_required_fields = validation_payload.get("missing_required_fields")
    if isinstance(missing_required_fields, list):
        return missing_required_fields

    checks = validation_payload.get("checks")
    if isinstance(checks, list):
        for check in checks:
            if not isinstance(check, dict):
                continue
            if check.get("check_id") != "required_fields" or check.get("status") != "failed":
                continue
            message = check.get("message")
            if isinstance(message, str):
                parsed = _parse_field_list_from_text(message, "Missing required fields: ")
                if parsed:
                    return parsed

    diagnostics = validation_payload.get("diagnostics")
    if isinstance(diagnostics, list):
        for diagnostic in diagnostics:
            if not isinstance(diagnostic, str):
                continue
            parsed = _parse_field_list_from_text(
                diagnostic,
                "Required fields missing from parsed output: ",
            )
            if parsed:
                return parsed

    return []


def _ingest_command(run_dir: Path, raw_output_file: Path) -> str:
    return (
        "python3 local_harness/run_manual_supervised_attempt.py ingest "
        f"--run-dir {run_dir} --raw-output-file {raw_output_file}"
    )


def _operator_instructions_text(run_dir: Path) -> str:
    return (
        "Manual Supervised Attempt Instructions\n\n"
        "1) Open model_prompt_packet.md and paste it into your model manually.\n"
        "2) Save the model response exactly as raw_model_output.txt.\n"
        "3) Do not execute commands from model output.\n"
        "4) Do not modify files from model output.\n"
        "5) Run ingest next:\n\n"
        f"{_ingest_command(run_dir, run_dir / 'raw_model_output.txt')}\n"
    )


def _call_local_url(endpoint: str) -> str:
    base = endpoint.strip()
    if not base:
        raise ValueError("--endpoint must be a non-empty string")
    return f"{base.rstrip('/')}/chat/completions"


def _call_local_metadata_payload(
    *,
    endpoint: str,
    model: str,
    temperature: float,
    max_tokens: int,
    prompt_path: Path,
    prompt_text: str,
    raw_output_path: Path,
    raw_output_text: str,
    request_body_sha256: str | None = None,
    request_body_length: int | None = None,
    response_schema_path: Path | None = None,
    response_schema_source_path: Path | None = None,
    response_format: dict[str, Any] | None = None,
    response_payload: dict[str, Any] | None = None,
    response_status: int | None = None,
) -> dict[str, Any]:
    response_envelope: dict[str, Any] = {}
    if response_payload is not None:
        choices = response_payload.get("choices")
        first_choice = choices[0] if isinstance(choices, list) and choices else None
        if isinstance(first_choice, dict):
            finish_reason = first_choice.get("finish_reason")
            if finish_reason is not None:
                response_envelope["finish_reason"] = finish_reason
        usage = response_payload.get("usage")
        if isinstance(usage, dict):
            usage_payload: dict[str, Any] = {}
            for field in ("prompt_tokens", "completion_tokens", "total_tokens"):
                if usage.get(field) is not None:
                    usage_payload[field] = usage.get(field)
            if usage_payload:
                response_envelope["usage"] = usage_payload
            timings = usage.get("timings")
            if isinstance(timings, dict) and timings:
                response_envelope["timings"] = timings
        for field in ("id", "model", "created", "system_fingerprint"):
            if response_payload.get(field) is not None:
                response_envelope[field] = response_payload.get(field)
        if response_status is not None:
            response_envelope["response_status"] = response_status
        if response_envelope:
            response_envelope["response_body_sha256"] = _sha256_text(json.dumps(response_payload, sort_keys=True))
    structured_output: dict[str, Any] = {
        "enabled": response_format is not None,
        "mechanism": "openai_json_schema" if response_format is not None else None,
    }
    if response_schema_path is not None:
        structured_output["schema_path"] = response_schema_path.name
        structured_output["schema_sha256"] = _sha256_file(response_schema_path)
        structured_output["schema_length"] = len(response_schema_path.read_bytes())
    if response_schema_source_path is not None:
        structured_output["schema_source_path"] = str(response_schema_source_path)
    if response_format is not None:
        structured_output["response_format"] = response_format
    return {
        "source": "local_openai_compatible_endpoint",
        "endpoint": endpoint,
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "prompt_path": prompt_path.name,
        "prompt_sha256": _sha256_text(prompt_text),
        "prompt_length": len(prompt_text),
        "raw_output_path": raw_output_path.name,
        "raw_output_sha256": _sha256_text(raw_output_text),
        "raw_output_length": len(raw_output_text),
        "request_body_sha256": request_body_sha256,
        "request_body_length": request_body_length,
        "structured_output": structured_output,
        "call_status": "completed",
        "review_required": True,
        "request_provenance": {
            "api": "openai-chat",
            "endpoint": endpoint,
            "request_url": _call_local_url(endpoint),
            "model": model,
            "configured_model": model,
            "resolved_model": model,
            "prompt_path": prompt_path.name,
            "prompt_sha256": _sha256_text(prompt_text),
            "prompt_length": len(prompt_text),
            "max_tokens": max_tokens,
            "temperature": temperature,
            "request_body_sha256": request_body_sha256,
            "request_body_length": request_body_length,
            "structured_output_enabled": response_format is not None,
            "structured_output_mechanism": "openai_json_schema" if response_format is not None else None,
            "response_format": response_format,
        },
        "response_provenance": {
            "raw_output_path": raw_output_path.name,
            "raw_output_sha256": _sha256_text(raw_output_text),
            "raw_output_length": len(raw_output_text),
            "model": model,
            "structured_output": structured_output,
            **({"endpoint_response": response_envelope} if response_envelope else {}),
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


def _call_local_failure_authority_boundaries() -> list[str]:
    return [
        "Failed local model call is evidence, not acceptance.",
        "No command execution authority is granted.",
        "No file modification authority is granted.",
        "No patch promotion authority is granted.",
        "No automatic training authority is granted.",
        "No default failure-to-curriculum capture authority is granted.",
        "Ingest and explicit review are required before downstream use.",
    ]


def _write_call_local_failure_evidence(
    *,
    run_dir: Path,
    endpoint: str,
    model: str,
    temperature: float,
    max_tokens: int,
    timeout_seconds: float,
    prompt_path: Path,
    raw_output_path: Path,
    failure_reason: str,
    response_status: int | None = None,
    response_body_json: dict[str, Any] | None = None,
    response_body_text: str | None = None,
    error_message: str | None = None,
) -> None:
    failure_payload: dict[str, Any] = {
        "source": "local_openai_compatible_endpoint",
        "call_status": "failed",
        "failure_reason": failure_reason,
        "endpoint": endpoint,
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "timeout_seconds": timeout_seconds,
        "prompt_path": prompt_path.name,
        "raw_output_path": raw_output_path.name,
        "review_required": True,
        "authority_boundaries": _call_local_failure_authority_boundaries(),
    }
    if response_status is not None:
        failure_payload["response_status"] = response_status
    if error_message is not None:
        failure_payload["error_message"] = error_message
    if response_body_json is not None:
        failure_payload["response_body_json"] = response_body_json
    if response_body_text is not None:
        failure_payload["response_body_text"] = response_body_text
    _write_json(run_dir / "local_model_call.failed.json", failure_payload)

    if response_body_json is not None or response_body_text is not None:
        response_payload: dict[str, Any] = {
            "source": "local_openai_compatible_endpoint",
            "call_status": "failed",
            "failure_reason": failure_reason,
        }
        if response_status is not None:
            response_payload["response_status"] = response_status
        if response_body_json is not None:
            response_payload["response_body_json"] = response_body_json
        if response_body_text is not None:
            response_payload["response_body_text"] = response_body_text
        _write_json(run_dir / "local_model_response.failed.json", response_payload)


def _is_timeout_reason(reason: object) -> bool:
    if isinstance(reason, (socket.timeout, TimeoutError)):
        return True
    if isinstance(reason, str):
        lowered = reason.lower()
        return "timed out" in lowered or "timeout" in lowered
    return False


def _build_retry_payload_skeleton(output_contract: dict[str, Any]) -> dict[str, Any]:
    required_fields = output_contract.get("required_fields")
    if not isinstance(required_fields, list):
        return {}
    skeleton: dict[str, Any] = {}
    for field in required_fields:
        if not isinstance(field, str) or not field.strip():
            continue
        if field in {"allowed_targets", "held_targets", "claims", "evidence_basis", "unverified_claims"}:
            skeleton[field] = []
        elif field == "scope_expansion_required":
            skeleton[field] = False
        elif field == "format":
            skeleton[field] = "json"
        elif field == "required_fields_present":
            skeleton[field] = True
        elif field == "reason":
            skeleton[field] = ""
        else:
            skeleton[field] = None
    return skeleton


def _read_evidence_source(path: Path, *, max_chars: int) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"missing evidence source: {path}")
    text = path.read_text(encoding="utf-8")
    excerpt = text if len(text) <= max_chars else text[:max_chars].rstrip() + "\n...[trimmed]"
    return {
        "path": str(path),
        "sha256": _sha256_file(path),
        "byte_length": len(path.read_bytes()),
        "char_length": len(text),
        "excerpt": excerpt,
        "truncated": len(text) > max_chars,
    }


def _estimate_tokens_from_text(text: str) -> int:
    return max(1, math.ceil(len(text) / 4))


def _prepare_evidence_budget(
    *,
    prompt_text: str,
    evidence_projection_packet: dict[str, Any],
    prompt_token_budget: int,
    response_reserve_tokens: int,
    overhead_tokens: int,
) -> dict[str, Any]:
    evidence_sources = evidence_projection_packet.get("evidence_sources", [])
    supplied_chars = sum(
        int(source.get("char_length", 0)) for source in evidence_sources if isinstance(source, dict)
    )
    supplied_excerpt_chars = sum(
        len(str(source.get("excerpt", ""))) for source in evidence_sources if isinstance(source, dict)
    )
    estimated_prompt_tokens = _estimate_tokens_from_text(prompt_text)
    available_prompt_tokens = max(0, prompt_token_budget - response_reserve_tokens - overhead_tokens)
    budget = {
        "estimation_method": "ceil(prompt_characters / 4)",
        "estimated_prompt_tokens": estimated_prompt_tokens,
        "prompt_token_budget": prompt_token_budget,
        "response_reserve_tokens": response_reserve_tokens,
        "overhead_tokens": overhead_tokens,
        "available_prompt_tokens": available_prompt_tokens,
        "supplied_evidence_characters": supplied_chars,
        "supplied_excerpt_characters": supplied_excerpt_chars,
        "any_source_truncated": any(bool(source.get("truncated")) for source in evidence_sources if isinstance(source, dict)),
        "any_source_excluded": False,
    }
    if estimated_prompt_tokens > available_prompt_tokens:
        budget["status"] = "failed"
        budget["diagnostic"] = (
            f"estimated prompt tokens {estimated_prompt_tokens} exceed available budget "
            f"{available_prompt_tokens} (limit {prompt_token_budget}, reserve {response_reserve_tokens}, overhead {overhead_tokens})"
        )
    else:
        budget["status"] = "passed"
        budget["diagnostic"] = (
            f"estimated prompt tokens {estimated_prompt_tokens} within available budget "
            f"{available_prompt_tokens} (limit {prompt_token_budget}, reserve {response_reserve_tokens}, overhead {overhead_tokens})"
        )
    return budget


def _build_evidence_projection_packet(
    *,
    task_title: str,
    task_summary: str,
    evidence_sources: list[Path],
    max_chars_per_source: int,
) -> dict[str, Any]:
    sources = [_read_evidence_source(path, max_chars=max_chars_per_source) for path in evidence_sources]
    return {
        "task_title": task_title,
        "task_summary": task_summary,
        "evidence_sources": sources,
        "output_contract": deepcopy(EVIDENCE_OUTPUT_CONTRACT),
    }


def _render_evidence_observation_prompt(packet: dict[str, Any]) -> str:
    evidence_json = json.dumps(packet, indent=2, sort_keys=True)
    selected_patches = packet.get("selected_prompt_patches", [])
    rendered_patch_deltas = packet.get("rendered_patch_deltas", "No prompt patches selected.\n")
    return (
        "# ZTH Repository Observation Packet\n\n"
        "## Role\n"
        "You are a bounded model helper operating inside a supervised ZTH workflow.\n\n"
        "## Task\n"
        f"{packet['task_title']}\n\n"
        "## Instructions\n"
        f"{packet['task_summary']}\n\n"
        "## Evidence Packet\n"
        f"```json\n{evidence_json}\n```\n\n"
        "## Prompt Patch Instructions\n"
        f"{json.dumps(selected_patches, indent=2, sort_keys=True)}\n\n"
        "### Rendered Patch Deltas\n"
        f"{rendered_patch_deltas}\n\n"
        "## Required Output Contract\n"
        f"```json\n{json.dumps(EVIDENCE_OUTPUT_CONTRACT, indent=2, sort_keys=True)}\n```\n\n"
        "## Required Response Shape\n"
        "- Return only JSON matching the output contract.\n"
        "- Each finding must include a claim and supporting evidence objects with path and detail fields.\n"
        "- Distinguish supplied evidence from model-generated claims.\n"
        "- Do not claim filesystem authority or additional repository access.\n"
        "- Do not include prose outside the JSON object.\n\n"
        "## Authority Boundaries\n"
        "- no filesystem authority\n"
        "- no command execution authority\n"
        "- no file modification authority\n"
        "- no automatic patch promotion\n"
        "- no automatic training\n"
        "- no default failure-to-curriculum capture\n"
    )


def _load_structured_authorized_targets_for_retry(run_dir: Path) -> list[str] | None:
    manifest_path = run_dir / "run_manifest.json"
    if manifest_path.is_file():
        try:
            manifest = _read_json(manifest_path, kind="run manifest")
        except ValueError:
            manifest = None
        if isinstance(manifest, dict):
            targets = _load_structured_authorized_targets(run_dir, manifest)
            if targets:
                return targets

    for packet_name in ("triage_packet.json", "orchestration_packet.json"):
        packet_path = run_dir / packet_name
        if not packet_path.is_file():
            continue
        payload = _read_json(packet_path, kind="structured authority packet")
        if isinstance(payload.get("allowed_targets"), list):
            targets = [
                target for target in payload["allowed_targets"] if isinstance(target, str) and target.strip()
            ]
            if targets:
                return targets
    return None


def _trim_text(text: str, *, limit: int = 1200) -> str:
    stripped = text.strip()
    if len(stripped) <= limit:
        return stripped
    return stripped[:limit].rstrip() + "\n...[trimmed]"


def _run_retry_contract(*, run_dir: Path, retry_id: int) -> dict[str, Any]:
    if retry_id < 1:
        raise ValueError("--retry-id must be >= 1")
    raw_output_path = run_dir / "raw_model_output.txt"
    validation_path = run_dir / "output_validation.json"
    validation_report_path = run_dir / "output_validation_report.txt"
    prompt_path = run_dir / "model_prompt_packet.md"
    output_contract_path = run_dir / "output_contract.json"
    if not raw_output_path.is_file():
        raise ValueError(f"missing raw_model_output.txt: {raw_output_path}")
    if not validation_path.is_file():
        raise ValueError(f"missing output_validation.json: {validation_path}")
    if not validation_report_path.is_file():
        raise ValueError(f"missing output_validation_report.txt: {validation_report_path}")
    if not prompt_path.is_file():
        raise ValueError(f"missing model_prompt_packet.md: {prompt_path}")
    validation_payload = _read_json(validation_path, kind="output validation")
    if validation_payload.get("validation_status") != "failed":
        raise ValueError("retry-contract requires validation_status == 'failed'")
    output_contract: dict[str, Any] | None = None
    if output_contract_path.is_file():
        output_contract = _read_json(output_contract_path, kind="output contract")

    failure_raw_path = run_dir / f"raw_model_output.failed_{retry_id}.txt"
    failure_validation_path = run_dir / f"output_validation.failed_{retry_id}.json"
    failure_report_path = run_dir / f"output_validation_report.failed_{retry_id}.txt"
    retry_prompt_path = run_dir / f"retry_prompt_to_paste_{retry_id}.md"

    if failure_raw_path.exists() or failure_validation_path.exists() or failure_report_path.exists():
        raise ValueError(f"failed_{retry_id} artifacts already exist")

    failure_raw_path.write_text(raw_output_path.read_text(encoding="utf-8"), encoding="utf-8")
    _write_json(failure_validation_path, validation_payload)
    failure_report_path.write_text(validation_report_path.read_text(encoding="utf-8"), encoding="utf-8")

    diagnostics = validation_payload.get("diagnostics")
    if isinstance(diagnostics, list):
        diagnostic_lines = [str(item) for item in diagnostics if str(item).strip()]
    else:
        diagnostic_lines = []
    checks = validation_payload.get("checks")
    check_lines: list[str] = []
    if isinstance(checks, list):
        for check in checks:
            if not isinstance(check, dict):
                continue
            check_lines.append(
                f"- {check.get('check_id')}: {check.get('status')} - {check.get('message', '')}".rstrip()
            )

    prompt_sections = [
        "Supervised Retry Prompt",
        "",
        "Validation failure summary:",
        f"- validation_status: {validation_payload.get('validation_status')}",
    ]
    if check_lines:
        prompt_sections.extend(["", "Validator checks:"] + check_lines)
    if diagnostic_lines:
        prompt_sections.extend(["", "Validator diagnostics:"] + [f"- {line}" for line in diagnostic_lines])
    prompt_sections.extend(
        [
            "",
            "Previous failed output",
            _trim_text(raw_output_path.read_text(encoding="utf-8")),
        ]
    )
    if output_contract is not None:
        prompt_sections.extend(["", "Required output contract:"])
        prompt_sections.append(json.dumps(output_contract, indent=2, sort_keys=True))
    structured_authorized_targets = _load_structured_authorized_targets_for_retry(run_dir)
    if structured_authorized_targets:
        prompt_sections.extend(
            [
                "",
                "Structured authorized targets available for this run:",
                *[f"- {target}" for target in structured_authorized_targets],
                "allowed_targets must be a subset of the structured authorized targets.",
            ]
        )
    prompt_sections.extend(
        [
            "",
            "Payload repair instructions",
            "Do not return the output contract itself.",
            "Do not return required_fields as a substitute for the payload.",
            "Do not return `required_fields` as a substitute for the payload.",
            "Do not describe the required fields.",
            "Return the actual payload fields required by the contract.",
            "Use the required field names as top-level keys in your JSON object.",
            "The following JSON skeleton is the payload shape only; it is not permission to fabricate evidence:",
        ]
    )
    skeleton = _build_retry_payload_skeleton(output_contract) if output_contract is not None else {}
    if skeleton:
        prompt_sections.append(json.dumps(skeleton, indent=2, sort_keys=True))
    prompt_sections.extend(
        [
            "",
            "Field guidance:",
            "allowed_targets: list only the task-authorized targets.",
            "held_targets: list out-of-scope targets or prohibited actions.",
            "scope_expansion_required: true only if the task cannot be completed within allowed targets.",
            "claims: list claims supported by the provided task/evidence only.",
            "evidence_basis: list the evidence lines or task facts supporting the claims.",
            "unverified_claims: list claims that are not verified by the provided evidence.",
            'format: must be "json".',
            "required_fields_present: must be true only when all required top-level fields are present.",
            "reason: non-empty explanation of why the output stays within scope.",
            "",
            "Final required JSON payload skeleton",
            "Return a JSON object with every top-level key shown in this skeleton.",
            "Do not omit any skeleton key.",
            "Replace placeholder values only when the task evidence supports a more specific value.",
            "If a list has no supported entries, keep it as [].",
            "The final answer must be this payload shape, not the previous failed output.",
        ]
    )
    if skeleton:
        prompt_sections.append(json.dumps(skeleton, indent=2, sort_keys=True))
    prompt_sections.extend(
        [
            "",
            "Return raw JSON only.",
            "Validation is evidence, not acceptance.",
            "No command execution, file modification, promotion, training, model materialization, or default failure-to-curriculum capture is authorized.",
        ]
    )
    retry_prompt_text = "\n".join(prompt_sections).rstrip() + "\n"
    retry_prompt_path.write_text(retry_prompt_text, encoding="utf-8")
    prompt_to_paste_path = run_dir / "prompt_to_paste.md"
    prompt_to_paste_path.write_text(retry_prompt_text, encoding="utf-8")

    return {
        "run_dir": run_dir,
        "retry_id": retry_id,
        "retry_prompt_path": retry_prompt_path,
        "prompt_path": prompt_to_paste_path,
        "failure_raw_path": failure_raw_path,
        "failure_validation_path": failure_validation_path,
        "failure_report_path": failure_report_path,
    }


def _extract_assistant_content(response_payload: dict[str, Any]) -> str:
    choices = response_payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("local endpoint response missing choices")
    first = choices[0]
    if not isinstance(first, dict):
        raise ValueError("local endpoint response choices[0] must be an object")
    message = first.get("message")
    if not isinstance(message, dict):
        raise ValueError("local endpoint response choices[0].message must be an object")
    content = message.get("content")
    if not isinstance(content, str) or not content:
        raise ValueError("local endpoint response missing assistant content")
    return content


def _resolve_run_file(run_dir: Path, path_value: str | Path, *, field: str) -> Path:
    candidate = Path(path_value)
    if not candidate.is_absolute():
        candidate = run_dir / candidate
    if not candidate.is_file():
        raise ValueError(f"missing {field}: {candidate}")
    return candidate


def _prepare_run_dir(*, out_dir: Path, timestamp: str | None, overwrite: bool) -> tuple[str, Path]:
    ts = timestamp or _utc_timestamp()
    if not ts.strip():
        raise ValueError("timestamp must be non-empty when provided")
    out_dir.mkdir(parents=True, exist_ok=True)
    run_dir = out_dir / ts
    if run_dir.exists() and not overwrite:
        raise FileExistsError(f"run directory already exists: {run_dir}")
    run_dir.mkdir(parents=True, exist_ok=overwrite)
    return ts, run_dir


def run_prepare(
    *,
    messy_input: str,
    out_dir: Path,
    timestamp: str | None = None,
    overwrite: bool = False,
    include_prompt_patches: list[str] | None = None,
    exclude_prompt_patches: list[str] | None = None,
    evidence_files: list[Path] | None = None,
    evidence_task_title: str | None = None,
    evidence_task_summary: str | None = None,
    evidence_max_chars: int = 12000,
    evidence_total_budget_tokens: int = 8192,
    evidence_response_reserve_tokens: int = 900,
    evidence_overhead_tokens: int = 512,
    response_schema_file: Path | None = None,
) -> dict[str, Any]:
    ts, run_dir = _prepare_run_dir(out_dir=out_dir, timestamp=timestamp, overwrite=overwrite)

    patch_library = PromptPatchLibrary()
    patch_library.load_dir("examples/prompt_patches")

    triage_id = f"triage_manual_{ts.lower()}"
    orchestration_id = f"orch_manual_{ts.lower()}"
    prompt_packet_id = f"prompt_packet_manual_{ts.lower()}"

    triage_packet = route_messy_input(
        messy_input,
        triage_id=triage_id,
        source="manual_supervised_attempt_prepare",
    )
    validate_triage_packet(triage_packet, model_facing=True)

    orchestration_packet = assemble_orchestration_packet(
        triage_packet,
        patch_library,
        orchestration_id=orchestration_id,
    )
    validate_orchestration_packet(orchestration_packet, patch_library)

    model_prompt_packet = render_model_prompt_packet(orchestration_packet, patch_library)
    canonical_output_contract = build_model_prompt_output_contract(orchestration_packet, patch_library)
    prompt_projection_packet, prompt_projection_summary = _project_prompt_packet(
        orchestration_packet,
        patch_library,
        include_prompt_patches=include_prompt_patches,
        exclude_prompt_patches=exclude_prompt_patches,
    )
    messy_input_path = run_dir / "messy_input.txt"
    prompt_path = run_dir / "model_prompt_packet.md"
    prompt_to_paste_path = run_dir / "prompt_to_paste.md"
    instructions_path = run_dir / "operator_instructions.txt"
    output_contract_path = run_dir / "output_contract.json"
    canonical_output_contract_path = run_dir / "canonical_output_contract.json"
    triage_packet_path = run_dir / "triage_packet.json"
    orchestration_packet_path = run_dir / "orchestration_packet.json"
    projection_summary_path = run_dir / "prompt_projection_summary.json"
    manifest_path = run_dir / "run_manifest.json"
    evidence_projection_packet = None
    evidence_prompt_to_paste = None
    evidence_output_contract: dict[str, Any] | None = None
    selected_response_schema: dict[str, Any] | None = None
    if response_schema_file is not None:
        if not response_schema_file.is_file():
            raise ValueError(f"--response-schema-file does not exist: {response_schema_file}")
        selected_response_schema = _load_json_object_file(response_schema_file, kind="response schema")
    if evidence_files:
        selected_output_contract: dict[str, Any] = deepcopy(EVIDENCE_OUTPUT_CONTRACT)
        if selected_response_schema is not None:
            selected_output_contract = {
                "format": "json",
                "required_fields": list(selected_response_schema.get("required") or []),
                "requires_reason": True,
            }
        evidence_projection_packet = _build_evidence_projection_packet(
            task_title=evidence_task_title or "Repository observation task",
            task_summary=evidence_task_summary or messy_input,
            evidence_sources=evidence_files,
            max_chars_per_source=evidence_max_chars,
        )
        evidence_output_contract = deepcopy(selected_output_contract)
        evidence_projection_packet["output_contract"] = deepcopy(selected_output_contract)
        evidence_projection_packet["selected_prompt_patches"] = list(prompt_projection_packet["selected_prompt_patches"])
        evidence_projection_packet["rendered_patch_deltas"] = prompt_projection_packet["rendered_patch_deltas"]
        if selected_response_schema is not None:
            evidence_projection_packet["response_schema"] = selected_response_schema
        evidence_prompt_to_paste = _render_evidence_observation_prompt(evidence_projection_packet)
        evidence_budget = _prepare_evidence_budget(
            prompt_text=evidence_prompt_to_paste,
            evidence_projection_packet=evidence_projection_packet,
            prompt_token_budget=evidence_total_budget_tokens,
            response_reserve_tokens=evidence_response_reserve_tokens,
            overhead_tokens=evidence_overhead_tokens,
        )
        evidence_projection_packet["budget"] = evidence_budget
        if evidence_budget["status"] == "failed":
            evidence_projection_path = run_dir / "evidence_projection.json"
            evidence_projection_md_path = run_dir / "evidence_projection.md"
            _write_json(evidence_projection_path, evidence_projection_packet)
            evidence_projection_md_path.write_text(evidence_prompt_to_paste or "", encoding="utf-8")
            prompt_projection_summary["evidence_projection_path"] = evidence_projection_path.name
            prompt_projection_summary["evidence_projection_md_path"] = evidence_projection_md_path.name
            prompt_projection_summary["evidence_source_count"] = len(evidence_projection_packet["evidence_sources"])
            prompt_projection_summary["evidence_output_contract_sha256"] = _sha256_text(
                json.dumps(EVIDENCE_OUTPUT_CONTRACT, indent=2, sort_keys=True) + "\n"
            )
            prompt_projection_summary["evidence_budget"] = evidence_budget
            _write_json(projection_summary_path, prompt_projection_summary)
            _write_json(canonical_output_contract_path, canonical_output_contract)
            _write_json(output_contract_path, EVIDENCE_OUTPUT_CONTRACT)
            _write_json(triage_packet_path, triage_packet)
            _write_json(orchestration_packet_path, orchestration_packet)
            _write_json(manifest_path, {
                "report_type": "manual_supervised_attempt_run_manifest.v1",
                "run_id": f"manual_supervised_attempt_{ts.lower()}",
                "created_at": _utc_iso(),
                "run_status": "prepared",
                "triage_id": triage_packet["triage_id"],
                "orchestration_id": orchestration_packet["orchestration_id"],
                "prompt_packet_id": prompt_packet_id,
                "artifacts": {
                    "messy_input": str(messy_input_path),
                    "model_prompt_packet": str(prompt_path),
                    "prompt_to_paste": str(prompt_to_paste_path),
                    "prompt_projection_summary": str(projection_summary_path),
                    "operator_instructions": str(instructions_path),
                    "canonical_output_contract": str(canonical_output_contract_path),
                    "output_contract": str(output_contract_path),
                    "triage_packet": str(triage_packet_path),
                    "orchestration_packet": str(orchestration_packet_path),
                    "evidence_projection": str(evidence_projection_path),
                    "evidence_projection_md": str(evidence_projection_md_path),
                },
            })
            raise ValueError(evidence_budget["diagnostic"])
        _write_json(
            run_dir / "response_schema.json",
            selected_response_schema if selected_response_schema is not None else json.loads(EVIDENCE_RESPONSE_SCHEMA_PATH.read_text(encoding="utf-8")),
        )

    prompt_to_paste = evidence_prompt_to_paste or render_model_prompt_packet(prompt_projection_packet, patch_library)
    projected_output_contract = (
        evidence_output_contract if evidence_output_contract is not None else build_model_prompt_output_contract(prompt_projection_packet, patch_library)
    )

    messy_input_path.write_text(messy_input + "\n", encoding="utf-8")
    prompt_path.write_text(model_prompt_packet.rstrip() + "\n", encoding="utf-8")
    prompt_to_paste_path.write_text(prompt_to_paste.rstrip() + "\n", encoding="utf-8")
    prompt_projection_summary["canonical_output_contract_sha256"] = _sha256_text(
        json.dumps(canonical_output_contract, indent=2, sort_keys=True) + "\n"
    )
    prompt_projection_summary["projected_output_contract_sha256"] = _sha256_text(
        json.dumps(projected_output_contract, indent=2, sort_keys=True) + "\n"
    )
    prompt_projection_summary["canonical_output_contract_path"] = canonical_output_contract_path.name
    prompt_projection_summary["projected_output_contract_path"] = output_contract_path.name
    if evidence_projection_packet is not None:
        evidence_projection_path = run_dir / "evidence_projection.json"
        evidence_projection_md_path = run_dir / "evidence_projection.md"
        _write_json(evidence_projection_path, evidence_projection_packet)
        evidence_projection_md_path.write_text(evidence_prompt_to_paste or "", encoding="utf-8")
        prompt_projection_summary["evidence_projection_path"] = evidence_projection_path.name
        prompt_projection_summary["evidence_projection_md_path"] = evidence_projection_md_path.name
        prompt_projection_summary["evidence_source_count"] = len(evidence_projection_packet["evidence_sources"])
        prompt_projection_summary["evidence_output_contract_sha256"] = _sha256_text(
            json.dumps(projected_output_contract, indent=2, sort_keys=True) + "\n"
        )
        if selected_response_schema is not None:
            prompt_projection_summary["selected_response_schema_sha256"] = _sha256_text(
                json.dumps(selected_response_schema, indent=2, sort_keys=True) + "\n"
            )
        prompt_projection_summary["evidence_budget"] = evidence_projection_packet["budget"]
    _write_json(projection_summary_path, prompt_projection_summary)
    instructions_path.write_text(_operator_instructions_text(run_dir), encoding="utf-8")
    _write_json(canonical_output_contract_path, canonical_output_contract)
    _write_json(output_contract_path, projected_output_contract)
    _write_json(triage_packet_path, triage_packet)
    _write_json(orchestration_packet_path, orchestration_packet)

    manifest = {
        "report_type": "manual_supervised_attempt_run_manifest.v1",
        "run_id": f"manual_supervised_attempt_{ts.lower()}",
        "created_at": _utc_iso(),
        "run_status": "prepared",
        "triage_id": triage_packet["triage_id"],
        "orchestration_id": orchestration_packet["orchestration_id"],
        "prompt_packet_id": prompt_packet_id,
        "artifacts": {
            "messy_input": str(messy_input_path),
            "model_prompt_packet": str(prompt_path),
            "prompt_to_paste": str(prompt_to_paste_path),
            "prompt_projection_summary": str(projection_summary_path),
            "operator_instructions": str(instructions_path),
            "canonical_output_contract": str(canonical_output_contract_path),
            "output_contract": str(output_contract_path),
            "triage_packet": str(triage_packet_path),
            "orchestration_packet": str(orchestration_packet_path),
            **(
                {
                    "evidence_projection": str(evidence_projection_path),
                    "evidence_projection_md": str(evidence_projection_md_path),
                    "response_schema": str(run_dir / "response_schema.json"),
                }
                if evidence_projection_packet is not None
                else {}
            ),
        },
    }
    _write_json(manifest_path, manifest)

    return {
        "run_dir": run_dir,
        "manifest_path": manifest_path,
        "model_prompt_packet_path": prompt_path,
        "prompt_to_paste_path": prompt_to_paste_path,
        "prompt_projection_summary_path": projection_summary_path,
        "canonical_output_contract_path": canonical_output_contract_path,
        "output_contract_path": output_contract_path,
        "response_schema_path": run_dir / "response_schema.json",
    }


def run_session(
    *,
    messy_input: str,
    out_dir: Path,
    timestamp: str | None = None,
    overwrite: bool = False,
    write_prompt_copy: bool = False,
    include_prompt_patches: list[str] | None = None,
    exclude_prompt_patches: list[str] | None = None,
    evidence_files: list[Path] | None = None,
    evidence_task_title: str | None = None,
    evidence_task_summary: str | None = None,
    evidence_max_chars: int = 12000,
    evidence_total_budget_tokens: int = 8192,
    evidence_response_reserve_tokens: int = 900,
    evidence_overhead_tokens: int = 512,
    response_schema_file: Path | None = None,
) -> dict[str, Any]:
    prepare_result = run_prepare(
        messy_input=messy_input,
        out_dir=out_dir,
        timestamp=timestamp,
        overwrite=overwrite,
        include_prompt_patches=include_prompt_patches,
        exclude_prompt_patches=exclude_prompt_patches,
        evidence_files=evidence_files,
        evidence_task_title=evidence_task_title,
        evidence_task_summary=evidence_task_summary,
        evidence_max_chars=evidence_max_chars,
        evidence_total_budget_tokens=evidence_total_budget_tokens,
        evidence_response_reserve_tokens=evidence_response_reserve_tokens,
        evidence_overhead_tokens=evidence_overhead_tokens,
        response_schema_file=response_schema_file,
    )
    run_dir = Path(prepare_result["run_dir"])
    model_prompt_packet_path = Path(prepare_result["model_prompt_packet_path"])
    prompt_to_paste_path = Path(prepare_result["prompt_to_paste_path"])
    raw_output_path = run_dir / "raw_model_output.txt"

    raw_output_path.write_text("", encoding="utf-8")

    return {
        "run_dir": run_dir,
        "manifest_path": Path(prepare_result["manifest_path"]),
        "model_prompt_packet_path": model_prompt_packet_path,
        "prompt_to_paste_path": prompt_to_paste_path,
        "prompt_projection_summary_path": Path(prepare_result["prompt_projection_summary_path"]),
        "raw_output_file_path": raw_output_path,
        "ingest_command": _ingest_command(run_dir, raw_output_path),
        "write_prompt_copy": write_prompt_copy,
    }


def run_call_local(
    *,
    run_dir: Path,
    endpoint: str,
    model: str,
    temperature: float,
    max_tokens: int,
    timeout_seconds: float,
    overwrite: bool,
    response_schema_file: Path | None = None,
) -> dict[str, Any]:
    prompt_path = run_dir / "prompt_to_paste.md"
    if not prompt_path.is_file():
        model_prompt_packet_path = run_dir / "model_prompt_packet.md"
        if not model_prompt_packet_path.is_file():
            raise ValueError(f"missing prompt_to_paste.md: {prompt_path}")
        prompt_path.write_text(model_prompt_packet_path.read_text(encoding="utf-8"), encoding="utf-8")
    prompt_text = prompt_path.read_text(encoding="utf-8")
    if not prompt_text.strip():
        raise ValueError("prompt_to_paste.md must contain non-empty text")

    raw_output_path = run_dir / "raw_model_output.txt"
    if raw_output_path.exists() and raw_output_path.read_text(encoding="utf-8") and not overwrite:
        raise ValueError("raw_model_output.txt is non-empty; use --overwrite to replace it")

    response_schema_path: Path | None = None
    response_schema_source_path: Path | None = None
    response_format: dict[str, Any] | None = None
    if response_schema_file is None and (run_dir / "response_schema.json").is_file():
        response_schema_file = run_dir / "response_schema.json"
    if response_schema_file is not None:
        if not response_schema_file.is_file():
            raise ValueError(f"--response-schema-file does not exist: {response_schema_file}")
        response_schema_source_path = response_schema_file
        response_schema_payload = _load_json_object_file(response_schema_file, kind="response schema")
        response_schema_path = run_dir / "response_schema.json"
        if response_schema_file.resolve() != response_schema_path.resolve():
            shutil.copyfile(response_schema_file, response_schema_path)
        elif not response_schema_path.exists():
            response_schema_path.write_text(response_schema_file.read_text(encoding="utf-8"), encoding="utf-8")
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "zth_structured_output",
                "strict": True,
                "schema": response_schema_payload,
            },
        }

    request_url = _call_local_url(endpoint)
    request_payload = {
        "model": _require_nonempty(model, field="--model"),
        "messages": [{"role": "user", "content": prompt_text}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if response_format is not None:
        request_payload["response_format"] = response_format
    request_bytes = json.dumps(request_payload).encode("utf-8")
    request_body_sha256 = _sha256_bytes(request_bytes)
    request = urllib.request.Request(
        request_url,
        data=request_bytes,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            status_code = getattr(response, "status", response.getcode())
            body = response.read().decode("utf-8")
    except (socket.timeout, TimeoutError) as exc:
        _write_call_local_failure_evidence(
            run_dir=run_dir,
            endpoint=endpoint,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout_seconds=timeout_seconds,
            prompt_path=prompt_path,
            raw_output_path=raw_output_path,
            failure_reason="timeout",
            error_message=f"local endpoint timed out: {exc}",
        )
        raise RuntimeError(f"local endpoint timed out: {exc}") from exc
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        try:
            parsed_error_body = json.loads(error_body)
        except json.JSONDecodeError:
            parsed_error_body = None
        if not isinstance(parsed_error_body, dict):
            parsed_error_body = None
        _write_call_local_failure_evidence(
            run_dir=run_dir,
            endpoint=endpoint,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout_seconds=timeout_seconds,
            prompt_path=prompt_path,
            raw_output_path=raw_output_path,
            failure_reason="http_error",
            response_status=exc.code,
            response_body_json=parsed_error_body,
            response_body_text=error_body if parsed_error_body is None else None,
            error_message=f"local endpoint returned HTTP {exc.code}: {error_body}",
        )
        raise RuntimeError(f"local endpoint returned HTTP {exc.code}: {error_body}") from exc
    except urllib.error.URLError as exc:
        failure_reason = "timeout" if _is_timeout_reason(getattr(exc, "reason", None)) else "connection_failed"
        _write_call_local_failure_evidence(
            run_dir=run_dir,
            endpoint=endpoint,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout_seconds=timeout_seconds,
            prompt_path=prompt_path,
            raw_output_path=raw_output_path,
            failure_reason=failure_reason,
            error_message=f"local endpoint connection failed: {exc.reason}",
        )
        raise RuntimeError(f"local endpoint connection failed: {exc.reason}") from exc

    if status_code < 200 or status_code >= 300:
        _write_call_local_failure_evidence(
            run_dir=run_dir,
            endpoint=endpoint,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout_seconds=timeout_seconds,
            prompt_path=prompt_path,
            raw_output_path=raw_output_path,
            failure_reason="non_2xx_status",
            response_status=status_code,
            response_body_text=body,
            error_message=f"local endpoint returned non-2xx status: {status_code}",
        )
        raise RuntimeError(f"local endpoint returned non-2xx status: {status_code}")

    try:
        response_payload = json.loads(body)
    except json.JSONDecodeError as exc:
        _write_call_local_failure_evidence(
            run_dir=run_dir,
            endpoint=endpoint,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout_seconds=timeout_seconds,
            prompt_path=prompt_path,
            raw_output_path=raw_output_path,
            failure_reason="malformed_response_json",
            response_status=status_code,
            response_body_text=body,
            error_message="local endpoint returned malformed JSON",
        )
        raise RuntimeError("local endpoint returned malformed JSON") from exc
    if not isinstance(response_payload, dict):
        _write_call_local_failure_evidence(
            run_dir=run_dir,
            endpoint=endpoint,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout_seconds=timeout_seconds,
            prompt_path=prompt_path,
            raw_output_path=raw_output_path,
            failure_reason="response_not_json_object",
            response_status=status_code,
            response_body_text=body,
            error_message="local endpoint response must be a JSON object",
        )
        raise RuntimeError("local endpoint response must be a JSON object")

    try:
        assistant_content = _extract_assistant_content(response_payload)
    except ValueError as exc:
        _write_call_local_failure_evidence(
            run_dir=run_dir,
            endpoint=endpoint,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout_seconds=timeout_seconds,
            prompt_path=prompt_path,
            raw_output_path=raw_output_path,
            failure_reason="missing_assistant_content",
            response_status=status_code,
            response_body_json=response_payload,
            error_message=str(exc),
        )
        raise RuntimeError(str(exc)) from exc
    raw_output_path.write_text(assistant_content, encoding="utf-8")

    metadata_path = run_dir / "local_model_call.json"
    metadata_payload = _call_local_metadata_payload(
        endpoint=endpoint,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        prompt_path=prompt_path,
        prompt_text=prompt_text,
        raw_output_path=raw_output_path,
        raw_output_text=assistant_content,
        request_body_sha256=request_body_sha256,
        request_body_length=len(request_bytes),
        response_schema_path=response_schema_path,
        response_schema_source_path=response_schema_source_path,
        response_format=response_format,
        response_payload=response_payload,
        response_status=status_code,
    )
    _write_json(metadata_path, metadata_payload)

    return {
        "run_dir": run_dir,
        "endpoint": endpoint,
        "model": model,
        "raw_output_path": raw_output_path,
        "local_model_call_path": metadata_path,
        "ingest_command": _ingest_command(run_dir, raw_output_path),
    }


def run_export_pattern(
    *,
    run_dir: Path,
    failure_raw: Path,
    failure_validation: Path,
    retry_prompt: Path,
    success_raw: Path,
    success_validation: Path,
    out_dir: Path,
    pattern_id: str,
    overwrite: bool,
) -> dict[str, Any]:
    resolved_pattern_id = _require_nonempty(pattern_id, field="--pattern-id")
    failure_raw_path = _resolve_run_file(run_dir, failure_raw, field="--failure-raw")
    failure_validation_path = _resolve_run_file(run_dir, failure_validation, field="--failure-validation")
    retry_prompt_path = _resolve_run_file(run_dir, retry_prompt, field="--retry-prompt")
    success_raw_path = _resolve_run_file(run_dir, success_raw, field="--success-raw")
    success_validation_path = _resolve_run_file(run_dir, success_validation, field="--success-validation")

    review_decision_path = run_dir / "review_decision.json"
    gate_path = run_dir / "downstream_use_gate.json"
    handoff_path = run_dir / "handoff_packet.json"

    failure_raw_text = failure_raw_path.read_text(encoding="utf-8")
    retry_prompt_text = retry_prompt_path.read_text(encoding="utf-8")
    success_raw_text = success_raw_path.read_text(encoding="utf-8")
    failure_validation_payload = _read_json(failure_validation_path, kind="failure validation")
    success_validation_payload = _read_json(success_validation_path, kind="success validation")

    local_call_metadata_path = run_dir / "local_model_call.json"
    local_call_metadata = _read_json(local_call_metadata_path, kind="local model call metadata") if local_call_metadata_path.is_file() else {}

    out_dir.mkdir(parents=True, exist_ok=True)
    pattern_path = out_dir / f"{resolved_pattern_id}.json"
    if pattern_path.exists() and not overwrite:
        raise ValueError(f"pattern already exists: {pattern_path}; use --overwrite to replace")

    missing_required_fields = _derive_missing_required_fields(failure_validation_payload)
    validator_diagnostics = failure_validation_payload.get("diagnostics")
    if not isinstance(validator_diagnostics, list):
        validator_diagnostics = failure_validation_payload.get("validator_diagnostics")
    if not isinstance(validator_diagnostics, list):
        validator_diagnostics = []

    review_status = "review_required"
    if review_decision_path.is_file():
        review_payload = _read_json(review_decision_path, kind="review decision")
        decision = review_payload.get("decision")
        if isinstance(decision, str) and decision == "accepted":
            review_status = "accepted_if_review_artifact_present"
        elif isinstance(decision, str) and decision:
            review_status = decision

    export_payload: dict[str, Any] = {
        "pattern_id": resolved_pattern_id,
        "artifact_type": "supervised_failure_success_training_pattern_candidate",
        "status": "candidate",
        "source": "explicit_operator_export",
        "not_training_data_until_reviewed": True,
        "not_automatic_curriculum_capture": True,
        "run_provenance": {
            "run_dir": str(run_dir),
            "model": local_call_metadata.get("model"),
            "endpoint_kind": local_call_metadata.get("source"),
            "temperature": local_call_metadata.get("temperature"),
            "max_tokens": local_call_metadata.get("max_tokens"),
        },
        "failure": {
            "failure_summary": "Model returned output that failed required contract validation.",
            "raw_output": failure_raw_text,
            "validation_status": failure_validation_payload.get("validation_status"),
            "missing_required_fields": missing_required_fields,
            "validator_diagnostics": validator_diagnostics,
        },
        "correction": {
            "correction_strategy": "Apply explicit retry guidance from supervised correction prompt.",
            "retry_prompt": retry_prompt_text,
        },
        "success": {
            "raw_output": success_raw_text,
            "validation_status": success_validation_payload.get("validation_status"),
            "review_status": review_status,
        },
        "learning_signal": {
            "failure_mode": "contract_validation_failure_recovered_by_explicit_retry_prompt",
            "desired_behavior": "Return contract-complete output that passes validator checks after correction guidance.",
            "useful_for": [
                "SFT candidate review",
                "LoRA curriculum candidate review",
                "prompt-patch regression fixture",
                "validator regression fixture",
            ],
        },
        "authority_boundaries": [
            "This artifact is evidence, not training authority.",
            "This artifact is not automatically included in any curriculum.",
            "No automatic training authority is granted.",
            "No patch promotion authority is granted.",
            "No command execution authority is granted.",
            "No file modification authority is granted.",
        ],
    }

    if gate_path.is_file():
        export_payload["review_gate_status"] = _read_json(gate_path, kind="downstream gate").get("gate_status")
    if handoff_path.is_file():
        export_payload["handoff_status"] = _read_json(handoff_path, kind="handoff packet").get("handoff_status")

    _write_json(pattern_path, export_payload)
    return {
        "pattern_path": pattern_path,
        "pattern_id": resolved_pattern_id,
        "run_dir": run_dir,
    }


def _resolve_manifest(run_dir: Path) -> tuple[dict[str, Any], Path]:
    manifest_path = run_dir / "run_manifest.json"
    manifest = _read_json(manifest_path, kind="run manifest")
    if manifest.get("report_type") != "manual_supervised_attempt_run_manifest.v1":
        raise ValueError("run manifest report_type must be manual_supervised_attempt_run_manifest.v1")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict):
        raise ValueError("run manifest artifacts must be an object")
    return manifest, manifest_path


def _load_structured_authorized_targets(run_dir: Path, manifest: dict[str, Any]) -> list[str] | None:
    candidate_paths: list[Path] = []
    artifacts = manifest.get("artifacts")
    if isinstance(artifacts, dict):
        for candidate_path in [artifacts.get("triage_packet"), artifacts.get("orchestration_packet")]:
            if isinstance(candidate_path, str) and candidate_path.strip():
                path = Path(candidate_path)
                if not path.is_absolute():
                    path = run_dir / path
                candidate_paths.append(path)

    manifest_packet_paths = [run_dir / "triage_packet.json", run_dir / "orchestration_packet.json"]
    candidate_paths.extend(manifest_packet_paths)

    seen_paths: set[Path] = set()
    for path in candidate_paths:
        if path in seen_paths:
            continue
        seen_paths.add(path)
        if not path.is_file():
            continue
        payload = _read_json(path, kind="structured authority packet")
        if isinstance(payload.get("allowed_targets"), list):
            allowed_targets = [
                target for target in payload["allowed_targets"] if isinstance(target, str) and target.strip()
            ]
            if allowed_targets:
                return allowed_targets
    return None


def _load_structured_authority_targets(
    run_dir: Path, manifest: dict[str, Any]
) -> tuple[list[str] | None, list[str] | None]:
    candidate_paths: list[Path] = []
    artifacts = manifest.get("artifacts")
    if isinstance(artifacts, dict):
        for candidate_path in [artifacts.get("triage_packet"), artifacts.get("orchestration_packet")]:
            if isinstance(candidate_path, str) and candidate_path.strip():
                path = Path(candidate_path)
                if not path.is_absolute():
                    path = run_dir / path
                candidate_paths.append(path)

    candidate_paths.extend([run_dir / "triage_packet.json", run_dir / "orchestration_packet.json"])
    allowed_targets: list[str] | None = None
    held_targets: list[str] | None = None
    seen_paths: set[Path] = set()
    for path in candidate_paths:
        if path in seen_paths or not path.is_file():
            continue
        seen_paths.add(path)
        payload = _read_json(path, kind="structured authority packet")
        if allowed_targets is None and isinstance(payload.get("allowed_targets"), list):
            allowed_targets = [
                target for target in payload["allowed_targets"] if isinstance(target, str) and target.strip()
            ] or None
        if held_targets is None and isinstance(payload.get("held_targets"), list):
            held_targets = [
                target for target in payload["held_targets"] if isinstance(target, str) and target.strip()
            ] or None
        if allowed_targets is not None and held_targets is not None:
            break
    return allowed_targets, held_targets


def _require_nonempty(value: str | None, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value


def run_ingest(
    *,
    run_dir: Path,
    raw_output_file: Path,
    model_call_metadata_file: Path | None = None,
    transport_qualification_ref: str | None = None,
    decision: str | None = None,
    decision_reason: str | None = None,
    operator: str | None = None,
    next_worker: str | None = None,
    next_worker_objective: str | None = None,
) -> dict[str, Any]:
    manifest, manifest_path = _resolve_manifest(run_dir)

    artifacts = manifest["artifacts"]
    output_contract_path = Path(_require_nonempty(artifacts.get("output_contract"), field="artifacts.output_contract"))
    model_prompt_packet_path = Path(
        _require_nonempty(artifacts.get("model_prompt_packet"), field="artifacts.model_prompt_packet")
    )
    output_contract = _read_json(output_contract_path, kind="output contract")
    authorized_targets, authoritative_held_targets = _load_structured_authority_targets(run_dir, manifest)
    projected_source_paths: list[str] | None = None
    evidence_projection_artifact = artifacts.get("evidence_projection")
    if isinstance(evidence_projection_artifact, str) and evidence_projection_artifact.strip():
        evidence_projection_path = _resolve_run_file(run_dir, evidence_projection_artifact, field="artifacts.evidence_projection")
        evidence_projection_payload = _read_json(evidence_projection_path, kind="evidence projection")
        if isinstance(evidence_projection_payload.get("evidence_sources"), list):
            projected_source_paths = [
                source.get("path")
                for source in evidence_projection_payload["evidence_sources"]
                if isinstance(source, dict) and isinstance(source.get("path"), str)
            ]

    if not raw_output_file.is_file():
        raise ValueError(f"--raw-output-file does not exist: {raw_output_file}")
    raw_output_text = raw_output_file.read_text(encoding="utf-8")

    model_call_metadata: dict[str, Any] | None = None
    if model_call_metadata_file is not None:
        if not model_call_metadata_file.is_file():
            raise ValueError(f"--model-call-metadata-file does not exist: {model_call_metadata_file}")
        model_call_metadata = _read_json(model_call_metadata_file, kind="model call metadata")
        if model_call_metadata.get("call_status") != "completed":
            raise ValueError("--model-call-metadata-file must represent a completed acquisition")
        request_provenance = model_call_metadata.get("request_provenance")
        if not isinstance(request_provenance, dict):
            raise ValueError("--model-call-metadata-file must include request_provenance")
        model_identity = model_call_metadata.get("model")
        if not isinstance(model_identity, str) or not model_identity.strip():
            raise ValueError("--model-call-metadata-file must include model")
        metadata_prompt_sha = model_call_metadata.get("prompt_sha256")
        metadata_prompt_length = model_call_metadata.get("prompt_length")
        if metadata_prompt_sha is None:
            raise ValueError("--model-call-metadata-file must include prompt_sha256")
        if metadata_prompt_length is None:
            raise ValueError("--model-call-metadata-file must include prompt_length")
        prompt_path_value = model_call_metadata.get("prompt_path")
        if not isinstance(prompt_path_value, str) or not prompt_path_value.strip():
            raise ValueError("--model-call-metadata-file must include prompt_path")
        expected_prompt_path = run_dir / prompt_path_value
        if not expected_prompt_path.is_file():
            raise ValueError(f"--model-call-metadata-file prompt_path does not resolve in run: {expected_prompt_path}")
        if _sha256_file(expected_prompt_path) != metadata_prompt_sha:
            raise ValueError("--model-call-metadata-file prompt_sha256 does not match run prompt artifact")
        if len(expected_prompt_path.read_text(encoding="utf-8")) != metadata_prompt_length:
            raise ValueError("--model-call-metadata-file prompt_length does not match run prompt artifact")
        if request_provenance.get("resolved_model") not in {None, model_identity}:
            raise ValueError("--model-call-metadata-file resolved_model must match model")
        if request_provenance.get("model") not in {None, model_identity}:
            raise ValueError("--model-call-metadata-file request_provenance.model must match model")
        if request_provenance.get("prompt_path") not in {None, prompt_path_value}:
            raise ValueError("--model-call-metadata-file request_provenance.prompt_path must match prompt_path")
        if request_provenance.get("prompt_sha256") != metadata_prompt_sha:
            raise ValueError("--model-call-metadata-file request_provenance.prompt_sha256 must match prompt_sha256")
        if request_provenance.get("prompt_length") != metadata_prompt_length:
            raise ValueError("--model-call-metadata-file request_provenance.prompt_length must match prompt_length")
        response_provenance = model_call_metadata.get("response_provenance")
        if not isinstance(response_provenance, dict):
            raise ValueError("--model-call-metadata-file must include response_provenance")
        if response_provenance.get("raw_output_sha256") is None:
            raise ValueError("--model-call-metadata-file must include response_provenance.raw_output_sha256")
        if response_provenance.get("raw_output_length") is None:
            raise ValueError("--model-call-metadata-file must include response_provenance.raw_output_length")
        if response_provenance.get("model") not in {None, model_identity}:
            raise ValueError("--model-call-metadata-file response_provenance.model must match model")
        if model_call_metadata.get("raw_output_sha256") is None:
            raise ValueError("--model-call-metadata-file must include raw_output_sha256")
        if model_call_metadata.get("raw_output_length") is None:
            raise ValueError("--model-call-metadata-file must include raw_output_length")
        if model_call_metadata["raw_output_sha256"] != _sha256_text(raw_output_text):
            raise ValueError("--raw-output-file does not match model call metadata raw_output_sha256")
        if model_call_metadata["raw_output_length"] != len(raw_output_text):
            raise ValueError("--raw-output-file length does not match model call metadata raw_output_length")
        if response_provenance.get("raw_output_sha256") != model_call_metadata["raw_output_sha256"]:
            raise ValueError("--model-call-metadata-file response_provenance.raw_output_sha256 must match raw_output_sha256")
        if response_provenance.get("raw_output_length") != model_call_metadata["raw_output_length"]:
            raise ValueError("--model-call-metadata-file response_provenance.raw_output_length must match raw_output_length")
        if response_provenance.get("raw_output_path") not in {None, model_call_metadata.get("raw_output_path")}:
            raise ValueError("--model-call-metadata-file response_provenance.raw_output_path must match raw_output_path")
        structured_output = model_call_metadata.get("structured_output")
        if structured_output is not None:
            if not isinstance(structured_output, dict):
                raise ValueError("--model-call-metadata-file structured_output must be an object when present")
            structured_enabled = structured_output.get("enabled")
            if structured_enabled is True:
                if structured_output.get("mechanism") != "openai_json_schema":
                    raise ValueError("--model-call-metadata-file structured_output.mechanism must be openai_json_schema")
                schema_path_value = structured_output.get("schema_path")
                schema_sha256 = structured_output.get("schema_sha256")
                schema_length = structured_output.get("schema_length")
                if not isinstance(schema_path_value, str) or not schema_path_value.strip():
                    raise ValueError(
                        "--model-call-metadata-file structured_output.schema_path must be a non-empty string"
                    )
                if not isinstance(schema_sha256, str) or not schema_sha256.strip():
                    raise ValueError(
                        "--model-call-metadata-file structured_output.schema_sha256 must be a non-empty string"
                    )
                if not isinstance(schema_length, int):
                    raise ValueError("--model-call-metadata-file structured_output.schema_length must be an integer")
                schema_path = run_dir / schema_path_value
                if not schema_path.is_file():
                    raise ValueError(
                        f"--model-call-metadata-file structured_output.schema_path does not resolve in run: {schema_path}"
                    )
                if _sha256_file(schema_path) != schema_sha256:
                    raise ValueError(
                        "--model-call-metadata-file structured_output.schema_sha256 does not match schema artifact"
                    )
                if len(schema_path.read_bytes()) != schema_length:
                    raise ValueError(
                        "--model-call-metadata-file structured_output.schema_length does not match schema artifact"
                    )
                schema_artifact = _load_json_object_file(schema_path, kind="structured output schema artifact")
                structured_response_format = structured_output.get("response_format")
                request_response_format = request_provenance.get("response_format")
                if structured_response_format != request_response_format:
                    raise ValueError(
                        "--model-call-metadata-file structured_output.response_format must match request_provenance.response_format"
                    )
                if not isinstance(structured_response_format, dict):
                    raise ValueError("--model-call-metadata-file structured_output.response_format must be an object")
                if structured_response_format.get("type") != "json_schema":
                    raise ValueError("--model-call-metadata-file structured_output.response_format.type must be json_schema")
                structured_json_schema = structured_response_format.get("json_schema")
                if not isinstance(structured_json_schema, dict):
                    raise ValueError(
                        "--model-call-metadata-file structured_output.response_format.json_schema must be an object"
                    )
                if structured_json_schema.get("schema") != schema_artifact:
                    raise ValueError(
                        "--model-call-metadata-file structured_output.response_format.json_schema.schema must match response_schema.json"
                    )
                if request_response_format is None:
                    raise ValueError("--model-call-metadata-file request_provenance.response_format must be present")
                if request_response_format != structured_response_format:
                    raise ValueError(
                        "--model-call-metadata-file request_provenance.response_format must match structured_output.response_format"
                    )
                if request_provenance.get("structured_output_enabled") is not True:
                    raise ValueError(
                        "--model-call-metadata-file request_provenance.structured_output_enabled must be true"
                    )
                if request_provenance.get("structured_output_mechanism") != "openai_json_schema":
                    raise ValueError(
                        "--model-call-metadata-file request_provenance.structured_output_mechanism must be openai_json_schema"
                    )
                request_body_sha256 = model_call_metadata.get("request_body_sha256")
                request_body_length = model_call_metadata.get("request_body_length")
                request_request_body_sha256 = request_provenance.get("request_body_sha256")
                request_request_body_length = request_provenance.get("request_body_length")
                if request_body_sha256 is not None or request_request_body_sha256 is not None:
                    if request_body_sha256 != request_request_body_sha256:
                        raise ValueError(
                            "--model-call-metadata-file request_body_sha256 must match request_provenance.request_body_sha256"
                        )
                if request_body_length is not None or request_request_body_length is not None:
                    if request_body_length != request_request_body_length:
                        raise ValueError(
                            "--model-call-metadata-file request_body_length must match request_provenance.request_body_length"
                        )
            elif structured_enabled is not False:
                raise ValueError("--model-call-metadata-file structured_output.enabled must be boolean when present")

    run_raw_output_path = run_dir / "raw_model_output.txt"
    run_raw_output_path.write_text(raw_output_text, encoding="utf-8")

    ts = _utc_timestamp().lower()
    if model_call_metadata is None:
        attempt_record = build_supervised_model_attempt_record(
            attempt_id=f"manual_attempt_{ts}",
            orchestration_id=_require_nonempty(manifest.get("orchestration_id"), field="orchestration_id"),
            triage_id=_require_nonempty(manifest.get("triage_id"), field="triage_id"),
            prompt_packet_id=_require_nonempty(manifest.get("prompt_packet_id"), field="prompt_packet_id"),
            source_prompt_packet_path=str(model_prompt_packet_path),
            raw_model_output=raw_output_text,
            model_metadata={
                "model_id": "manual_operator_provided_model_output",
                "provider": "manual_operator",
            },
            operator_metadata={
                "operator": operator.strip() if isinstance(operator, str) and operator.strip() else "manual",
                "review_required": True,
            },
            transport_qualification_ref=transport_qualification_ref,
            provenance={
                "source": "manual_operator_pasted_model_output",
                "input_artifact": "model_prompt_packet",
                "raw_output_preserved": True,
                "run_manifest_path": str(manifest_path),
                "raw_output_source_path": str(raw_output_file),
            },
        )
    else:
        attempt_record = build_supervised_model_attempt_record(
            attempt_id=f"model_attempt_{ts}",
            orchestration_id=_require_nonempty(manifest.get("orchestration_id"), field="orchestration_id"),
            triage_id=_require_nonempty(manifest.get("triage_id"), field="triage_id"),
            prompt_packet_id=_require_nonempty(manifest.get("prompt_packet_id"), field="prompt_packet_id"),
            source_prompt_packet_path=str(model_prompt_packet_path),
            raw_model_output=raw_output_text,
            model_metadata={
                "model_id": model_call_metadata["model"],
                "provider": "local_model_call",
                "request_url": model_call_metadata.get("request_url"),
            },
            operator_metadata={
                "operator": operator.strip() if isinstance(operator, str) and operator.strip() else "manual",
                "review_required": True,
            },
            provenance={
                "source": "captured_model_output",
                "input_artifact": "model_prompt_packet",
                "raw_output_preserved": True,
                "run_manifest_path": str(manifest_path),
                "raw_output_source_path": str(raw_output_file),
                "raw_output_sha256": model_call_metadata["raw_output_sha256"],
                "raw_output_length": model_call_metadata["raw_output_length"],
                "model_call_metadata_path": str(model_call_metadata_file),
                "model_call_metadata_sha256": _sha256_file(model_call_metadata_file),
                "model_call_metadata": model_call_metadata,
                "acquisition_request_provenance": model_call_metadata.get("request_provenance"),
                "structured_output": model_call_metadata.get("structured_output"),
                "transport_qualification_ref": transport_qualification_ref,
            },
        )

    validation_record = validate_supervised_attempt_output_against_contract(
        attempt_record=attempt_record,
        output_contract=output_contract,
        validation_id=f"manual_validation_{ts}",
        validated_at=_utc_iso(),
        authorized_targets=authorized_targets,
        authoritative_held_targets=authoritative_held_targets,
        projected_source_paths=projected_source_paths,
    )

    attempt_path = run_dir / "supervised_model_attempt.json"
    validation_path = run_dir / "output_validation.json"
    validation_report_path = run_dir / "output_validation_report.txt"

    _write_json(attempt_path, attempt_record)
    _write_json(validation_path, validation_record)
    validation_report_path.write_text(render_supervised_attempt_output_validation(validation_record), encoding="utf-8")

    result: dict[str, Any] = {
        "run_dir": run_dir,
        "attempt_path": attempt_path,
        "validation_path": validation_path,
        "validation_report_path": validation_report_path,
        "validation_status": validation_record["validation_status"],
        "review_required": decision is None,
    }

    if decision is None:
        return result

    if decision not in ALLOWED_DECISIONS:
        allowed = ", ".join(sorted(ALLOWED_DECISIONS))
        raise ValueError(f"--decision must be one of: {allowed}")

    resolved_reason = _require_nonempty(decision_reason, field="--decision-reason")
    resolved_operator = operator.strip() if isinstance(operator, str) and operator.strip() else "manual"

    review_decision = build_supervised_review_decision_record(
        decision_id=f"manual_decision_{ts}",
        attempt_record=attempt_record,
        validation_record=validation_record,
        decision=decision,
        decision_reason=resolved_reason,
        decided_at=_utc_iso(),
        reviewer_metadata={
            "reviewer": resolved_operator,
            "review_required": True,
        },
    )

    gate_record = build_supervised_downstream_use_gate_record(
        gate_id=f"manual_gate_{ts}",
        decision_record=review_decision,
        requested_downstream_use="next_supervised_step_input",
        operator_metadata={
            "operator": resolved_operator,
            "review_required": True,
        },
        gate_reason="Downstream use remains bounded to supervised next-step input handling.",
        gated_at=_utc_iso(),
    )

    handoff_packet = build_supervised_handoff_packet(
        handoff_id=f"manual_handoff_{ts}",
        gate_record=gate_record,
        next_step_type="next_supervised_step_input",
        next_step_summary="Use reviewed output as bounded input for the next supervised step.",
        next_step_objective=next_worker_objective,
        handoff_payload={
            "payload_kind": "reviewed_model_output_reference",
            "raw_output_artifact": str(run_raw_output_path),
        },
        operator_metadata={
            "operator": resolved_operator,
            "review_required": True,
        },
        handoff_reason="Handoff remains supervised and bounded by downstream-use gate status.",
    )

    decision_path = run_dir / "review_decision.json"
    gate_path = run_dir / "downstream_use_gate.json"
    handoff_path = run_dir / "handoff_packet.json"

    _write_json(decision_path, review_decision)
    _write_json(gate_path, gate_record)
    _write_json(handoff_path, handoff_packet)

    result.update(
        {
            "review_required": False,
            "decision": decision,
            "decision_path": decision_path,
            "gate_path": gate_path,
            "handoff_path": handoff_path,
        }
    )
    if decision == "accepted":
        transaction_result = build_transaction_handoff_artifacts(
            run_dir=run_dir,
            next_worker_identity=next_worker,
        )
        result.update(transaction_result)
        if next_worker_objective is not None:
            continuation_result = build_next_worker_continuation_context(
                transaction_manifest=transaction_result["transaction_manifest"],
                next_worker_context=transaction_result["next_worker_context"],
                output_dir=run_dir,
            )
            result.update(
                {
                    "next_worker_continuation_path": continuation_result["continuation_path"],
                    "next_worker_continuation": continuation_result,
                }
            )
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="mode", required=True)

    prepare = subparsers.add_parser("prepare")
    prepare.add_argument("--messy-input")
    prepare.add_argument("--messy-input-file", type=Path)
    prepare.add_argument("--out-dir", type=Path, required=True)
    prepare.add_argument("--timestamp")
    prepare.add_argument("--overwrite", action="store_true")
    prepare.add_argument(
        "--include-prompt-patch",
        action="append",
        default=[],
        help="Prompt patch IDs to add to the projected prompt_to_paste.md.",
    )
    prepare.add_argument(
        "--exclude-prompt-patch",
        action="append",
        default=[],
        help="Prompt patch IDs to exclude from prompt_to_paste.md projection.",
    )
    prepare.add_argument(
        "--evidence-file",
        action="append",
        type=Path,
        default=[],
        help="Repository evidence file to project into a bounded observation packet.",
    )
    prepare.add_argument(
        "--evidence-task-title",
        help="Task title for evidence-projection mode.",
    )
    prepare.add_argument(
        "--evidence-task-summary",
        help="Task summary for evidence-projection mode.",
    )
    prepare.add_argument(
        "--evidence-max-chars",
        type=int,
        default=12000,
        help="Maximum characters per projected evidence source.",
    )
    prepare.add_argument(
        "--evidence-total-budget-tokens",
        type=int,
        default=8192,
        help="Maximum total token budget for evidence-mode prompts.",
    )
    prepare.add_argument(
        "--evidence-response-reserve-tokens",
        type=int,
        default=900,
        help="Reserved completion tokens for evidence-mode prompts.",
    )
    prepare.add_argument(
        "--evidence-overhead-tokens",
        type=int,
        default=512,
        help="Reserved prompt overhead tokens for evidence-mode prompts.",
    )
    prepare.add_argument("--response-schema-file", type=Path)

    session = subparsers.add_parser("session")
    session.add_argument("--messy-input")
    session.add_argument("--messy-input-file", type=Path)
    session.add_argument("--out-dir", type=Path, required=True)
    session.add_argument("--timestamp")
    session.add_argument("--overwrite", action="store_true")
    session.add_argument("--print-prompt", action="store_true")
    session.add_argument("--write-prompt-copy", action="store_true")
    session.add_argument(
        "--include-prompt-patch",
        action="append",
        default=[],
        help="Prompt patch IDs to add to the projected prompt_to_paste.md.",
    )
    session.add_argument(
        "--exclude-prompt-patch",
        action="append",
        default=[],
        help="Prompt patch IDs to exclude from prompt_to_paste.md projection.",
    )
    session.add_argument(
        "--evidence-file",
        action="append",
        type=Path,
        default=[],
        help="Repository evidence file to project into a bounded observation packet.",
    )
    session.add_argument(
        "--evidence-task-title",
        help="Task title for evidence-projection mode.",
    )
    session.add_argument(
        "--evidence-task-summary",
        help="Task summary for evidence-projection mode.",
    )
    session.add_argument(
        "--evidence-max-chars",
        type=int,
        default=12000,
        help="Maximum characters per projected evidence source.",
    )
    session.add_argument(
        "--evidence-total-budget-tokens",
        type=int,
        default=8192,
        help="Maximum total token budget for evidence-mode prompts.",
    )
    session.add_argument(
        "--evidence-response-reserve-tokens",
        type=int,
        default=900,
        help="Reserved completion tokens for evidence-mode prompts.",
    )
    session.add_argument(
        "--evidence-overhead-tokens",
        type=int,
        default=512,
        help="Reserved prompt overhead tokens for evidence-mode prompts.",
    )
    session.add_argument("--response-schema-file", type=Path)

    call_local = subparsers.add_parser("call-local")
    call_local.add_argument("--run-dir", type=Path, required=True)
    call_local.add_argument("--endpoint", required=True)
    call_local.add_argument("--model", required=True)
    call_local.add_argument("--temperature", type=float, default=0)
    call_local.add_argument("--max-tokens", type=int, default=1024)
    call_local.add_argument("--timeout-seconds", type=float, default=30)
    call_local.add_argument("--response-schema-file", type=Path)
    call_local.add_argument("--overwrite", action="store_true")

    retry_contract = subparsers.add_parser("retry-contract")
    retry_contract.add_argument("--run-dir", type=Path, required=True)
    retry_contract.add_argument("--retry-id", type=int, required=True)

    export_pattern = subparsers.add_parser("export-pattern")
    export_pattern.add_argument("--run-dir", type=Path, required=True)
    export_pattern.add_argument("--failure-raw", type=Path, required=True)
    export_pattern.add_argument("--failure-validation", type=Path, required=True)
    export_pattern.add_argument("--retry-prompt", type=Path, required=True)
    export_pattern.add_argument("--success-raw", type=Path, required=True)
    export_pattern.add_argument("--success-validation", type=Path, required=True)
    export_pattern.add_argument("--out-dir", type=Path, required=True)
    export_pattern.add_argument("--pattern-id", required=True)
    export_pattern.add_argument("--overwrite", action="store_true")

    ingest = subparsers.add_parser("ingest")
    ingest.add_argument("--run-dir", type=Path, required=True)
    ingest.add_argument("--raw-output-file", type=Path, required=True)
    ingest.add_argument("--model-call-metadata-file", type=Path)
    ingest.add_argument("--transport-qualification-ref")
    ingest.add_argument("--decision", choices=sorted(ALLOWED_DECISIONS))
    ingest.add_argument("--decision-reason")
    ingest.add_argument("--operator")
    ingest.add_argument("--next-worker")
    ingest.add_argument("--next-worker-objective")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        if args.mode == "prepare":
            messy_input = _read_messy_input(
                messy_input=args.messy_input,
                messy_input_file=args.messy_input_file,
            )
            result = run_prepare(
                messy_input=messy_input,
                out_dir=args.out_dir,
                timestamp=args.timestamp,
                overwrite=bool(args.overwrite),
                include_prompt_patches=args.include_prompt_patch,
                exclude_prompt_patches=args.exclude_prompt_patch,
                evidence_files=args.evidence_file or None,
                evidence_task_title=args.evidence_task_title,
                evidence_task_summary=args.evidence_task_summary,
                evidence_max_chars=args.evidence_max_chars,
                evidence_total_budget_tokens=args.evidence_total_budget_tokens,
                evidence_response_reserve_tokens=args.evidence_response_reserve_tokens,
                evidence_overhead_tokens=args.evidence_overhead_tokens,
                response_schema_file=args.response_schema_file,
            )
            print(f"run_dir: {result['run_dir']}")
            print(f"model_prompt_packet_path: {result['model_prompt_packet_path']}")
            print(f"manifest_path: {result['manifest_path']}")
            return 0

        if args.mode == "session":
            messy_input = _read_messy_input(
                messy_input=args.messy_input,
                messy_input_file=args.messy_input_file,
            )
            result = run_session(
                messy_input=messy_input,
                out_dir=args.out_dir,
                timestamp=args.timestamp,
                overwrite=bool(args.overwrite),
                write_prompt_copy=bool(args.write_prompt_copy),
                include_prompt_patches=args.include_prompt_patch,
                exclude_prompt_patches=args.exclude_prompt_patch,
                evidence_files=args.evidence_file or None,
                evidence_task_title=args.evidence_task_title,
                evidence_task_summary=args.evidence_task_summary,
                evidence_max_chars=args.evidence_max_chars,
                evidence_total_budget_tokens=args.evidence_total_budget_tokens,
                evidence_response_reserve_tokens=args.evidence_response_reserve_tokens,
                evidence_overhead_tokens=args.evidence_overhead_tokens,
                response_schema_file=args.response_schema_file,
            )
            print(f"run_dir: {result['run_dir']}")
            print(f"model_prompt_packet_path: {result['model_prompt_packet_path']}")
            print(f"prompt_to_paste: {result['prompt_to_paste_path']}")
            print(f"raw_output_file: {result['raw_output_file_path']}")
            print("")
            print("Next:")
            print("1. Paste prompt_to_paste.md into your model manually.")
            print("2. Save the exact model response to raw_model_output.txt.")
            print("3. Run:")
            print("")
            print(result["ingest_command"])
            print("")
            print("Do not paste operator instructions into the model.")
            if not result["write_prompt_copy"]:
                print("Tip: --write-prompt-copy is accepted for compatibility but prompt_to_paste.md is always written.")
            if args.print_prompt:
                prompt_text = Path(result["prompt_to_paste_path"]).read_text(encoding="utf-8")
                print("----- BEGIN MODEL PROMPT PACKET -----")
                print(prompt_text.rstrip())
                print("----- END MODEL PROMPT PACKET -----")
            return 0

        if args.mode == "call-local":
            result = run_call_local(
                run_dir=args.run_dir,
                endpoint=args.endpoint,
                model=args.model,
                temperature=args.temperature,
                max_tokens=args.max_tokens,
                timeout_seconds=args.timeout_seconds,
                overwrite=bool(args.overwrite),
                response_schema_file=args.response_schema_file,
            )
            print(f"run_dir: {result['run_dir']}")
            print(f"endpoint: {result['endpoint']}")
            print(f"model: {result['model']}")
            print(f"raw_output_file: {result['raw_output_path']}")
            print(f"local_model_call_path: {result['local_model_call_path']}")
            print("next_ingest_command:")
            print(result["ingest_command"])
            return 0

        if args.mode == "retry-contract":
            result = _run_retry_contract(run_dir=args.run_dir, retry_id=args.retry_id)
            print(f"run_dir: {result['run_dir']}")
            print(f"retry_id: {result['retry_id']}")
            print(f"retry_prompt_path: {result['retry_prompt_path']}")
            print(f"prompt_path: {result['prompt_path']}")
            print(f"failure_raw_path: {result['failure_raw_path']}")
            print(f"failure_validation_path: {result['failure_validation_path']}")
            print(f"failure_report_path: {result['failure_report_path']}")
            return 0

        if args.mode == "export-pattern":
            result = run_export_pattern(
                run_dir=args.run_dir,
                failure_raw=args.failure_raw,
                failure_validation=args.failure_validation,
                retry_prompt=args.retry_prompt,
                success_raw=args.success_raw,
                success_validation=args.success_validation,
                out_dir=args.out_dir,
                pattern_id=args.pattern_id,
                overwrite=bool(args.overwrite),
            )
            print(f"run_dir: {result['run_dir']}")
            print(f"pattern_id: {result['pattern_id']}")
            print(f"pattern_path: {result['pattern_path']}")
            return 0

        if args.decision is not None and not (isinstance(args.decision_reason, str) and args.decision_reason.strip()):
            raise ValueError("--decision-reason is required when --decision is provided")

        result = run_ingest(
            run_dir=args.run_dir,
            raw_output_file=args.raw_output_file,
            model_call_metadata_file=args.model_call_metadata_file,
            transport_qualification_ref=args.transport_qualification_ref,
            decision=args.decision,
            decision_reason=args.decision_reason,
            operator=args.operator,
            next_worker=args.next_worker,
            next_worker_objective=args.next_worker_objective,
        )
        print(f"run_dir: {result['run_dir']}")
        print(f"attempt_path: {result['attempt_path']}")
        print(f"validation_path: {result['validation_path']}")
        print(f"validation_report_path: {result['validation_report_path']}")
        print(f"validation_status: {result['validation_status']}")

        if result["review_required"]:
            print("review_required: explicit review decision is required before downstream use")
            return 0

        print(f"decision: {result['decision']}")
        print(f"decision_path: {result['decision_path']}")
        print(f"gate_path: {result['gate_path']}")
        print(f"handoff_path: {result['handoff_path']}")
        if "transaction_manifest_path" in result:
            print(f"transaction_manifest_path: {result['transaction_manifest_path']}")
            print(f"next_worker_context_path: {result['next_worker_context_path']}")
        if "next_worker_continuation_path" in result:
            print(f"next_worker_continuation_path: {result['next_worker_continuation_path']}")
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
