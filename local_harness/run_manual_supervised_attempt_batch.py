#!/usr/bin/env python3
"""Deterministic mini-batch runner for manual supervised attempts."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import local_harness.run_manual_supervised_attempt as manual_attempt


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _read_jsonl_tasks(tasks_jsonl: Path) -> list[dict[str, Any]]:
    if not tasks_jsonl.is_file():
        raise ValueError(f"--tasks-jsonl does not exist: {tasks_jsonl}")
    tasks: list[dict[str, Any]] = []
    for lineno, line in enumerate(tasks_jsonl.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON on line {lineno} of {tasks_jsonl}: {exc.msg}") from exc
        if not isinstance(payload, dict):
            raise ValueError(f"task entry on line {lineno} must be a JSON object")
        if not isinstance(payload.get("task_id"), str) or not payload["task_id"].strip():
            raise ValueError(f"task entry on line {lineno} is missing task_id")
        if not isinstance(payload.get("messy_input"), str) or not payload["messy_input"].strip():
            raise ValueError(f"task entry on line {lineno} is missing messy_input")
        tasks.append(payload)
    return tasks


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, sort_keys=True) + "\n")


def _write_summary(path: Path, records: list[dict[str, Any]], *, endpoint: str, model: str) -> None:
    initial_pass = sum(1 for r in records if r["initial_validation_status"] == "passed")
    retry_pass = sum(1 for r in records if r["retry_validation_status"] == "passed")
    failed_snapshot_count = sum(1 for r in records if r["failed_snapshot_preserved"])
    lines = [
        "# Mini-batch Summary",
        "",
        f"- endpoint: {endpoint}",
        f"- model: {model}",
        f"- task count: {len(records)}",
        f"- initial passed: {initial_pass}",
        f"- initial failed: {len(records) - initial_pass}",
        f"- retry passed: {retry_pass}",
        f"- retry failed: {sum(1 for r in records if r['retry_validation_status'] == 'failed')}",
        f"- failed snapshot preservation count: {failed_snapshot_count}",
        f"- timeout evidence observations: {sum(1 for r in records if r['timeout_evidence_preserved'])}",
        f"- accepted count: 0",
        f"- pattern exported count: 0",
        "",
        "## Safety Boundaries",
        "",
        "- no model output executed/applied",
        "- no acceptance",
        "- no promotion",
        "- no training",
        "- no materialization",
        "- no automatic failure-to-curriculum capture",
        "",
    ]
    target_statuses = ", ".join(sorted({str(r["target_authority_status"]) for r in records}))
    duplicate_statuses = ", ".join(sorted({str(r["duplicate_json_keys_status"]) for r in records}))
    type_statuses = ", ".join(sorted({str(r["required_field_types_status"]) for r in records}))
    lines.extend(
        [
            f"- target authority results: {target_statuses}",
            f"- duplicate_json_keys results: {duplicate_statuses}",
            f"- required_field_types results: {type_statuses}",
        ]
    )
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _status_from_check(validation: dict[str, Any], check_id: str) -> str | None:
    for check in validation.get("checks", []):
        if isinstance(check, dict) and check.get("check_id") == check_id:
            status = check.get("status")
            return status if isinstance(status, str) else None
    return None


def _record_timeout_evidence(run_dir: Path) -> bool | None:
    call_failed = run_dir / "local_model_call.failed.json"
    response_failed = run_dir / "local_model_response.failed.json"
    if not call_failed.exists() and not response_failed.exists():
        return None
    return call_failed.exists() or response_failed.exists()


def run_batch(
    *,
    tasks_jsonl: Path,
    out_dir: Path,
    endpoint: str,
    model: str,
    max_tokens: int = 4096,
    timeout_seconds: float = 480,
    max_tasks: int | None = None,
    task_ids: list[str] | None = None,
    retry_limit: int = 0,
    operator: str = "batch_runner",
    timestamp: str | None = None,
    dry_run: bool = False,
    overwrite: bool = False,
) -> dict[str, Any]:
    if out_dir.exists() and any(out_dir.iterdir()) and not overwrite:
        raise FileExistsError(f"--out-dir is not empty: {out_dir}")

    tasks = _read_jsonl_tasks(tasks_jsonl)
    if task_ids:
        task_id_set = set(task_ids)
        tasks = [task for task in tasks if task["task_id"] in task_id_set]
    if max_tasks is not None:
        tasks = tasks[:max_tasks]

    batch_ts = timestamp or _utc_timestamp()
    runs_root = out_dir / "runs"
    runs_root.mkdir(parents=True, exist_ok=True)

    ledger_records: list[dict[str, Any]] = []

    for task in tasks:
        task_id = task["task_id"]
        task_root = runs_root / task_id
        task_root.mkdir(parents=True, exist_ok=True)
        (task_root / "task_input.txt").write_text(task["messy_input"] + "\n", encoding="utf-8")
        attempt_dir = task_root / "attempt_1"

        initial_validation_status = "not_run"
        retry_validation_status = "not_run"
        retries = 0
        failed_snapshot_preserved = False
        timeout_evidence_preserved: bool | None = None
        notes: list[str] = []
        validation_payload: dict[str, Any] | None = None

        try:
            if dry_run:
                notes.append("dry-run: skipped session/call-local/ingest")
            else:
                manual_attempt.run_session(
                    messy_input=task["messy_input"],
                    out_dir=task_root,
                    timestamp="attempt_1",
                    overwrite=True,
                )
                try:
                    manual_attempt.run_call_local(
                        run_dir=attempt_dir,
                        endpoint=endpoint,
                        model=model,
                        temperature=0,
                        max_tokens=max_tokens,
                        timeout_seconds=timeout_seconds,
                        overwrite=False,
                    )
                except Exception as exc:
                    notes.append(f"call-local failed: {exc}")
                call_failed = attempt_dir / "local_model_call.failed.json"
                response_failed = attempt_dir / "local_model_response.failed.json"
                if call_failed.exists() or response_failed.exists():
                    timeout_evidence_preserved = call_failed.exists() or response_failed.exists()
                    notes.append("call-local failure evidence preserved")
                ingest_result = manual_attempt.run_ingest(
                    run_dir=attempt_dir,
                    raw_output_file=attempt_dir / "raw_model_output.txt",
                    operator=operator,
                )
                initial_validation_status = ingest_result["validation_status"]
                validation_payload = json.loads((attempt_dir / "output_validation.json").read_text(encoding="utf-8"))
                if initial_validation_status == "failed" and retry_limit >= 1:
                    manual_attempt._run_retry_contract(run_dir=attempt_dir, retry_id=1)
                    retries = 1
                    failed_snapshot_preserved = all(
                        (attempt_dir / name).is_file()
                        for name in [
                            "raw_model_output.failed_1.txt",
                            "output_validation.failed_1.json",
                            "output_validation_report.failed_1.txt",
                            "retry_prompt_to_paste_1.md",
                            "prompt_to_paste.md",
                        ]
                    )
                    if failed_snapshot_preserved:
                        notes.append("retry-contract preserved failed snapshots")
                    try:
                        manual_attempt.run_call_local(
                            run_dir=attempt_dir,
                            endpoint=endpoint,
                            model=model,
                            temperature=0,
                            max_tokens=max_tokens,
                            timeout_seconds=timeout_seconds,
                            overwrite=True,
                        )
                    except Exception as exc:
                        notes.append(f"retry call-local failed: {exc}")
                    retry_ingest = manual_attempt.run_ingest(
                        run_dir=attempt_dir,
                        raw_output_file=attempt_dir / "raw_model_output.txt",
                        operator=operator,
                    )
                    retry_validation_status = retry_ingest["validation_status"]
        except Exception as exc:
            notes.append(f"task failed: {exc}")
            if validation_payload is None and (attempt_dir / "output_validation.json").is_file():
                validation_payload = json.loads((attempt_dir / "output_validation.json").read_text(encoding="utf-8"))

        if validation_payload is None and (attempt_dir / "output_validation.json").is_file():
            validation_payload = json.loads((attempt_dir / "output_validation.json").read_text(encoding="utf-8"))

        ledger_records.append(
            {
                "task_id": task_id,
                "run_dir": str(attempt_dir),
                "initial_validation_status": initial_validation_status,
                "retry_validation_status": retry_validation_status,
                "retries": retries,
                "accepted": False,
                "pattern_exported": False,
                "failed_snapshot_preserved": failed_snapshot_preserved,
                "timeout_evidence_preserved": timeout_evidence_preserved,
                "target_authority_status": _status_from_check(validation_payload or {}, "target_authority"),
                "duplicate_json_keys_status": _status_from_check(validation_payload or {}, "duplicate_json_keys"),
                "required_field_types_status": _status_from_check(validation_payload or {}, "required_field_types"),
                "notes": "; ".join(notes) if notes else "completed",
            }
        )

    ledger_path = out_dir / "batch_ledger.jsonl"
    summary_path = out_dir / "batch_summary.md"
    _write_jsonl(ledger_path, ledger_records)
    _write_summary(summary_path, ledger_records, endpoint=endpoint, model=model)
    return {
        "batch_ts": batch_ts,
        "ledger_path": ledger_path,
        "summary_path": summary_path,
        "records": ledger_records,
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks-jsonl", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--timeout-seconds", type=float, default=480)
    parser.add_argument("--max-tasks", type=int)
    parser.add_argument("--task-id", action="append")
    parser.add_argument("--retry-limit", type=int, default=0)
    parser.add_argument("--operator", default="batch_runner")
    parser.add_argument("--timestamp")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    try:
        result = run_batch(
            tasks_jsonl=args.tasks_jsonl,
            out_dir=args.out_dir,
            endpoint=args.endpoint,
            model=args.model,
            max_tokens=args.max_tokens,
            timeout_seconds=args.timeout_seconds,
            max_tasks=args.max_tasks,
            task_ids=args.task_id,
            retry_limit=args.retry_limit,
            operator=args.operator,
            timestamp=args.timestamp,
            dry_run=args.dry_run,
            overwrite=args.overwrite,
        )
        print(f"ledger_path: {result['ledger_path']}")
        print(f"summary_path: {result['summary_path']}")
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
