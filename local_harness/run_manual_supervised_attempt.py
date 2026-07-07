#!/usr/bin/env python3
"""Manual supervised model-attempt runner with prepare and ingest phases."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from local_harness.orchestration_packet import assemble_orchestration_packet, validate_orchestration_packet
from local_harness.prompt_patch_library import PromptPatchLibrary
from local_harness.render_model_prompt_packet import (
    build_model_prompt_output_contract,
    render_model_prompt_packet,
)
from local_harness.render_supervised_attempt_output_validation import (
    render_supervised_attempt_output_validation,
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
    output_contract = build_model_prompt_output_contract(orchestration_packet, patch_library)

    messy_input_path = run_dir / "messy_input.txt"
    prompt_path = run_dir / "model_prompt_packet.md"
    instructions_path = run_dir / "operator_instructions.txt"
    output_contract_path = run_dir / "output_contract.json"
    triage_packet_path = run_dir / "triage_packet.json"
    orchestration_packet_path = run_dir / "orchestration_packet.json"
    manifest_path = run_dir / "run_manifest.json"

    messy_input_path.write_text(messy_input + "\n", encoding="utf-8")
    prompt_path.write_text(model_prompt_packet.rstrip() + "\n", encoding="utf-8")
    instructions_path.write_text(_operator_instructions_text(run_dir), encoding="utf-8")
    _write_json(output_contract_path, output_contract)
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
            "operator_instructions": str(instructions_path),
            "output_contract": str(output_contract_path),
            "triage_packet": str(triage_packet_path),
            "orchestration_packet": str(orchestration_packet_path),
        },
    }
    _write_json(manifest_path, manifest)

    return {
        "run_dir": run_dir,
        "manifest_path": manifest_path,
        "model_prompt_packet_path": prompt_path,
        "output_contract_path": output_contract_path,
    }


def run_session(
    *,
    messy_input: str,
    out_dir: Path,
    timestamp: str | None = None,
    overwrite: bool = False,
    write_prompt_copy: bool = False,
) -> dict[str, Any]:
    prepare_result = run_prepare(
        messy_input=messy_input,
        out_dir=out_dir,
        timestamp=timestamp,
        overwrite=overwrite,
    )
    run_dir = Path(prepare_result["run_dir"])
    model_prompt_packet_path = Path(prepare_result["model_prompt_packet_path"])
    prompt_to_paste_path = run_dir / "prompt_to_paste.md"
    raw_output_path = run_dir / "raw_model_output.txt"

    prompt_to_paste_path.write_text(model_prompt_packet_path.read_text(encoding="utf-8"), encoding="utf-8")

    raw_output_path.write_text("", encoding="utf-8")

    return {
        "run_dir": run_dir,
        "manifest_path": Path(prepare_result["manifest_path"]),
        "model_prompt_packet_path": model_prompt_packet_path,
        "prompt_to_paste_path": prompt_to_paste_path,
        "raw_output_file_path": raw_output_path,
        "ingest_command": _ingest_command(run_dir, raw_output_path),
        "write_prompt_copy": write_prompt_copy,
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


def _require_nonempty(value: str | None, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value


def run_ingest(
    *,
    run_dir: Path,
    raw_output_file: Path,
    decision: str | None = None,
    decision_reason: str | None = None,
    operator: str | None = None,
) -> dict[str, Any]:
    manifest, manifest_path = _resolve_manifest(run_dir)

    artifacts = manifest["artifacts"]
    output_contract_path = Path(_require_nonempty(artifacts.get("output_contract"), field="artifacts.output_contract"))
    model_prompt_packet_path = Path(
        _require_nonempty(artifacts.get("model_prompt_packet"), field="artifacts.model_prompt_packet")
    )
    output_contract = _read_json(output_contract_path, kind="output contract")

    if not raw_output_file.is_file():
        raise ValueError(f"--raw-output-file does not exist: {raw_output_file}")
    raw_output_text = raw_output_file.read_text(encoding="utf-8")

    run_raw_output_path = run_dir / "raw_model_output.txt"
    run_raw_output_path.write_text(raw_output_text, encoding="utf-8")

    ts = _utc_timestamp().lower()
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
        provenance={
            "source": "manual_operator_pasted_model_output",
            "input_artifact": "model_prompt_packet",
            "raw_output_preserved": True,
            "run_manifest_path": str(manifest_path),
            "raw_output_source_path": str(raw_output_file),
        },
    )

    validation_record = validate_supervised_attempt_output_against_contract(
        attempt_record=attempt_record,
        output_contract=output_contract,
        validation_id=f"manual_validation_{ts}",
        validated_at=_utc_iso(),
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

    session = subparsers.add_parser("session")
    session.add_argument("--messy-input")
    session.add_argument("--messy-input-file", type=Path)
    session.add_argument("--out-dir", type=Path, required=True)
    session.add_argument("--timestamp")
    session.add_argument("--overwrite", action="store_true")
    session.add_argument("--print-prompt", action="store_true")
    session.add_argument("--write-prompt-copy", action="store_true")

    ingest = subparsers.add_parser("ingest")
    ingest.add_argument("--run-dir", type=Path, required=True)
    ingest.add_argument("--raw-output-file", type=Path, required=True)
    ingest.add_argument("--decision", choices=sorted(ALLOWED_DECISIONS))
    ingest.add_argument("--decision-reason")
    ingest.add_argument("--operator")

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

        if args.decision is not None and not (isinstance(args.decision_reason, str) and args.decision_reason.strip()):
            raise ValueError("--decision-reason is required when --decision is provided")

        result = run_ingest(
            run_dir=args.run_dir,
            raw_output_file=args.raw_output_file,
            decision=args.decision,
            decision_reason=args.decision_reason,
            operator=args.operator,
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
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
