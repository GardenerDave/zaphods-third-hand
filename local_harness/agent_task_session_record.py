#!/usr/bin/env python3
"""Model-free execution-evidence and review-decision records for Agent Task Sessions.

This module records what a supervised executor observed (execution evidence)
and what a human reviewer decided (review decision) against an existing,
already-validated Agent Task Session packet.

Boundaries:

- the source packet (task.yaml and every builder-generated file) is never
  mutated; records are separate derived evidence files;
- recorded evidence is not authority and grants no merge, release, promotion,
  cleanup, deletion, or lifecycle authority;
- review decisions are human-supplied records, not tool decisions;
- this module executes no checks, agents, shell commands, or Git operations.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from local_harness.agent_task_session import (
    CONTRACT_VERSION,
    REPO_ROOT,
    SessionValidationError,
    validate_task_session,
)


EXECUTION_RECORD_SCHEMA = "zth.agent_task_session_execution_record.v0.1"
REVIEW_RECORD_SCHEMA = "zth.agent_task_session_review_record.v0.1"
REVIEW_DECISIONS = ("accepted", "rejected", "revision_requested")
EXECUTION_DIR = "execution"
REVIEW_DIR = "review"
STAGE_DRAFT = "draft"
STAGE_EXECUTED = "executed"
STAGE_REVIEWED = "reviewed"
MODULE_NAME = "local_harness/agent_task_session_record.py"
EXECUTION_ID_RE = re.compile(r"^execution_\d{8}t\d{6}z(?:-\d{6})?$")
REVIEW_ID_RE = re.compile(r"^review_\d{8}t\d{6}z(?:-\d{6})?$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
RECORD_BOUNDARIES = (
    "Recorded execution evidence is not authority.",
    "Recorded review decisions are human-supplied records, not tool decisions.",
    "The source Agent Task Session packet is never mutated by these records.",
    "These records grant no merge, release, promotion, cleanup, deletion, or lifecycle authority.",
    "This module executes no checks, agents, shell commands, or Git operations.",
)


class SessionRecordError(ValueError):
    """Raised when session record construction or validation fails closed."""


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _next_record_id(directory: Path, prefix: str) -> str:
    """Return a collision-free record id for ``directory``.

    Ids are second-resolution stamps; a same-second collision appends a
    zero-padded ``-NNNNNN`` suffix, which keeps lexicographic id order equal
    to chronological order.
    """
    now = datetime.now(timezone.utc)
    base = f"{prefix}_{now:%Y%m%d}t{now:%H%M%S}z"
    if not (directory / f"{base}.json").exists():
        return base
    for counter in range(1, 1000000):
        candidate = f"{base}-{counter:06d}"
        if not (directory / f"{candidate}.json").exists():
            return candidate
    raise SessionRecordError(f"record id space exhausted for {directory}")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _require_nonempty(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SessionRecordError(f"{field} must be a non-empty string")
    return value


def _clean_text(value: str, *, field: str) -> str:
    cleaned = " ".join(value.split())
    if not cleaned:
        raise SessionRecordError(f"{field} must not be empty")
    return cleaned


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_json(path: Path, *, kind: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SessionRecordError(f"missing {kind}: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SessionRecordError(f"invalid JSON in {kind}: {path}") from exc
    if not isinstance(payload, dict):
        raise SessionRecordError(f"{kind} must be a JSON object: {path}")
    return payload


def _base_session(session_dir: Path):
    try:
        return validate_task_session(session_dir)
    except SessionValidationError as exc:
        raise SessionRecordError(f"base task session is invalid: {exc}") from exc


def _repo_relative(path: Path) -> str | None:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return None


def _resolve_evidence_file(value: str) -> Path:
    if not value or not value.strip():
        raise SessionRecordError("evidence file paths must not be empty")
    if "\x00" in value:
        raise SessionRecordError("evidence file paths must not contain NUL bytes")
    path = Path(value)
    if not path.is_file():
        raise SessionRecordError(f"evidence file does not exist or is not a file: {value}")
    return path.resolve()


def _execution_dir(session_dir: Path) -> Path:
    return session_dir / EXECUTION_DIR


def _review_dir(session_dir: Path) -> Path:
    return session_dir / REVIEW_DIR


def _record_files(directory: Path, *, id_prefix: str, kind: str) -> list[Path]:
    if not directory.exists():
        return []
    if not directory.is_dir():
        raise SessionRecordError(f"{kind} directory is not a directory: {directory}")
    expected_prefix = f"{id_prefix}_"
    files: list[Path] = []
    for entry in sorted(directory.iterdir()):
        if not entry.is_file():
            raise SessionRecordError(f"unexpected non-file entry in {kind} directory: {entry}")
        stem = entry.stem
        if not stem.startswith(expected_prefix) or entry.suffix != ".json":
            raise SessionRecordError(
                f"unexpected file in {kind} directory (expected {expected_prefix}*.json): {entry}"
            )
        files.append(entry)
    return files

def record_execution(
    *,
    session_dir: Path,
    outcomes: Sequence[str],
    evidence_files: Sequence[str] = (),
    note: str | None = None,
) -> dict[str, Any]:
    """Record one execution-evidence entry against a validated task session."""
    base = _base_session(session_dir)
    checks = base.required_checks
    if len(outcomes) != len(checks):
        raise SessionRecordError(
            "supply exactly one outcome per required check, in packet order "
            f"({len(checks)} checks recorded, {len(outcomes)} outcomes given)"
        )
    check_entries = [
        {"command": command, "outcome": _clean_text(outcome, field="check outcome")}
        for command, outcome in zip(checks, outcomes)
    ]
    evidence_entries: list[dict[str, Any]] = []
    for value in evidence_files:
        path = _resolve_evidence_file(value)
        data = path.read_bytes()
        evidence_entries.append(
            {
                "path": str(path),
                "repo_relative": _repo_relative(path),
                "sha256": _sha256_bytes(data),
                "bytes": len(data),
            }
        )
    resolved_note = _clean_text(note, field="note") if note is not None else None
    output_dir = _execution_dir(session_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    execution_id = _next_record_id(output_dir, "execution")
    payload: dict[str, Any] = {
        "schema_version": EXECUTION_RECORD_SCHEMA,
        "task_id": base.task_id,
        "execution_id": execution_id,
        "recorded_at": _utc_iso(),
        "checks": check_entries,
        "evidence_files": evidence_entries,
        "note": resolved_note,
        "authority_boundaries": list(RECORD_BOUNDARIES),
        "provenance": {
            "module": MODULE_NAME,
            "session_dir": str(session_dir),
            "task_session_contract_version": CONTRACT_VERSION,
            "task_yaml_sha256": _sha256_file(session_dir / "task.yaml"),
            "base_packet_validated": True,
        },
    }
    record_path = output_dir / f"{execution_id}.json"
    if record_path.exists():
        raise SessionRecordError(f"execution record already exists: {record_path}")
    _write_json(record_path, payload)
    payload["execution_record_path"] = str(record_path)
    return payload


def _validated_execution_records(
    session_dir: Path,
    *,
    base,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for record_path in _record_files(
        _execution_dir(session_dir), id_prefix="execution", kind="execution record"
    ):
        payload = _read_json(record_path, kind="execution record")
        _validate_execution_record(
            payload,
            record_path=record_path,
            base=base,
        )
        payload["execution_record_path"] = str(record_path)
        records.append(payload)
    records.sort(key=lambda record: record["execution_id"])
    return records


def _validate_execution_record(payload: dict[str, Any], *, record_path: Path, base) -> None:
    if payload.get("schema_version") != EXECUTION_RECORD_SCHEMA:
        raise SessionRecordError(f"unsupported execution record schema: {record_path}")
    if payload.get("task_id") != base.task_id:
        raise SessionRecordError(f"execution record task_id mismatch: {record_path}")
    execution_id = payload.get("execution_id")
    if not isinstance(execution_id, str) or not EXECUTION_ID_RE.fullmatch(execution_id):
        raise SessionRecordError(f"malformed execution id: {record_path}")
    if execution_id != record_path.stem:
        raise SessionRecordError(
            f"execution record file name must match its execution id: {record_path}"
        )
    _require_nonempty(payload.get("recorded_at"), field=f"recorded_at in {record_path}")
    checks = payload.get("checks")
    if not isinstance(checks, list) or len(checks) != len(base.required_checks):
        raise SessionRecordError(
            f"execution record must carry one check entry per packet required check: {record_path}"
        )
    for entry, command in zip(checks, base.required_checks):
        if not isinstance(entry, dict) or entry.get("command") != command:
            raise SessionRecordError(
                f"execution record checks must match packet required checks in order: {record_path}"
            )
        _require_nonempty(entry.get("outcome"), field=f"check outcome in {record_path}")
    evidence_files = payload.get("evidence_files")
    if not isinstance(evidence_files, list):
        raise SessionRecordError(f"evidence_files must be a list: {record_path}")
    for entry in evidence_files:
        if not isinstance(entry, dict):
            raise SessionRecordError(f"evidence file entry must be an object: {record_path}")
        path_value = _require_nonempty(entry.get("path"), field=f"evidence path in {record_path}")
        sha_value = entry.get("sha256")
        if not isinstance(sha_value, str) or not SHA256_RE.fullmatch(sha_value):
            raise SessionRecordError(f"evidence sha256 must be 64 hex chars: {record_path}")
        size_value = entry.get("bytes")
        if not isinstance(size_value, int) or isinstance(size_value, bool) or size_value < 0:
            raise SessionRecordError(f"evidence bytes must be a non-negative integer: {record_path}")
        path = Path(path_value)
        if not path.is_file():
            raise SessionRecordError(
                f"recorded evidence file no longer exists: {path_value} ({record_path})"
            )
        data = path.read_bytes()
        if _sha256_bytes(data) != sha_value or len(data) != size_value:
            raise SessionRecordError(
                f"recorded evidence file drifted from its recorded hash: {path_value} ({record_path})"
            )
    note = payload.get("note")
    if note is not None and not isinstance(note, str):
        raise SessionRecordError(f"note must be a string or null: {record_path}")
    if payload.get("authority_boundaries") != list(RECORD_BOUNDARIES):
        raise SessionRecordError(f"execution record authority boundaries mismatch: {record_path}")
    provenance = payload.get("provenance")
    if not isinstance(provenance, dict):
        raise SessionRecordError(f"execution record provenance must be an object: {record_path}")
    if provenance.get("module") != MODULE_NAME:
        raise SessionRecordError(f"execution record provenance module mismatch: {record_path}")
    if provenance.get("task_session_contract_version") != CONTRACT_VERSION:
        raise SessionRecordError(f"execution record contract version mismatch: {record_path}")
    _require_nonempty(provenance.get("session_dir"), field=f"provenance session_dir in {record_path}")
    expected_task_yaml = _sha256_file(record_path.parents[1] / "task.yaml")
    if provenance.get("task_yaml_sha256") != expected_task_yaml:
        raise SessionRecordError(
            f"task.yaml drifted from the hash recorded at execution time: {record_path}"
        )

def record_review(
    *,
    session_dir: Path,
    decision: str,
    reviewer: str,
    reason: str,
    execution_id: str | None = None,
    supersedes: str | None = None,
) -> dict[str, Any]:
    """Record one human-supplied review decision against recorded execution evidence."""
    if decision not in REVIEW_DECISIONS:
        raise SessionRecordError(
            f"decision must be one of: {', '.join(REVIEW_DECISIONS)}"
        )
    base = _base_session(session_dir)
    executions = _validated_execution_records(session_dir, base=base)
    if not executions:
        raise SessionRecordError(
            "cannot record a review before execution evidence exists; record execution first"
        )
    if execution_id is None:
        bound_execution = executions[-1]
        execution_binding = "latest"
    else:
        matching = [record for record in executions if record["execution_id"] == execution_id]
        if not matching:
            raise SessionRecordError(
                f"execution id not found in session records: {execution_id}"
            )
        bound_execution = matching[0]
        execution_binding = "explicit"
    reviews = _validated_review_records(session_dir, task_id=base.task_id, executions=executions)
    if reviews:
        latest = reviews[-1]["review_id"]
        if supersedes is None:
            raise SessionRecordError(
                f"a review decision already exists ({latest}); pass supersedes='{latest}' to record a superseding decision"
            )
        if supersedes != latest:
            raise SessionRecordError(
                f"a new review must supersede the latest review decision ({latest}), not {supersedes}"
            )
    elif supersedes is not None:
        raise SessionRecordError(
            f"no existing review decision to supersede: {supersedes}"
        )
    resolved_reviewer = _clean_text(reviewer, field="reviewer")
    resolved_reason = _clean_text(reason, field="reason")
    output_dir = _review_dir(session_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    review_id = _next_record_id(output_dir, "review")
    execution_path = Path(bound_execution["execution_record_path"])
    payload: dict[str, Any] = {
        "schema_version": REVIEW_RECORD_SCHEMA,
        "task_id": base.task_id,
        "review_id": review_id,
        "execution_id": bound_execution["execution_id"],
        "execution_binding": execution_binding,
        "decision": decision,
        "reviewer": resolved_reviewer,
        "reviewer_identity_boundary": "Reviewer identity is supplied input, not tool-verified identity.",
        "reason": resolved_reason,
        "decided_at": _utc_iso(),
        "supersedes": supersedes,
        "authority_boundaries": list(RECORD_BOUNDARIES),
        "provenance": {
            "module": MODULE_NAME,
            "session_dir": str(session_dir),
            "task_session_contract_version": CONTRACT_VERSION,
            "task_yaml_sha256": _sha256_file(session_dir / "task.yaml"),
            "execution_record_sha256": _sha256_file(execution_path),
        },
    }
    record_path = output_dir / f"{review_id}.json"
    if record_path.exists():
        raise SessionRecordError(f"review record already exists: {record_path}")
    _write_json(record_path, payload)
    payload["review_record_path"] = str(record_path)
    return payload


def _validated_review_records(
    session_dir: Path,
    *,
    task_id: str,
    executions: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    execution_ids = {record["execution_id"] for record in executions}
    execution_by_id = {record["execution_id"]: record for record in executions}
    records: list[dict[str, Any]] = []
    for record_path in _record_files(
        _review_dir(session_dir), id_prefix="review", kind="review record"
    ):
        payload = _read_json(record_path, kind="review record")
        _validate_review_record(
            payload,
            record_path=record_path,
            task_id=task_id,
            execution_ids=execution_ids,
        )
        expected_execution_sha = _sha256_file(
            Path(execution_by_id[payload["execution_id"]]["execution_record_path"])
        )
        if payload["provenance"].get("execution_record_sha256") != expected_execution_sha:
            raise SessionRecordError(
                f"review record execution hash mismatch: {record_path}"
            )
        payload["review_record_path"] = str(record_path)
        records.append(payload)
    records.sort(key=lambda record: record["review_id"])
    for index, record in enumerate(records):
        previous_id = records[index - 1]["review_id"] if index else None
        if record.get("supersedes") != previous_id:
            if index == 0:
                raise SessionRecordError(
                    f"first review record must not supersede anything: {record['review_record_path']}"
                )
            raise SessionRecordError(
                f"review record chain broken: {record['review_id']} supersedes "
                f"{record.get('supersedes')}, expected {previous_id}"
            )
    return records


def _validate_review_record(
    payload: dict[str, Any],
    *,
    record_path: Path,
    task_id: str,
    execution_ids: set[str],
) -> None:
    if payload.get("schema_version") != REVIEW_RECORD_SCHEMA:
        raise SessionRecordError(f"unsupported review record schema: {record_path}")
    if payload.get("task_id") != task_id:
        raise SessionRecordError(f"review record task_id mismatch: {record_path}")
    review_id = payload.get("review_id")
    if not isinstance(review_id, str) or not REVIEW_ID_RE.fullmatch(review_id):
        raise SessionRecordError(f"malformed review id: {record_path}")
    if review_id != record_path.stem:
        raise SessionRecordError(
            f"review record file name must match its review id: {record_path}"
        )
    if payload.get("execution_id") not in execution_ids:
        raise SessionRecordError(f"review record binds an unknown execution id: {record_path}")
    if payload.get("execution_binding") not in {"latest", "explicit"}:
        raise SessionRecordError(f"review record execution_binding is malformed: {record_path}")
    if payload.get("decision") not in REVIEW_DECISIONS:
        raise SessionRecordError(f"review record decision is not allowed: {record_path}")
    _require_nonempty(payload.get("reviewer"), field=f"reviewer in {record_path}")
    _require_nonempty(payload.get("reason"), field=f"reason in {record_path}")
    _require_nonempty(payload.get("decided_at"), field=f"decided_at in {record_path}")
    supersedes = payload.get("supersedes")
    if supersedes is not None and (
        not isinstance(supersedes, str) or not REVIEW_ID_RE.fullmatch(supersedes)
    ):
        raise SessionRecordError(f"review record supersedes value is malformed: {record_path}")
    if payload.get("authority_boundaries") != list(RECORD_BOUNDARIES):
        raise SessionRecordError(f"review record authority boundaries mismatch: {record_path}")
    provenance = payload.get("provenance")
    if not isinstance(provenance, dict):
        raise SessionRecordError(f"review record provenance must be an object: {record_path}")
    if provenance.get("module") != MODULE_NAME:
        raise SessionRecordError(f"review record provenance module mismatch: {record_path}")
    if provenance.get("task_session_contract_version") != CONTRACT_VERSION:
        raise SessionRecordError(f"review record contract version mismatch: {record_path}")
    _require_nonempty(provenance.get("session_dir"), field=f"provenance session_dir in {record_path}")
    expected_task_yaml = _sha256_file(record_path.parents[1] / "task.yaml")
    if provenance.get("task_yaml_sha256") != expected_task_yaml:
        raise SessionRecordError(
            f"task.yaml drifted from the hash recorded at review time: {record_path}"
        )

@dataclass(frozen=True)
class SessionRecordsValidation:
    task_id: str
    session_dir: Path
    stage: str
    execution_count: int
    review_count: int
    effective_review_decision: str | None
    effective_review_id: str | None
    allowed_paths: tuple[str, ...]
    required_checks: tuple[str, ...]
    execution_ids: tuple[str, ...]
    review_ids: tuple[str, ...]


def validate_session_records(session_dir: Path) -> SessionRecordsValidation:
    """Validate a task session plus any recorded execution and review records."""
    base = _base_session(session_dir)
    executions = _validated_execution_records(session_dir, base=base)
    reviews = _validated_review_records(session_dir, task_id=base.task_id, executions=executions)
    if reviews and not executions:
        raise SessionRecordError(
            "review records exist without execution records; recording is fail-closed"
        )
    if executions:
        stage = STAGE_REVIEWED if reviews else STAGE_EXECUTED
    else:
        stage = STAGE_DRAFT
    return SessionRecordsValidation(
        task_id=base.task_id,
        session_dir=session_dir,
        stage=stage,
        execution_count=len(executions),
        review_count=len(reviews),
        effective_review_decision=reviews[-1]["decision"] if reviews else None,
        effective_review_id=reviews[-1]["review_id"] if reviews else None,
        allowed_paths=base.allowed_paths,
        required_checks=base.required_checks,
        execution_ids=tuple(record["execution_id"] for record in executions),
        review_ids=tuple(record["review_id"] for record in reviews),
    )


def validation_json_payload(validation: SessionRecordsValidation) -> dict[str, Any]:
    return {
        "allowed_paths": list(validation.allowed_paths),
        "effective_review_decision": validation.effective_review_decision,
        "effective_review_id": validation.effective_review_id,
        "execution_count": validation.execution_count,
        "execution_ids": list(validation.execution_ids),
        "review_count": validation.review_count,
        "review_ids": list(validation.review_ids),
        "required_checks": list(validation.required_checks),
        "session_dir": str(validation.session_dir),
        "stage": validation.stage,
        "task_id": validation.task_id,
        "valid": True,
        "warnings": [
            "Records and the derived stage are evidence, not authority.",
            "No checks, agents, shell commands, or Git operations were executed.",
            "Human review remains required for any acceptance or follow-up action.",
        ],
    }


def _execution_json_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "execution_id": payload["execution_id"],
        "execution_record_path": payload["execution_record_path"],
        "evidence_file_count": len(payload["evidence_files"]),
        "task_id": payload["task_id"],
        "warnings": list(RECORD_BOUNDARIES),
    }


def _review_json_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": payload["decision"],
        "execution_id": payload["execution_id"],
        "review_id": payload["review_id"],
        "review_record_path": payload["review_record_path"],
        "supersedes": payload["supersedes"],
        "task_id": payload["task_id"],
        "warnings": list(RECORD_BOUNDARIES),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Record execution evidence and human review decisions against an existing "
            "Agent Task Session. Records are evidence, not authority. This command "
            "executes no checks, agents, shell commands, or Git operations."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    execution_parser = subparsers.add_parser(
        "record-execution",
        help="Record one execution-evidence entry against a validated task session.",
    )
    execution_parser.add_argument("session", type=Path, help="Task session directory.")
    execution_parser.add_argument(
        "--outcome",
        action="append",
        required=True,
        help=(
            "Observed outcome for one required check, in packet order; repeat once per "
            "required check. Outcomes are recorded evidence, not verified results."
        ),
    )
    execution_parser.add_argument(
        "--evidence-file",
        action="append",
        default=[],
        help="Existing evidence file to bind (path recorded with sha256); repeat as needed.",
    )
    execution_parser.add_argument(
        "--note",
        help="Optional free-text note recorded with the execution evidence.",
    )
    execution_parser.add_argument(
        "--json",
        action="store_true",
        help="Print a machine-readable recording summary.",
    )

    review_parser = subparsers.add_parser(
        "record-review",
        help="Record one human-supplied review decision against execution evidence.",
    )
    review_parser.add_argument("session", type=Path, help="Task session directory.")
    review_parser.add_argument(
        "--decision",
        required=True,
        choices=REVIEW_DECISIONS,
        help="Human review decision to record.",
    )
    review_parser.add_argument(
        "--reviewer",
        required=True,
        help="Reviewer identity as supplied; not tool-verified.",
    )
    review_parser.add_argument(
        "--reason",
        required=True,
        help="Human-supplied review reason.",
    )
    review_parser.add_argument(
        "--execution-id",
        help="Bind the review to a specific execution record (defaults to the latest).",
    )
    review_parser.add_argument(
        "--supersedes",
        help="Existing review id this decision supersedes (required when a review exists).",
    )
    review_parser.add_argument(
        "--json",
        action="store_true",
        help="Print a machine-readable recording summary.",
    )

    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate the packet plus recorded execution and review records.",
    )
    validate_parser.add_argument("session", type=Path, help="Task session directory.")
    validate_parser.add_argument(
        "--json",
        action="store_true",
        help="Print a machine-readable validation summary.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "validate":
        try:
            validation = validate_session_records(args.session)
        except (SessionRecordError, SessionValidationError) as exc:
            if args.json:
                print(
                    json.dumps(
                        {"error": str(exc), "session": str(args.session), "valid": False},
                        indent=2,
                        sort_keys=True,
                    )
                )
            else:
                print(f"INVALID {args.session}: {exc}", file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps(validation_json_payload(validation), indent=2, sort_keys=True))
            return 0
        review = (
            f"review={validation.effective_review_decision} ({validation.effective_review_id})"
            if validation.effective_review_decision
            else "review=<none>"
        )
        print(
            f"VALID {validation.session_dir}: {validation.task_id} "
            f"stage={validation.stage} executions={validation.execution_count} {review}"
        )
        print("Records and the derived stage are evidence, not authority.")
        print("No checks, agents, shell commands, or Git operations were executed.")
        return 0

    try:
        if args.command == "record-execution":
            payload = record_execution(
                session_dir=args.session,
                outcomes=args.outcome,
                evidence_files=args.evidence_file,
                note=args.note,
            )
            summary = _execution_json_payload(payload)
        else:
            payload = record_review(
                session_dir=args.session,
                decision=args.decision,
                reviewer=args.reviewer,
                reason=args.reason,
                execution_id=args.execution_id,
                supersedes=args.supersedes,
            )
            summary = _review_json_payload(payload)
    except (SessionRecordError, SessionValidationError) as exc:
        if args.json:
            print(json.dumps({"error": str(exc)}, indent=2, sort_keys=True))
        else:
            print(f"agent-task-session-record: error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0
    if args.command == "record-execution":
        print(f"Recorded execution evidence: {payload['execution_record_path']}")
        print("Outcomes are recorded operator/agent input, not tool-verified results.")
    else:
        print(f"Recorded review decision: {payload['review_record_path']}")
        print("The review decision is a human-supplied record, not a tool decision.")
    print("Records are evidence, not authority. The source packet was not mutated.")
    print("No checks, agents, shell commands, or Git operations were executed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
