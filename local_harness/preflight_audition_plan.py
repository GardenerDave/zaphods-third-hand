#!/usr/bin/env python3
"""Print a supervised preflight-to-audition command plan without executing it."""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Sequence


PLAN_CONTRACT_VERSION = "zth.preflight_audition_plan.v0.1"
PREFLIGHT_CONTRACT_VERSION = "zth.llm_probe_preflight.v0.1"
PREFLIGHT_STATUSES = {"pass", "intermittent", "fail", "unknown"}
SAFETY_NOTES = (
    "The planner does not run models or auditions.",
    "The planner does not start model endpoints.",
    "The planner does not perform cleanup or delete .work or other evidence.",
    "The planner does not promote, approve, rank, or assign models.",
    "Printed commands are review material and must be run manually.",
    "Passing checks are evidence, not authority.",
)


@dataclass(frozen=True)
class PlanInput:
    llm_probe_output: Path | None
    manifest: Path | None
    model: Path
    suite: Path | None
    board: Path | None
    out_dir: Path
    write_plan: Path | None = None


@dataclass(frozen=True)
class PlannedCommand:
    label: str
    command: tuple[str, ...]
    writes: tuple[Path, ...] = ()
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class Plan:
    mode: Literal["single-suite", "board"]
    source_kind: Literal["llm-probe-output", "manifest"]
    source_path: Path
    manifest_path: Path
    model_path: Path
    target_path: Path
    out_dir: Path
    commands: tuple[PlannedCommand, ...]
    derived_artifacts: tuple[Path, ...]
    safety_notes: tuple[str, ...] = SAFETY_NOTES


def read_json_object(path: Path, description: str) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError as exc:
        raise ValueError(f"{description} is not valid UTF-8: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"{description} is not valid JSON: {path}: "
            f"line {exc.lineno} column {exc.colno}"
        ) from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{description} must contain a JSON object: {path}")
    return payload


def require_file(path: Path, description: str) -> None:
    if not path.is_file():
        raise ValueError(f"{description} is not a file: {path}")


def require_empty_or_missing_directory(path: Path, description: str) -> None:
    if path.exists() and not path.is_dir():
        raise ValueError(f"{description} is not a directory: {path}")
    if path.is_dir() and any(path.iterdir()):
        raise ValueError(f"{description} exists and is non-empty: {path}")


def validate_manifest(path: Path) -> None:
    manifest = read_json_object(path, "preflight manifest")
    if manifest.get("output_contract_version") != PREFLIGHT_CONTRACT_VERSION:
        raise ValueError(
            "preflight manifest has unsupported output_contract_version"
        )
    if manifest.get("scope") != "preflight_only":
        raise ValueError("preflight manifest must have scope 'preflight_only'")
    if manifest.get("promotion_performed") is not False:
        raise ValueError(
            "preflight manifest must record promotion_performed as false"
        )
    if manifest.get("requires_human_review") is not True:
        raise ValueError(
            "preflight manifest must record requires_human_review as true"
        )
    if manifest.get("preflight_status") not in PREFLIGHT_STATUSES:
        raise ValueError(
            "preflight manifest preflight_status must be one of: "
            + ", ".join(sorted(PREFLIGHT_STATUSES))
        )


def validate_inputs(plan_input: PlanInput) -> str:
    sources = [
        plan_input.llm_probe_output is not None,
        plan_input.manifest is not None,
    ]
    if sum(sources) != 1:
        raise ValueError(
            "provide exactly one of --llm-probe-output or --manifest"
        )

    targets = [plan_input.suite is not None, plan_input.board is not None]
    if sum(targets) != 1:
        raise ValueError("provide exactly one of --suite or --board")

    require_file(plan_input.model, "model config")
    model = read_json_object(plan_input.model, "model config")
    model_id = model.get("model_id")
    if not isinstance(model_id, str) or not model_id.strip():
        raise ValueError("model config must contain a non-empty model_id")
    base_url = model.get("base_url")
    if not isinstance(base_url, str) or not base_url.strip():
        raise ValueError("model config must contain a non-empty base_url")

    if plan_input.suite is not None:
        require_file(plan_input.suite, "suite config")
        suite = read_json_object(plan_input.suite, "suite config")
        if not isinstance(suite.get("suite_id"), str) or not str(
            suite["suite_id"]
        ).strip():
            raise ValueError("suite config must contain a non-empty suite_id")

    if plan_input.board is not None:
        require_file(plan_input.board, "board config")
        board = read_json_object(plan_input.board, "board config")
        if not isinstance(board.get("board_id"), str) or not str(
            board["board_id"]
        ).strip():
            raise ValueError("board config must contain a non-empty board_id")
        if not isinstance(board.get("suites"), list) or not board["suites"]:
            raise ValueError("board config must contain a non-empty suites list")

    if plan_input.llm_probe_output is not None:
        require_file(plan_input.llm_probe_output, "LLM-probe output")
        if plan_input.llm_probe_output.suffix.lower() not in {
            ".json",
            ".yaml",
            ".yml",
        }:
            raise ValueError(
                "LLM-probe output extension must be .json, .yaml, or .yml"
            )

    if plan_input.manifest is not None:
        require_file(plan_input.manifest, "preflight manifest")
        validate_manifest(plan_input.manifest)

    require_empty_or_missing_directory(plan_input.out_dir, "audition out-dir")

    if plan_input.write_plan is not None and plan_input.write_plan.exists():
        raise ValueError(
            f"refusing to overwrite existing plan file: {plan_input.write_plan}"
        )

    return model_id.strip()


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "preflight"


def inspection_command(label: str, path: Path) -> PlannedCommand:
    return PlannedCommand(
        label=label,
        command=("python3", "-m", "json.tool", os.fspath(path)),
        notes=("Read-only inspection; confirm content before later write steps.",),
    )


def raw_source_inspection_command(path: Path) -> PlannedCommand:
    return PlannedCommand(
        label="Inspect LLM-probe source evidence",
        command=("sed", "-n", "1,220p", os.fspath(path)),
        notes=(
            "Read-only inspection of operator-supplied source evidence.",
            "The later importer remains responsible for schema validation.",
        ),
    )


def relative_manifest_reference(manifest_path: Path, map_path: Path) -> str:
    return Path(
        os.path.relpath(
            manifest_path.resolve(),
            start=map_path.parent.resolve(),
        )
    ).as_posix()


def manifest_map_write_commands(
    *,
    map_path: Path,
    manifest_path: Path,
    model_id: str,
) -> tuple[PlannedCommand, PlannedCommand]:
    map_payload = {
        "schema_version": "zth.preflight_manifest_map.v0.1",
        "models": {
            model_id: relative_manifest_reference(manifest_path, map_path),
        },
    }
    map_text = json.dumps(map_payload, indent=2, sort_keys=True) + "\n"
    make_parent = PlannedCommand(
        label="Prepare manifest-map directory",
        command=("mkdir", "-p", os.fspath(map_path.parent)),
        writes=(map_path.parent,),
        notes=(
            "Printed for manual execution; the planner does not create this directory.",
        ),
    )
    write_map = PlannedCommand(
        label="Write reviewed board preflight manifest map",
        command=(
            "python3",
            "-c",
            (
                "import pathlib, sys; "
                "handle = pathlib.Path(sys.argv[1]).open("
                "'x', encoding='utf-8'); "
                "handle.write(sys.argv[2]); handle.close()"
            ),
            os.fspath(map_path),
            map_text,
        ),
        writes=(map_path,),
        notes=(
            "This map adapts one reviewed manifest to the board runner's existing contract.",
            "Inspect the map before running the board audition.",
        ),
    )
    return make_parent, write_map


def build_plan(plan_input: PlanInput) -> Plan:
    model_id = validate_inputs(plan_input)
    mode: Literal["single-suite", "board"] = (
        "single-suite" if plan_input.suite is not None else "board"
    )
    target_path = plan_input.suite or plan_input.board
    assert target_path is not None

    commands: list[PlannedCommand] = []
    derived_artifacts: list[Path] = []

    if plan_input.llm_probe_output is not None:
        source_kind: Literal["llm-probe-output", "manifest"] = (
            "llm-probe-output"
        )
        source_path = plan_input.llm_probe_output
        preflight_dir = (
            Path(".work")
            / "llm_probe_preflight"
            / slugify(plan_input.llm_probe_output.stem)
        )
        require_empty_or_missing_directory(
            preflight_dir,
            "derived preflight out-dir",
        )
        manifest_path = preflight_dir / "preflight_capability_manifest.json"
        derived_artifacts.append(preflight_dir)
        commands.append(raw_source_inspection_command(source_path))
    else:
        source_kind = "manifest"
        assert plan_input.manifest is not None
        source_path = plan_input.manifest
        manifest_path = plan_input.manifest
        commands.append(
            inspection_command("Inspect preflight capability manifest", manifest_path)
        )

    commands.append(inspection_command("Inspect model config", plan_input.model))
    commands.append(
        inspection_command(
            "Inspect suite config" if mode == "single-suite" else "Inspect board config",
            target_path,
        )
    )

    if plan_input.llm_probe_output is not None:
        preflight_dir = manifest_path.parent
        commands.append(
            PlannedCommand(
                label="Import LLM-probe output as preflight-only evidence",
                command=(
                    "python3",
                    "local_harness/llm_probe_preflight_ingest.py",
                    "--probe-output",
                    os.fspath(plan_input.llm_probe_output),
                    "--input-format",
                    "auto",
                    "--out-dir",
                    os.fspath(preflight_dir),
                ),
                writes=(preflight_dir,),
                notes=(
                    "This imports evidence only; it does not promote or audition a model.",
                ),
            )
        )
        commands.append(
            inspection_command(
                "Inspect generated preflight capability manifest",
                manifest_path,
            )
        )

    if mode == "single-suite":
        assert plan_input.suite is not None
        commands.append(
            PlannedCommand(
                label="Run the gated single-suite audition after review",
                command=(
                    "python3",
                    "local_harness/run_model_audition.py",
                    "--model",
                    os.fspath(plan_input.model),
                    "--suite",
                    os.fspath(plan_input.suite),
                    "--preflight-manifest",
                    os.fspath(manifest_path),
                    "--out-dir",
                    os.fspath(plan_input.out_dir),
                ),
                writes=(plan_input.out_dir,),
                notes=(
                    "This command calls the configured model endpoint if an operator runs it.",
                    "A preflight pass permits an audition; it does not promote the model.",
                ),
            )
        )
    else:
        assert plan_input.board is not None
        if plan_input.llm_probe_output is not None:
            map_path = manifest_path.parent / "preflight_manifest_map.json"
        else:
            map_path = (
                Path(".work")
                / "llm_probe_preflight"
                / f"{slugify(manifest_path.parent.name or manifest_path.stem)}-board-map"
                / "preflight_manifest_map.json"
            )
        if map_path.exists():
            raise ValueError(
                f"refusing to plan overwrite of existing manifest map: {map_path}"
            )
        derived_artifacts.append(map_path)
        commands.extend(
            manifest_map_write_commands(
                map_path=map_path,
                manifest_path=manifest_path,
                model_id=model_id,
            )
        )
        commands.append(
            inspection_command("Inspect board preflight manifest map", map_path)
        )
        commands.append(
            PlannedCommand(
                label="Run the gated board audition after review",
                command=(
                    "python3",
                    "local_harness/run_model_audition_board.py",
                    "--model",
                    os.fspath(plan_input.model),
                    "--board",
                    os.fspath(plan_input.board),
                    "--preflight-manifest-map",
                    os.fspath(map_path),
                    "--out-dir",
                    os.fspath(plan_input.out_dir),
                ),
                writes=(plan_input.out_dir,),
                notes=(
                    "This command calls the configured model endpoint if an operator runs it.",
                    "Preflight status is a gate, not a board score or promotion signal.",
                ),
            )
        )

    commands.extend(
        (
            PlannedCommand(
                label="Run the focused planner tests",
                command=(
                    "python3",
                    "-m",
                    "pytest",
                    "local_harness/tests/test_preflight_audition_plan.py",
                ),
                notes=("Validation evidence only; this grants no authority.",),
            ),
            PlannedCommand(
                label="Run fast repository health checks",
                command=("python3", "local_harness/repo_health_check.py"),
                notes=("Read-only repository health evidence.",),
            ),
            PlannedCommand(
                label="Run full repository health checks when appropriate",
                command=("python3", "local_harness/repo_health_check.py", "--all"),
                notes=(
                    "This may run the local_harness test suite; it does not approve the results.",
                ),
            ),
        )
    )

    return Plan(
        mode=mode,
        source_kind=source_kind,
        source_path=source_path,
        manifest_path=manifest_path,
        model_path=plan_input.model,
        target_path=target_path,
        out_dir=plan_input.out_dir,
        commands=tuple(commands),
        derived_artifacts=tuple(derived_artifacts),
    )


def render_shell_command(command: PlannedCommand) -> str:
    return shlex.join(command.command)


def plan_to_dict(plan: Plan) -> dict[str, object]:
    return {
        "schema_version": PLAN_CONTRACT_VERSION,
        "mode": plan.mode,
        "source_kind": plan.source_kind,
        "source_evidence": {
            "path": os.fspath(plan.source_path),
            "derived": False,
        },
        "manifest_path": os.fspath(plan.manifest_path),
        "model_path": os.fspath(plan.model_path),
        "target_path": os.fspath(plan.target_path),
        "audition_out_dir": os.fspath(plan.out_dir),
        "derived_artifacts": [
            os.fspath(path) for path in plan.derived_artifacts
        ],
        "commands": [
            {
                "label": command.label,
                "argv": list(command.command),
                "shell": render_shell_command(command),
                "writes": [os.fspath(path) for path in command.writes],
                "notes": list(command.notes),
            }
            for command in plan.commands
        ],
        "safety_notes": list(plan.safety_notes),
    }


def render_json(plan: Plan) -> str:
    return json.dumps(plan_to_dict(plan), indent=2, sort_keys=True) + "\n"


def render_commands(plan: Plan) -> str:
    lines = [
        "# Preflight-to-audition operator plan",
        "# Review each command before running it manually.",
        "#",
    ]
    for note in plan.safety_notes:
        lines.append(f"# SAFETY: {note}")
    for command in plan.commands:
        lines.extend(("", f"# {command.label}"))
        for note in command.notes:
            lines.append(f"# NOTE: {note}")
        lines.append(render_shell_command(command))
    return "\n".join(lines) + "\n"


def render_markdown(plan: Plan) -> str:
    lines = [
        "# Preflight-to-Audition Operator Plan",
        "",
        "Status: draft review material",
        "",
        "This plan distinguishes operator-supplied source evidence from commands",
        "that would derive preflight or audition artifacts. Nothing was executed.",
        "",
        "## Inputs",
        "",
        f"- Mode: `{plan.mode}`",
        f"- Source kind: `{plan.source_kind}`",
        f"- Source evidence: `{plan.source_path}`",
        f"- Expected capability manifest: `{plan.manifest_path}`",
        f"- Model config: `{plan.model_path}`",
        f"- Suite or board config: `{plan.target_path}`",
        f"- Audition output directory: `{plan.out_dir}`",
        "",
        "## Safety Boundaries",
        "",
    ]
    lines.extend(f"- {note}" for note in plan.safety_notes)
    lines.extend(("", "## Planned Commands", ""))
    for index, command in enumerate(plan.commands, start=1):
        lines.extend(
            (
                f"### {index}. {command.label}",
                "",
                "```bash",
                render_shell_command(command),
                "```",
                "",
            )
        )
        if command.writes:
            lines.append(
                "Would write: "
                + ", ".join(f"`{path}`" for path in command.writes)
            )
            lines.append("")
        lines.extend(f"- {note}" for note in command.notes)
        if command.notes:
            lines.append("")
    lines.extend(
        (
            "## Review Decision",
            "",
            "An authorized operator must review source evidence, generated manifests,",
            "gate status, commands, output paths, and endpoint configuration before",
            "running any write or model-calling command.",
            "",
        )
    )
    return "\n".join(lines)


def write_plan_file(path: Path, content: str) -> None:
    if path.exists():
        raise ValueError(f"refusing to overwrite existing plan file: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        handle.write(content)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--llm-probe-output")
    parser.add_argument("--manifest")
    parser.add_argument("--model", required=True)
    parser.add_argument("--suite")
    parser.add_argument("--board")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument(
        "--write-plan",
        help="Explicitly write the Markdown plan to this new file.",
    )
    output_group = parser.add_mutually_exclusive_group()
    output_group.add_argument(
        "--print-commands",
        action="store_true",
        help="Print shell commands with review comments.",
    )
    output_group.add_argument(
        "--json",
        action="store_true",
        help="Print a deterministic machine-readable plan.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    plan_input = PlanInput(
        llm_probe_output=(
            Path(args.llm_probe_output) if args.llm_probe_output else None
        ),
        manifest=Path(args.manifest) if args.manifest else None,
        model=Path(args.model),
        suite=Path(args.suite) if args.suite else None,
        board=Path(args.board) if args.board else None,
        out_dir=Path(args.out_dir),
        write_plan=Path(args.write_plan) if args.write_plan else None,
    )
    try:
        plan = build_plan(plan_input)
        markdown = render_markdown(plan)
        if plan_input.write_plan is not None:
            write_plan_file(plan_input.write_plan, markdown)
        if args.json:
            output = render_json(plan)
        elif args.print_commands:
            output = render_commands(plan)
        else:
            output = markdown
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(output, end="")
    if plan_input.write_plan is not None:
        print(f"\nPlan written: {plan_input.write_plan}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
