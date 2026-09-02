#!/usr/bin/env python3
"""Supervised ZTH task front door.

One coherent operator interface that composes the already proven ZTH
mechanisms into a bounded, evidence-backed task workflow:

    objective
      -> two-repository baseline preflight (local_harness/zth_preflight.py)
      -> verbatim objective record + private task workspace
      -> advisory semantic interpretation (one model call, strictly contracted)
      -> Project Historian ask-and-bind (local_harness/historian_context_query.py)
      -> deterministic scope binding into a validated Agent Task Session
         (local_harness/agent_task_session.py)
      -> operator-facing summary, resumable derived status, exact handoff
      -> execution evidence + human review through the existing recorder
         (local_harness/agent_task_session_record.py)

This module does not fork a second task-packet implementation, a second
lifecycle, or a new coding-agent client. Front-door task state is always
derived from durable artifacts, never from a mutable status flag.

Boundaries:
- Task preparation grants no execution authority; a prepared packet is
  review material, not permission to act.
- The semantic interpretation is advisory model output. ZTH binds every
  authority-bearing fact deterministically and rejects authority-bearing or
  unknown model fields instead of ignoring them.
- The Historian answer is advisory interpretation over evidence; the cited
  canonical records remain the evidence.
- A passing preflight is an observation, not authorization; a validated
  packet is not approval; execution evidence is not acceptance; a commit is
  not acceptance.
- This front door executes no required checks, performs no Git operations,
  commits nothing, and grants no merge, release, promotion, cleanup, or
  lifecycle authority. Human review remains a separate, required step.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Sequence

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from local_harness.agent_task_session import (
    CONTRACT_VERSION as TASK_SESSION_CONTRACT_VERSION,
    DEFAULT_SESSION_ROOT,
    REPO_ROOT,
    SessionValidationError,
    clean_check,
    clean_text,
    create_task_session,
    normalize_allowed_path,
    slugify,
    validate_task_id,
    validate_task_session,
)
from local_harness.agent_task_session_record import (
    SessionRecordError,
    validate_session_records,
)
from local_harness.historian_context_query import (
    HistorianAskBindError,
    ask_and_bind_many,
)
from local_harness.zth_preflight import (
    DEFAULT_TIMEOUT_SECONDS as DEFAULT_PREFLIGHT_TIMEOUT_SECONDS,
    STATUS_FAIL,
    STATUS_PASS,
    result_json,
    run_preflight,
)

FRONTDOOR_SCHEMA = "zth.task_frontdoor.v0.1"
OBJECTIVE_SCHEMA = "zth.task_objective.v0.1"
INTERPRETATION_SCHEMA = "zth.task_semantic_interpretation.v0.1"
HISTORIAN_INDEX_SCHEMA = "zth.task_historian_index.v0.1"
SESSION_REF_SCHEMA = "zth.task_session_ref.v0.1"
FAILURE_SCHEMA = "zth.task_failure.v0.1"

MODULE_NAME = "local_harness/zth_task.py"
WORK_ROOT = REPO_ROOT / ".work" / "zth_tasks"
TASK_ID_PREFIX = "zth-task-"
TASK_ID_MAX_LENGTH = 64

OBJECTIVE_FILE = "objective.json"
PREFLIGHT_FILE = "preflight.json"
INTERPRETATION_FILE = "semantic_interpretation.json"
HISTORIAN_DIR_NAME = "historian"
HISTORIAN_INDEX_FILE = "historian/index.json"
SESSION_REF_FILE = "task_session_ref.json"
SUMMARY_FILE = "task_summary.md"
FAILURE_FILE = "failure.json"

STATE_CREATED = "created"
STATE_CONTEXT_BOUND = "context_bound"
STATE_READY_FOR_EXECUTION = "ready_for_execution"
STATE_EXECUTED = "executed"
STATE_REVIEWED = "reviewed"
STATE_BLOCKED = "blocked"

STAGE_PREFLIGHT = "preflight"
STAGE_INTERPRETATION = "interpretation"
STAGE_HISTORIAN = "historian"
STAGE_SCOPE_BINDING = "scope_binding"
STAGE_SESSION_CREATION = "session_creation"
STAGE_SESSION_VALIDATION = "session_validation"

INTERPRETER_ENDPOINT_ENV = "ZTH_TASK_INTERPRETER_ENDPOINT"
INTERPRETER_MODEL_ENV = "ZTH_TASK_INTERPRETER_MODEL"
DEFAULT_INTERPRETER_MAX_TOKENS = 2048
DEFAULT_INTERPRETER_TIMEOUT_SECONDS = 240
DEFAULT_HISTORIAN_TIMEOUT_SECONDS = 600

MAX_HISTORIAN_QUESTIONS = 5
MAX_CANDIDATE_PATHS = 12

INTERPRETATION_KEYS = (
    "goal",
    "candidate_allowed_paths",
    "non_goals",
    "required_checks",
    "historian_questions",
    "reasoning_summary",
    "uncertainties",
)
_AUTHORITY_FIELD_MARKERS = (
    "authority",
    "approv",
    "commit",
    "permission",
    "authoriz",
    "execute",
    "grant",
)

WILDCARD_CHARS = "*?["
PRIVATE_TARGET_ROOTS = {".work", "outputs", "sources"}

FRONTDOOR_BOUNDARIES = (
    "Task preparation grants no execution authority; a prepared packet is review material, not permission to act.",
    "The semantic interpretation is advisory model output; ZTH binds authority-bearing facts deterministically and rejects authority-bearing model fields.",
    "The Historian answer is advisory interpretation over evidence; the cited canonical records remain the evidence.",
    "A passing preflight is an observation, not authorization; a validated packet is not approval; execution evidence is not acceptance; a commit is not acceptance.",
    "This front door executes no required checks, performs no Git operations, commits nothing, and grants no merge, release, promotion, cleanup, or lifecycle authority.",
    "Human review remains a separate, required step for every task this front door prepares.",
)

INTERPRETATION_JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "goal": {"type": "string", "minLength": 1},
        "candidate_allowed_paths": {
            "type": "array",
            "minItems": 1,
            "maxItems": MAX_CANDIDATE_PATHS,
            "items": {"type": "string", "minLength": 1},
        },
        "non_goals": {"type": "array", "items": {"type": "string", "minLength": 1}},
        "required_checks": {
            "type": "array",
            "minItems": 1,
            "items": {"type": "string", "minLength": 1},
        },
        "historian_questions": {
            "type": "array",
            "maxItems": MAX_HISTORIAN_QUESTIONS,
            "items": {"type": "string", "minLength": 1},
        },
        "reasoning_summary": {"type": "string", "minLength": 1},
        "uncertainties": {"type": "array", "items": {"type": "string", "minLength": 1}},
    },
    "required": list(INTERPRETATION_KEYS),
}

ModelCall = Callable[..., str]


class ZthTaskError(ValueError):
    """A fail-closed front-door error."""


def _utc_now_iso(*, microseconds: bool = False) -> str:
    pattern = "%Y-%m-%dT%H:%M:%S.%fZ" if microseconds else "%Y-%m-%dT%H:%M:%SZ"
    return datetime.now(timezone.utc).strftime(pattern)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _read_json_file(path: Path, kind: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ZthTaskError(f"missing {kind} artifact: {_display(path)}") from exc
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ZthTaskError(f"corrupt {kind} artifact: {_display(path)}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ZthTaskError(f"corrupt {kind} artifact: {_display(path)}: not a JSON object")
    return payload


def _display(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _repo_relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def derive_frontdoor_task_id(objective: str, created_at: str) -> str:
    slug = slugify(objective)[:24]
    digest = hashlib.sha256(f"{objective}\n{created_at}".encode("utf-8")).hexdigest()[:8]
    task_id = f"{TASK_ID_PREFIX}{slug}-{digest}" if slug else f"{TASK_ID_PREFIX}{digest}"
    return validate_task_id(task_id)


def resolve_interpreter_endpoint(explicit: str | None) -> tuple[str | None, str | None]:
    if explicit:
        return explicit, "cli"
    value = os.environ.get(INTERPRETER_ENDPOINT_ENV)
    if value:
        return value, "env"
    return None, None


def resolve_interpreter_model(explicit: str | None) -> str | None:
    return explicit or os.environ.get(INTERPRETER_MODEL_ENV)


def interpreter_system_prompt() -> str:
    return (
        "You are the ZTH task interpreter. You turn one operator-supplied "
        "development objective into a bounded, reviewable task proposal. You "
        "are advisory only: you cannot grant execution authority, approve "
        "anything, authorize commits, or expand scope. ZTH will "
        "deterministically validate and bind every authority-bearing fact and "
        "will reject any field outside the required schema.\n"
        "Reply with exactly one JSON object with exactly these keys:\n"
        "- goal: one specific bounded outcome statement;\n"
        "- candidate_allowed_paths: repository-relative paths this task should "
        "be allowed to touch. Only existing files or directories, or new files "
        "under existing directories. No wildcards. Never .git, .work, outputs, "
        "sources, private configuration, or secret material;\n"
        "- non_goals: explicit constraints naming what this task must not do;\n"
        "- required_checks: focused verification commands, runnable from the "
        "repository root, whose observed results can be recorded as evidence;\n"
        "- historian_questions: zero to five discriminating questions for the "
        "Project Historian about decisions, prior attempts, failures to avoid "
        "repeating, or existing coverage that bound this objective. Ask only "
        "questions whose answers would change the task; simple tasks may need "
        "none. The Project Historian can only cite canonical project records, "
        "and answers without citations are refused by binding: ask only "
        "questions whose answers plausibly exist in reviewed or canonical "
        "records, never questions about live tool output, current working-tree "
        "state, or anything the canonical records would not contain;\n"
        "- reasoning_summary: why this scope is the bounded interpretation of "
        "the objective;\n"
        "- uncertainties: what remains uncertain for the human reviewer.\n"
        "Do not add any other field. Do not claim, grant, or imply any "
        "authority, approval, execution permission, or commit permission."
    )


def interpreter_user_prompt(
    *,
    objective: str,
    zth_head: str | None,
    historian_head: str | None,
    preflight_status: str,
) -> str:
    return (
        f"Objective (verbatim, from the operator):\n{objective}\n\n"
        "Observed baseline: "
        f"preflight {preflight_status}; ZTH HEAD {zth_head or 'unknown'}; "
        f"Historian HEAD {historian_head or 'unknown'}.\n\n"
        "Propose the bounded task interpretation now, as exactly one JSON "
        "object."
    )


def call_interpreter_model(
    *,
    endpoint: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
    timeout_seconds: int,
) -> str:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0,
        "top_p": 1,
        "seed": 42,
        "max_tokens": max_tokens,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "zth_task_interpretation",
                "schema": INTERPRETATION_JSON_SCHEMA,
            },
        },
        "stream": False,
    }
    request = urllib.request.Request(
        endpoint.rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            body = response.read()
    except urllib.error.HTTPError as exc:
        tail = ""
        try:
            tail = exc.read()[:400].decode("utf-8", "replace")
        except Exception:
            tail = "<unreadable>"
        raise ZthTaskError(
            f"task interpreter endpoint returned HTTP {exc.code}: {tail}"
        ) from exc
    except TimeoutError as exc:
        raise ZthTaskError(
            f"task interpreter endpoint timed out after {timeout_seconds}s"
        ) from exc
    except urllib.error.URLError as exc:
        raise ZthTaskError(f"task interpreter endpoint call failed: {exc.reason}") from exc
    except OSError as exc:
        raise ZthTaskError(f"task interpreter endpoint call failed: {exc}") from exc
    try:
        envelope = json.loads(body)
    except json.JSONDecodeError as exc:
        raise ZthTaskError("task interpreter endpoint returned non-JSON output") from exc
    if not isinstance(envelope, dict):
        raise ZthTaskError("task interpreter endpoint returned a non-object envelope")
    choices = envelope.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ZthTaskError("task interpreter endpoint returned no choices")
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, str) or not content.strip():
        raise ZthTaskError("task interpreter endpoint returned empty content")
    return content


def _authority_hit(field: str) -> bool:
    lowered = field.lower()
    return any(marker in lowered for marker in _AUTHORITY_FIELD_MARKERS)


def validate_interpretation(payload: object) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ZthTaskError("semantic interpretation must be a JSON object")
    unexpected = sorted(set(payload) - set(INTERPRETATION_KEYS))
    if unexpected:
        kind = (
            "authority-bearing"
            if any(_authority_hit(field) for field in unexpected)
            else "unknown"
        )
        raise ZthTaskError(
            "semantic interpretation carries {} field(s) the contract does not "
            "allow: {}. Model output cannot add fields or grant authority; "
            "failing closed".format(kind, ", ".join(repr(f) for f in unexpected))
        )
    missing = [key for key in INTERPRETATION_KEYS if key not in payload]
    if missing:
        raise ZthTaskError(
            "semantic interpretation is missing required field(s): "
            + ", ".join(missing)
        )
    try:
        goal = clean_text(payload["goal"], "goal")
    except ValueError as exc:
        raise ZthTaskError(str(exc)) from exc
    if not goal:
        raise ZthTaskError("semantic interpretation goal must not be empty")

    raw_candidates = payload["candidate_allowed_paths"]
    if not isinstance(raw_candidates, list) or not raw_candidates:
        raise ZthTaskError(
            "semantic interpretation candidate_allowed_paths must be a non-empty list"
        )
    if len(raw_candidates) > MAX_CANDIDATE_PATHS:
        raise ZthTaskError(
            "semantic interpretation proposes more than "
            f"{MAX_CANDIDATE_PATHS} candidate paths; failing closed"
        )
    if not all(isinstance(item, str) and item.strip() for item in raw_candidates):
        raise ZthTaskError(
            "candidate_allowed_paths entries must be non-empty strings"
        )
    if len(raw_candidates) != len(set(raw_candidates)):
        raise ZthTaskError("candidate_allowed_paths entries must be unique")

    raw_checks = payload["required_checks"]
    if not isinstance(raw_checks, list) or not raw_checks:
        raise ZthTaskError(
            "semantic interpretation required_checks must be a non-empty list; "
            "an empty verification plan fails closed"
        )
    try:
        required_checks = [clean_check(value) for value in raw_checks]
    except ValueError as exc:
        raise ZthTaskError(str(exc)) from exc
    if len(required_checks) != len(set(required_checks)):
        raise ZthTaskError("required_checks entries must be unique")

    raw_questions = payload["historian_questions"]
    if not isinstance(raw_questions, list):
        raise ZthTaskError("historian_questions must be a list")
    if len(raw_questions) > MAX_HISTORIAN_QUESTIONS:
        raise ZthTaskError(
            "historian_questions exceeds the bounded maximum of "
            f"{MAX_HISTORIAN_QUESTIONS}"
        )
    if not all(isinstance(item, str) and item.strip() for item in raw_questions):
        raise ZthTaskError("historian_questions entries must be non-empty strings")
    if len(raw_questions) != len(set(raw_questions)):
        raise ZthTaskError("historian_questions entries must be unique")

    def _clean_list(value: object, label: str) -> list[str]:
        if not isinstance(value, list):
            raise ZthTaskError(f"{label} must be a list")
        if not all(isinstance(item, str) and item.strip() for item in value):
            raise ZthTaskError(f"{label} entries must be non-empty strings")
        return [item.strip() for item in value]

    non_goals = _clean_list(payload["non_goals"], "non_goals")
    uncertainties = _clean_list(payload["uncertainties"], "uncertainties")
    try:
        reasoning_summary = clean_text(payload["reasoning_summary"], "reasoning_summary")
    except ValueError as exc:
        raise ZthTaskError(str(exc)) from exc
    if not reasoning_summary:
        raise ZthTaskError("semantic interpretation reasoning_summary must not be empty")

    return {
        "goal": goal,
        "candidate_allowed_paths": list(raw_candidates),
        "non_goals": non_goals,
        "required_checks": required_checks,
        "historian_questions": list(raw_questions),
        "reasoning_summary": reasoning_summary,
        "uncertainties": uncertainties,
    }


def parse_interpretation(raw: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ZthTaskError(
            f"semantic interpretation is not valid JSON: {exc}"
        ) from exc
    return validate_interpretation(payload)


def _is_private_config_target(normalized: str) -> bool:
    parts = [part.lower() for part in normalized.split("/")]
    base = parts[-1]
    if base == ".env" or base.startswith(".env.") or base.endswith(".env"):
        return True
    if base.startswith("id_rsa") or base.endswith((".pem", ".key")):
        return True
    private_stems = {"secrets", "credentials", "secret", "credential"}
    for part in parts:
        if part in private_stems or part.split(".")[0] in private_stems:
            return True
    return False


def validate_candidate_path(repo_root: Path, candidate: str) -> str:
    try:
        normalized = normalize_allowed_path(candidate)
    except ValueError as exc:
        raise ZthTaskError(f"candidate path rejected: {exc}") from exc
    if any(char in normalized for char in WILDCARD_CHARS):
        raise ZthTaskError(
            f"candidate path uses an unsupported wildcard: {candidate!r}"
        )
    parts = PurePosixPath(normalized).parts
    if parts and parts[0] in PRIVATE_TARGET_ROOTS:
        raise ZthTaskError(
            f"candidate path targets a private/ignored evidence root: {candidate!r}"
        )
    if _is_private_config_target(normalized):
        raise ZthTaskError(
            f"candidate path looks like private configuration or secret "
            f"material: {candidate!r}"
        )
    target = repo_root / normalized
    if target.exists():
        return normalized
    if target.parent.is_dir():
        return normalized
    raise ZthTaskError(
        f"candidate path does not exist and its parent directory does not "
        f"exist: {candidate!r}"
    )


def bind_task_scope(*, repo_root: Path, interpretation: dict[str, Any]) -> dict[str, Any]:
    candidates = interpretation["candidate_allowed_paths"]
    validated: list[str] = []
    held: list[str] = []
    for candidate in candidates:
        try:
            validated.append(validate_candidate_path(repo_root, candidate))
        except ZthTaskError as exc:
            held.append(f"{candidate}: {exc}")
    if held:
        raise ZthTaskError(
            "semantic interpretation proposed unsafe or unverifiable "
            "path(s); deterministic scope binding holds them and creates no "
            "task session: " + " | ".join(held)
        )
    unique_paths: list[str] = []
    for path in validated:
        if path not in unique_paths:
            unique_paths.append(path)
    goal = interpretation["goal"].strip()
    if not goal:
        raise ZthTaskError("bound goal must not be empty")
    checks = interpretation["required_checks"]
    if not checks:
        raise ZthTaskError("bound verification plan must not be empty")
    return {
        "goal": goal,
        "allowed_paths": unique_paths,
        "required_checks": list(checks),
        "non_goals": list(interpretation["non_goals"]),
    }


def gather_historian_context(
    *,
    questions: Sequence[str],
    workspace: Path,
    historian_repo: Path,
    repo_root: Path = REPO_ROOT,
    endpoint: str | None,
    historian_python: str | None = None,
    timeout_seconds: int = DEFAULT_HISTORIAN_TIMEOUT_SECONDS,
    ask_bind: Callable[..., dict[str, Any]] = ask_and_bind_many,
) -> dict[str, Any]:
    historian_dir = workspace / HISTORIAN_DIR_NAME
    entries: list[dict[str, Any]] = []
    if questions:
        try:
            summary = ask_bind(
                questions=list(questions),
                historian_repo=historian_repo,
                output_dir=historian_dir,
                endpoint=endpoint,
                historian_python=historian_python,
                timeout_seconds=timeout_seconds,
            )
        except HistorianAskBindError as exc:
            raise ZthTaskError(f"Historian ask-and-bind failed: {exc}") from exc
        if summary.get("status") != "ok":
            raise ZthTaskError(
                "Historian ask-and-bind failed: "
                f"{summary.get('error', 'unknown failure')}"
            )
        for bound in summary.get("bound", []):
            entries.append(
                {
                    "question": bound.get("question"),
                    "historian_query_id": bound.get("historian_query_id"),
                    "historian_query_dir": bound.get("historian_query_dir"),
                    "context_path": _repo_relative(
                        Path(bound["historian_context_path"]), repo_root
                    ),
                    "context_markdown_path": _repo_relative(
                        Path(bound["historian_context_markdown_path"]), repo_root
                    ),
                    "cited_record_ids": list(bound.get("cited_record_ids", [])),
                    "retrieval_corpus_fingerprint": bound.get(
                        "retrieval_corpus_fingerprint"
                    ),
                    "retrieval_revision": bound.get("retrieval_revision"),
                }
            )
    index_payload = {
        "schema_version": HISTORIAN_INDEX_SCHEMA,
        "questions_asked": len(questions),
        "bound_count": len(entries),
        "contexts": entries,
        "advisory": (
            "Historian answers are advisory interpretation over evidence; the "
            "cited canonical records remain the evidence; a successful query or "
            "bind is not approval."
        ),
        "boundaries": list(FRONTDOOR_BOUNDARIES),
    }
    _write_json(historian_dir / "index.json", index_payload)
    return index_payload


def _context_reference_paths(
    index_payload: dict[str, Any],
    *,
    workspace: Path,
    repo_root: Path,
) -> list[str]:
    workspace_relative = _repo_relative(workspace, repo_root)
    references = [f"{workspace_relative}/{HISTORIAN_INDEX_FILE}"]
    for entry in index_payload.get("contexts", []):
        context_path = entry.get("context_path")
        if isinstance(context_path, str) and context_path:
            references.append(
                f"{workspace_relative}/{HISTORIAN_DIR_NAME}/"
                f"{Path(context_path).name}"
            )
    return references


def record_failure(
    workspace: Path,
    *,
    task_id: str,
    stage: str,
    error: str,
    raw_model_output: str | None = None,
) -> dict[str, Any]:
    failure_path = workspace / FAILURE_FILE
    if failure_path.exists():
        raise ZthTaskError(
            f"failure record already exists and is never overwritten: "
            f"{_display(failure_path)}"
        )
    payload: dict[str, Any] = {
        "schema_version": FAILURE_SCHEMA,
        "task_id": task_id,
        "stage": stage,
        "error": error,
        "failed_at": _utc_now_iso(),
        "preserved": True,
        "boundaries": list(FRONTDOOR_BOUNDARIES),
    }
    if raw_model_output is not None:
        payload["raw_model_output"] = raw_model_output
    _write_json(failure_path, payload)
    return payload


def prepare_task(
    *,
    objective: str,
    historian_repo: Path,
    zth_repo: Path = REPO_ROOT,
    work_root: Path = WORK_ROOT,
    session_root: Path = DEFAULT_SESSION_ROOT,
    interpreter_endpoint: str | None = None,
    interpreter_model: str | None = None,
    historian_endpoint: str | None = None,
    historian_python: str | None = None,
    interpreter_max_tokens: int = DEFAULT_INTERPRETER_MAX_TOKENS,
    interpreter_timeout_seconds: int = DEFAULT_INTERPRETER_TIMEOUT_SECONDS,
    historian_timeout_seconds: int = DEFAULT_HISTORIAN_TIMEOUT_SECONDS,
    preflight_timeout_seconds: int = DEFAULT_PREFLIGHT_TIMEOUT_SECONDS,
    model_call: ModelCall = call_interpreter_model,
    preflight_runner: Callable[..., Any] = run_preflight,
    ask_bind: Callable[..., dict[str, Any]] = ask_and_bind_many,
) -> tuple[dict[str, Any], int]:
    if not isinstance(objective, str) or not objective.strip():
        raise ZthTaskError("an objective must be a non-empty string")
    if isinstance(historian_python, str):
        historian_python = Path(historian_python) if historian_python else None

    created_at = _utc_now_iso()
    task_id = derive_frontdoor_task_id(objective, _utc_now_iso(microseconds=True))
    workspace = work_root / task_id
    if workspace.exists():
        raise ZthTaskError(
            f"task workspace already exists and is never overwritten: {task_id}"
        )
    workspace.mkdir(parents=True)

    result = preflight_runner(
        zth_repo=zth_repo,
        historian_repo=historian_repo,
        historian_python=historian_python,
        timeout_seconds=preflight_timeout_seconds,
    )
    preflight_report = result_json(result)
    _write_json(workspace / PREFLIGHT_FILE, preflight_report)
    _write_json(
        workspace / OBJECTIVE_FILE,
        {
            "schema_version": OBJECTIVE_SCHEMA,
            "task_id": task_id,
            "objective": objective,
            "objective_sha256": _sha256_text(objective),
            "created_at": created_at,
            "zth_head": preflight_report.get("zth", {}).get("head"),
            "historian_head": preflight_report.get("historian", {}).get("head"),
            "frontdoor_schema": FRONTDOOR_SCHEMA,
            "boundaries": list(FRONTDOOR_BOUNDARIES),
        },
    )

    def _blocked(stage: str, error: str, raw: str | None = None) -> tuple[dict[str, Any], int]:
        failure = record_failure(
            workspace, task_id=task_id, stage=stage, error=error, raw_model_output=raw
        )
        payload = _status_payload(
            workspace,
            work_root=work_root,
            session_validator=validate_task_session,
            records_validator=validate_session_records,
        )
        payload["failure"] = {
            "stage": failure["stage"],
            "error": failure["error"],
        }
        return payload, 1

    if result.status != STATUS_PASS:
        errors = "; ".join(preflight_report.get("errors", [])) or "preflight failed"
        return _blocked(STAGE_PREFLIGHT, errors)

    endpoint, endpoint_source = resolve_interpreter_endpoint(interpreter_endpoint)
    model = resolve_interpreter_model(interpreter_model)
    if not endpoint or not model:
        return _blocked(
            STAGE_INTERPRETATION,
            "no task interpreter endpoint/model configured; set "
            f"{INTERPRETER_ENDPOINT_ENV}/{INTERPRETER_MODEL_ENV} or pass "
            "--interpreter-endpoint/--interpreter-model",
        )
    try:
        raw_output = model_call(
            endpoint=endpoint,
            model=model,
            system_prompt=interpreter_system_prompt(),
            user_prompt=interpreter_user_prompt(
                objective=objective,
                zth_head=preflight_report.get("zth", {}).get("head"),
                historian_head=preflight_report.get("historian", {}).get("head"),
                preflight_status=result.status,
            ),
            max_tokens=interpreter_max_tokens,
            timeout_seconds=interpreter_timeout_seconds,
        )
    except ZthTaskError as exc:
        return _blocked(STAGE_INTERPRETATION, str(exc))
    try:
        interpretation = parse_interpretation(raw_output)
    except ZthTaskError as exc:
        return _blocked(STAGE_INTERPRETATION, str(exc), raw=raw_output)
    _write_json(
        workspace / INTERPRETATION_FILE,
        {
            "schema_version": INTERPRETATION_SCHEMA,
            "task_id": task_id,
            "objective_sha256": _sha256_text(objective),
            "authority": (
                "advisory semantic interpretation only; no authority granted; "
                "authority-bearing facts are bound deterministically by ZTH"
            ),
            "contract": {
                "keys": list(INTERPRETATION_KEYS),
                "max_historian_questions": MAX_HISTORIAN_QUESTIONS,
                "max_candidate_paths": MAX_CANDIDATE_PATHS,
            },
            "advisory": interpretation,
            "raw_model_output": raw_output,
            "provenance": {
                "module": MODULE_NAME,
                "model": model,
                "endpoint_source": endpoint_source,
                "temperature": 0,
                "top_p": 1,
                "seed": 42,
                "max_tokens": interpreter_max_tokens,
                "called_at": _utc_now_iso(),
            },
            "boundaries": list(FRONTDOOR_BOUNDARIES),
        },
    )

    try:
        index_payload = gather_historian_context(
            questions=interpretation["historian_questions"],
            workspace=workspace,
            historian_repo=historian_repo,
            repo_root=zth_repo,
            endpoint=historian_endpoint,
            historian_python=historian_python,
            timeout_seconds=historian_timeout_seconds,
            ask_bind=ask_bind,
        )
    except ZthTaskError as exc:
        return _blocked(STAGE_HISTORIAN, str(exc))

    try:
        scope = bind_task_scope(repo_root=zth_repo, interpretation=interpretation)
    except ZthTaskError as exc:
        return _blocked(STAGE_SCOPE_BINDING, str(exc))

    session_name = clean_text(
        scope["goal"][:80] if len(scope["goal"]) > 80 else scope["goal"],
        "task name",
    )
    branch = f"zth-task-{slugify(objective)[:32]}"
    try:
        session = create_task_session(
            name=session_name,
            goal=scope["goal"],
            branch=branch,
            allowed_paths=scope["allowed_paths"],
            required_checks=scope["required_checks"],
            non_goals=scope["non_goals"],
            context_references=_context_reference_paths(
                index_payload, workspace=workspace, repo_root=zth_repo
            ),
            session_root=session_root,
        )
    except ValueError as exc:
        return _blocked(STAGE_SESSION_CREATION, str(exc))

    session_dir = session.output_dir
    try:
        validation = validate_task_session(session_dir)
    except SessionValidationError as exc:
        return _blocked(STAGE_SESSION_VALIDATION, str(exc))

    _write_json(
        workspace / SESSION_REF_FILE,
        {
            "schema_version": SESSION_REF_SCHEMA,
            "task_id": task_id,
            "session_task_id": validation.task_id,
            "session_dir": _display(session_dir),
            "task_yaml_sha256": _sha256_text(
                (session_dir / "task.yaml").read_text(encoding="utf-8")
            ),
            "contract_version": TASK_SESSION_CONTRACT_VERSION,
            "created_at": _utc_now_iso(),
            "boundaries": list(FRONTDOOR_BOUNDARIES),
        },
    )

    payload = _status_payload(
        workspace,
        work_root=work_root,
        session_validator=validate_task_session,
        records_validator=validate_session_records,
    )
    _write_text_summary(workspace, payload)
    return payload, 0


def _write_text_summary(workspace: Path, payload: dict[str, Any]) -> None:
    (workspace / SUMMARY_FILE).write_text(render_summary_text(payload), encoding="utf-8")


def _next_action(state: str, payload: dict[str, Any]) -> str:
    if state == STATE_BLOCKED:
        failure = payload.get("failure") or {}
        return (
            f"BLOCKED at stage {failure.get('stage', 'unknown')}: inspect the "
            "failure record in the task workspace, repair narrowly, and "
            "prepare a new task. The front door never auto-repairs or deletes "
            "evidence."
        )
    if state == STATE_CREATED:
        return (
            "preparation incomplete: no validated semantic interpretation and "
            "Historian context; re-run prepare for a new task"
        )
    if state == STATE_CONTEXT_BOUND:
        return (
            "preparation incomplete: no validated Agent Task Session; "
            "re-run prepare for a new task"
        )
    if state == STATE_READY_FOR_EXECUTION:
        return (
            "operator review of the proposed scope is required before "
            "execution; when execution is explicitly authorized, run: "
            "python3 local_harness/zth_task.py handoff "
            f"{payload.get('task_id')}"
        )
    if state == STATE_EXECUTED:
        return (
            "human review pending: record the human-supplied review decision "
            "with local_harness/agent_task_session_record.py record-review"
        )
    if state == STATE_REVIEWED:
        decision = (payload.get("review") or {}).get("decision")
        return (
            f"review decision recorded ({decision}); recording is evidence, "
            "not lifecycle promotion; acceptance, follow-up, and repository "
            "action remain human decisions"
        )
    return "unknown state"


def _status_payload(
    workspace: Path,
    *,
    work_root: Path = WORK_ROOT,
    session_validator: Callable[..., Any] = validate_task_session,
    records_validator: Callable[..., Any] = validate_session_records,
) -> dict[str, Any]:
    task_id = workspace.name
    if not workspace.is_dir():
        raise ZthTaskError(f"no front-door task workspace: {task_id}")
    objective_record = _read_json_file(workspace / OBJECTIVE_FILE, "objective")
    if objective_record.get("task_id") != task_id:
        raise ZthTaskError(
            "objective artifact task_id does not match the workspace name; "
            "refusing to guess"
        )
    preflight_report = _read_json_file(workspace / PREFLIGHT_FILE, "preflight")

    payload: dict[str, Any] = {
        "schema_version": FRONTDOOR_SCHEMA,
        "task_id": task_id,
        "objective": objective_record.get("objective"),
        "objective_sha256": objective_record.get("objective_sha256"),
        "created_at": objective_record.get("created_at"),
        "baseline": {
            "preflight_status": preflight_report.get("status"),
            "zth_head": objective_record.get("zth_head"),
            "historian_head": objective_record.get("historian_head"),
        },
        "boundaries": list(FRONTDOOR_BOUNDARIES),
    }
    state = STATE_CREATED

    failure_path = workspace / FAILURE_FILE
    if failure_path.exists():
        failure = _read_json_file(failure_path, "failure")
        payload["failure"] = {
            "stage": failure.get("stage"),
            "error": failure.get("error"),
            "failed_at": failure.get("failed_at"),
        }
        state = STATE_BLOCKED
        payload["state"] = state
        payload["next_action"] = _next_action(state, payload)
        return payload

    interpretation_path = workspace / INTERPRETATION_FILE
    index_path = workspace / Path(HISTORIAN_INDEX_FILE)
    interpretation = None
    if interpretation_path.exists():
        interpretation = _read_json_file(
            interpretation_path, "semantic interpretation"
        )
    if index_path.exists():
        index_payload = _read_json_file(index_path, "historian index")
        contexts = index_payload.get("contexts", [])
        cited = sorted(
            {
                record_id
                for entry in contexts
                for record_id in entry.get("cited_record_ids", [])
            }
        )
        payload["historian"] = {
            "questions_asked": index_payload.get("questions_asked"),
            "bound_count": index_payload.get("bound_count"),
            "cited_record_ids": cited,
            "retrieval_corpus_fingerprint": (
                contexts[0].get("retrieval_corpus_fingerprint")
                if contexts
                else None
            ),
            "advisory": index_payload.get("advisory"),
        }
    if interpretation is not None and index_path.exists():
        state = STATE_CONTEXT_BOUND
        payload["semantic_interpretation"] = {
            "advisory": interpretation.get("advisory"),
            "authority": interpretation.get("authority"),
            "provenance": interpretation.get("provenance"),
        }

    session_ref_path = workspace / SESSION_REF_FILE
    if session_ref_path.exists():
        session_ref = _read_json_file(session_ref_path, "task session reference")
        session_dir = REPO_ROOT / str(session_ref.get("session_dir", ""))
        try:
            validation = session_validator(session_dir)
        except SessionValidationError as exc:
            payload["state"] = STATE_BLOCKED
            payload["blocked_reason"] = (
                f"the recorded Agent Task Session no longer validates: {exc}"
            )
            payload["next_action"] = _next_action(STATE_BLOCKED, payload)
            return payload
        payload["task_session"] = {
            "task_id": session_ref.get("session_task_id"),
            "dir": session_ref.get("session_dir"),
            "task_yaml_sha256": session_ref.get("task_yaml_sha256"),
            "allowed_paths": list(validation.allowed_paths),
            "required_checks": list(validation.required_checks),
            "contract_version": session_ref.get("contract_version"),
        }
        try:
            records = records_validator(session_dir)
        except SessionRecordError as exc:
            payload["state"] = STATE_BLOCKED
            payload["blocked_reason"] = (
                f"the recorded execution/review evidence no longer validates: {exc}"
            )
            payload["next_action"] = _next_action(STATE_BLOCKED, payload)
            return payload
        stage = records.stage
        if stage == "reviewed":
            state = STATE_REVIEWED
            payload["review"] = {
                "decision": records.effective_review_decision,
                "review_id": records.effective_review_id,
                "note": "recorded supplied input; not tool-verified identity",
            }
        elif stage == "executed":
            state = STATE_EXECUTED
        else:
            state = STATE_READY_FOR_EXECUTION
        payload["executions"] = [
            {"execution_id": execution_id}
            for execution_id in records.execution_ids
        ]
        if state == STATE_EXECUTED and "review" not in payload:
            payload["review"] = {"decision": None, "note": "pending human review"}

    payload["state"] = state
    payload["next_action"] = _next_action(state, payload)
    return payload


def derive_task_status(
    task_id: str,
    *,
    work_root: Path = WORK_ROOT,
    session_validator: Callable[..., Any] = validate_task_session,
    records_validator: Callable[..., Any] = validate_session_records,
) -> dict[str, Any]:
    validate_task_id(task_id)
    return _status_payload(
        work_root / task_id,
        work_root=work_root,
        session_validator=session_validator,
        records_validator=records_validator,
    )


def render_summary_text(payload: dict[str, Any]) -> str:
    baseline = payload.get("baseline", {})
    historian = payload.get("historian") or {}
    session = payload.get("task_session") or {}
    interpretation = payload.get("semantic_interpretation") or {}
    advisory = interpretation.get("advisory") or {}
    lines: list[str] = []
    lines.append(f"ZTH TASK {payload.get('task_id')}")
    lines.append("")
    lines.append("objective:")
    lines.append(f"  {payload.get('objective')}")
    lines.append("")
    lines.append("baseline:")
    lines.append(f"  preflight: {baseline.get('preflight_status')}")
    lines.append(f"  ZTH HEAD: {baseline.get('zth_head')}")
    lines.append(f"  Historian HEAD: {baseline.get('historian_head')}")
    if historian:
        lines.append(
            f"  historian: {historian.get('bound_count')} question(s) bound, "
            f"{len(historian.get('cited_record_ids', []))} canonical record(s) cited"
        )
    lines.append("")
    lines.append("semantic interpretation (advisory):")
    lines.append(f"  goal: {advisory.get('goal')}")
    reasoning = advisory.get("reasoning_summary") or ""
    if reasoning:
        snippet = reasoning if len(reasoning) <= 200 else reasoning[:197] + "..."
        lines.append(f"  reasoning: {snippet}")
    lines.append("")
    lines.append("proposed task:")
    lines.append(f"  goal: {advisory.get('goal') or ''}")
    for path in session.get("allowed_paths", []):
        lines.append(f"    - {path}")
    lines.append("  required checks:")
    for check in session.get("required_checks", []):
        lines.append(f"    - {check}")
    non_goals = advisory.get("non_goals", [])
    lines.append("  non-goals:")
    for non_goal in non_goals:
        lines.append(f"    - {non_goal}")
    if not non_goals:
        lines.append("    - (none recorded)")
    lines.append("")
    lines.append("task session:")
    lines.append(f"  id: {session.get('task_id')}")
    lines.append(f"  path: {session.get('dir')}")
    lines.append("  validation: VALID")
    lines.append("")
    lines.append("authority:")
    for boundary in FRONTDOOR_BOUNDARIES:
        lines.append(f"  - {boundary}")
    lines.append("")
    lines.append(f"STATUS: {(payload.get('state') or '').upper()}")
    lines.append(f"NEXT ACTION: {payload.get('next_action')}")
    return "\n".join(lines) + "\n"


def render_status_text(payload: dict[str, Any]) -> str:
    baseline = payload.get("baseline", {})
    historian = payload.get("historian") or {}
    session = payload.get("task_session") or {}
    executions = payload.get("executions") or []
    review = payload.get("review") or {}
    lines: list[str] = []
    lines.append(f"ZTH TASK STATUS {payload.get('task_id')}")
    lines.append("")
    lines.append(f"objective: {payload.get('objective')}")
    lines.append(f"state: {payload.get('state')}")
    if payload.get("blocked_reason"):
        lines.append(f"blocked reason: {payload['blocked_reason']}")
    lines.append(
        f"baseline: preflight {baseline.get('preflight_status')} "
        f"(ZTH {baseline.get('zth_head')}, Historian {baseline.get('historian_head')})"
    )
    if historian:
        lines.append(
            f"historian: {historian.get('bound_count')} bound, "
            f"{len(historian.get('cited_record_ids', []))} cited"
        )
    if session:
        lines.append(f"task session: {session.get('task_id')} (VALID)")
        lines.append(f"  path: {session.get('dir')}")
        for check in session.get("required_checks", []):
            lines.append(f"  check: {check}")
    else:
        lines.append("task session: none yet")
    if payload.get("failure"):
        lines.append(f"failure: stage {payload['failure'].get('stage')}")
    if executions:
        lines.append(
            "executions: "
            + ", ".join(
                entry.get("execution_id") or "?" for entry in executions
            )
        )
    else:
        lines.append("executions: none")
    if review.get("decision"):
        lines.append(
            f"review: {review.get('decision')} ({review.get('review_id')}) "
            "[recorded supplied input, not tool-verified]"
        )
    else:
        lines.append("review: pending (human-supplied decision required)")
    lines.append("")
    lines.append(f"NEXT ACTION: {payload.get('next_action')}")
    lines.append("")
    lines.append("Boundaries:")
    for boundary in FRONTDOOR_BOUNDARIES:
        lines.append(f"Boundary: {boundary}")
    return "\n".join(lines) + "\n"


def render_handoff_text(payload: dict[str, Any]) -> str:
    session = payload.get("task_session") or {}
    session_dir = session.get("dir")
    prompt_path = (
        f"{session_dir}/codex_prompt.md" if isinstance(session_dir, str) else None
    )
    outcome_flags = " ".join(
        f'--outcome "<observed outcome {index + 1}>"'
        for index in range(len(session.get("required_checks", [])))
    )
    lines: list[str] = []
    lines.append(f"ZTH TASK HANDOFF {payload.get('task_id')}")
    lines.append("")
    lines.append("This handoff emits the exact validated packet. It executes")
    lines.append("nothing, grants no authority, and records no review.")
    lines.append("")
    lines.append("agent prompt (hand this file to the coding agent):")
    lines.append(f"  {prompt_path}")
    lines.append("")
    lines.append("task session:")
    lines.append(f"  id: {session.get('task_id')}")
    lines.append(f"  path: {session_dir}")
    lines.append("allowed paths:")
    for path in session.get("allowed_paths", []):
        lines.append(f"  - {path}")
    lines.append("required checks (run only within the authorized task; record")
    lines.append("one observed outcome per check, in packet order):")
    for check in session.get("required_checks", []):
        lines.append(f"  - {check}")
    lines.append("")
    lines.append("record execution evidence afterwards with:")
    lines.append(
        "  python3 local_harness/agent_task_session_record.py record-execution "
        f"{session_dir} {outcome_flags}"
    )
    lines.append("")
    lines.append("human review remains a separate, required step; execution")
    lines.append("evidence is not acceptance; a commit is not acceptance.")
    return "\n".join(lines) + "\n"


def handoff_task(
    task_id: str,
    *,
    work_root: Path = WORK_ROOT,
    session_validator: Callable[..., Any] = validate_task_session,
    records_validator: Callable[..., Any] = validate_session_records,
) -> tuple[dict[str, Any], int]:
    payload = derive_task_status(
        task_id,
        work_root=work_root,
        session_validator=session_validator,
        records_validator=records_validator,
    )
    state = payload.get("state")
    if state not in {STATE_READY_FOR_EXECUTION, STATE_EXECUTED}:
        raise ZthTaskError(
            f"handoff requires a validated, execution-ready task session; "
            f"current state is {state!r}"
        )
    session = payload.get("task_session") or {}
    payload["handoff"] = {
        "agent_prompt_path": f"{session.get('dir')}/codex_prompt.md",
        "record_execution_command": (
            "python3 local_harness/agent_task_session_record.py "
            f"record-execution {session.get('dir')} "
            + " ".join(
                f'--outcome "<observed outcome {index + 1}>"'
                for index in range(len(session.get("required_checks", [])))
            )
        ),
        "note": (
            "handoff emits the packet; it executes nothing, grants no "
            "authority, and records no review"
        ),
    }
    return payload, 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="zth_task.py",
        description=(
            "Supervised ZTH task front door: one interface from an "
            "ordinary-language objective to a validated, context-backed, "
            "execution-ready Agent Task Session. Preparation grants no "
            "execution authority; human review remains a separate, required "
            "step."
        ),
        epilog="\n".join(f"Boundary: {line}" for line in FRONTDOOR_BOUNDARIES),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare_parser = subparsers.add_parser(
        "prepare",
        help="Preflight, preserve the objective, interpret it, bind Historian "
        "context, and create a validated Agent Task Session.",
    )
    prepare_parser.add_argument(
        "objective",
        help="The operator objective, verbatim, in ordinary language.",
    )
    prepare_parser.add_argument(
        "--historian-repo",
        type=Path,
        required=True,
        help="Path to the Project Historian repository.",
    )
    prepare_parser.add_argument(
        "--interpreter-endpoint",
        help=f"OpenAI-compatible endpoint for advisory task interpretation "
        f"(or {INTERPRETER_ENDPOINT_ENV}).",
    )
    prepare_parser.add_argument(
        "--interpreter-model",
        help=f"Model id for advisory task interpretation "
        f"(or {INTERPRETER_MODEL_ENV}).",
    )
    prepare_parser.add_argument(
        "--max-tokens",
        type=int,
        default=DEFAULT_INTERPRETER_MAX_TOKENS,
        help="Max tokens for the interpretation call.",
    )
    prepare_parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_INTERPRETER_TIMEOUT_SECONDS,
        help="Timeout for the interpretation call, in seconds.",
    )
    prepare_parser.add_argument(
        "--historian-endpoint",
        help="Optional reasoner endpoint override passed through to the "
        "consolidated Historian ask-and-bind command.",
    )
    prepare_parser.add_argument(
        "--historian-python",
        help="Optional override for the Historian retrieval runtime.",
    )
    prepare_parser.add_argument(
        "--historian-timeout",
        type=int,
        default=DEFAULT_HISTORIAN_TIMEOUT_SECONDS,
        help="Timeout for the consolidated Historian ask-and-bind run.",
    )
    prepare_parser.add_argument(
        "--json",
        action="store_true",
        help="Print a machine-readable summary.",
    )

    status_parser = subparsers.add_parser(
        "status",
        help="Derive and display the current task state from durable artifacts.",
    )
    status_parser.add_argument("task_id", help="Front-door task id.")
    status_parser.add_argument(
        "--json",
        action="store_true",
        help="Print a machine-readable status.",
    )

    handoff_parser = subparsers.add_parser(
        "handoff",
        help="Emit the exact validated agent packet and where execution "
        "evidence belongs.",
    )
    handoff_parser.add_argument("task_id", help="Front-door task id.")
    handoff_parser.add_argument(
        "--json",
        action="store_true",
        help="Print a machine-readable handoff.",
    )
    return parser


def _print_result(payload: dict[str, Any], *, json_mode: bool, text_key: str) -> None:
    if json_mode:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return
    if text_key == "summary":
        print(render_summary_text(payload), end="")
    elif text_key == "status":
        print(render_status_text(payload), end="")
    else:
        print(render_handoff_text(payload), end="")


def main(argv: Sequence[str] | None = None) -> int:
    args_list = list(sys.argv[1:] if argv is None else argv)
    if args_list and args_list[0] not in {"prepare", "status", "handoff"} and not args_list[0].startswith("-"):
        args_list = ["prepare", *args_list]
    args = build_parser().parse_args(args_list)
    try:
        if args.command == "prepare":
            payload, exit_code = prepare_task(
                objective=args.objective,
                historian_repo=args.historian_repo,
                interpreter_endpoint=args.interpreter_endpoint,
                interpreter_model=args.interpreter_model,
                historian_endpoint=args.historian_endpoint,
                historian_python=args.historian_python,
                interpreter_max_tokens=args.max_tokens,
                interpreter_timeout_seconds=args.timeout,
                historian_timeout_seconds=args.historian_timeout,
            )
            _print_result(payload, json_mode=args.json, text_key="summary")
            return exit_code
        if args.command == "status":
            payload = derive_task_status(args.task_id)
            _print_result(payload, json_mode=args.json, text_key="status")
            return 0
        payload, exit_code = handoff_task(args.task_id)
        _print_result(payload, json_mode=args.json, text_key="handoff")
        return exit_code
    except (ZthTaskError, ValueError) as exc:
        print(f"zth-task: error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
