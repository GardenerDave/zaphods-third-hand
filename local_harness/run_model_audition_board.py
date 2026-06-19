"""Run one model across multiple audition suites and emit a board capability card."""

from __future__ import annotations

import argparse
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from local_harness.run_model_audition import (
    ApiClient,
    AuditionConfig,
    append_jsonl,
    display_path,
    evaluate_preflight_gate,
    load_json,
    resolve_api_key,
    resolve_cli_path,
    resolve_suite_path,
    run_audition,
    utc_now_iso,
    write_json,
)


@dataclass(frozen=True)
class BoardRunConfig:
    run_id: str
    board_id: str
    board_file: Path
    suite_files: list[Path]
    model_id: str
    base_url: str
    api_key: str
    out_dir: Path
    temperature: float | None = None
    max_tokens: int | None = None
    timeout_seconds: int | None = None
    limit_per_suite: int | None = None
    resume: bool = False
    dry_run: bool = False
    preflight_manifest_map: Path | None = None
    preflight_manifest: Path | None = None
    preflight_lookup_key: str = ""
    allow_missing_preflight_manifest: bool = False
    allow_intermittent_preflight: bool = False
    allow_unknown_preflight: bool = False
    waive_preflight: str | None = None


def resolve_board_suite_path(board_file: Path, maybe_relative: str) -> Path:
    path = Path(maybe_relative)
    if path.is_absolute():
        return path
    return (board_file.parent / path).resolve()


def prepare_board_output_dir(out_dir: Path, *, resume: bool) -> None:
    if out_dir.exists() and any(out_dir.iterdir()) and not resume:
        raise FileExistsError(
            f"out_dir exists and is non-empty: {out_dir}. "
            "Use --resume to skip existing suites."
        )

    (out_dir / "suites").mkdir(parents=True, exist_ok=True)


def resolve_preflight_manifest_from_map(
    *,
    map_file: Path,
    lookup_keys: list[str],
    allow_missing: bool,
) -> tuple[Path | None, str]:
    manifest_map = load_json(map_file)
    if not isinstance(manifest_map, dict):
        raise ValueError(
            "preflight manifest map must contain a JSON object"
        )
    if set(manifest_map) != {"schema_version", "models"}:
        raise ValueError(
            "preflight manifest map must contain only schema_version and models"
        )
    if manifest_map["schema_version"] != "zth.preflight_manifest_map.v0.1":
        raise ValueError("unsupported preflight manifest map schema_version")

    models = manifest_map["models"]
    if not isinstance(models, dict):
        raise ValueError("preflight manifest map models must be a JSON object")
    for key, value in models.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError(
                "preflight manifest map model keys must be non-empty strings"
            )
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                "preflight manifest map paths must be non-empty strings"
            )

    for key in lookup_keys:
        if key in models:
            manifest_path = Path(models[key]).expanduser()
            if not manifest_path.is_absolute():
                manifest_path = map_file.parent / manifest_path
            return manifest_path.resolve(), key

    if allow_missing:
        return None, ""
    raise ValueError(
        "preflight manifest map has no entry for model; tried: "
        + ", ".join(lookup_keys)
    )


def build_board_config_from_args(args: argparse.Namespace) -> BoardRunConfig:
    board_file = resolve_cli_path(args.board)
    board_config = load_json(board_file)
    board_defaults = board_config.get("defaults", {})

    model_config: dict[str, Any] = {}
    model_file: Path | None = None
    if args.model:
        model_file = resolve_cli_path(args.model)
        model_config = load_json(model_file)

    model_id = args.model_id or model_config.get("model_id")
    base_url = args.base_url or model_config.get("base_url")

    if not model_id:
        raise ValueError("--model-id is required unless provided by --model")
    if not base_url:
        raise ValueError("--base-url is required unless provided by --model")
    if not args.preflight_manifest_map and (
        args.allow_missing_preflight_manifest
        or args.allow_intermittent_preflight
        or args.allow_unknown_preflight
        or args.waive_preflight is not None
    ):
        raise ValueError(
            "board preflight override flags require "
            "--preflight-manifest-map"
        )

    suite_files = [
        resolve_board_suite_path(board_file, suite_ref)
        for suite_ref in board_config.get("suites", [])
    ]

    if not suite_files:
        raise ValueError(f"board has no suites: {board_file}")

    preflight_manifest_map: Path | None = None
    preflight_manifest: Path | None = None
    preflight_lookup_key = ""
    if args.preflight_manifest_map:
        preflight_manifest_map = resolve_cli_path(args.preflight_manifest_map)
        lookup_keys = [str(model_id)]
        model_ref = model_config.get("model_ref")
        if isinstance(model_ref, str) and model_ref.strip():
            lookup_keys.append(model_ref.strip())
        if model_file is not None:
            lookup_keys.append(model_file.stem)
        lookup_keys = list(dict.fromkeys(lookup_keys))
        preflight_manifest, preflight_lookup_key = (
            resolve_preflight_manifest_from_map(
                map_file=preflight_manifest_map,
                lookup_keys=lookup_keys,
                allow_missing=bool(args.allow_missing_preflight_manifest),
            )
        )

    return BoardRunConfig(
        run_id=args.run_id or Path(args.out_dir).name,
        board_id=board_config["board_id"],
        board_file=board_file,
        suite_files=suite_files,
        model_id=str(model_id),
        base_url=str(base_url),
        api_key=resolve_api_key(
            explicit_api_key=args.api_key,
            model_config=model_config,
        ),
        out_dir=resolve_cli_path(args.out_dir),
        temperature=(
            float(args.temperature)
            if args.temperature is not None
            else (
                float(board_defaults["temperature"])
                if "temperature" in board_defaults
                else None
            )
        ),
        max_tokens=(
            int(args.max_tokens)
            if args.max_tokens is not None
            else (
                int(board_defaults["max_tokens"])
                if "max_tokens" in board_defaults
                else None
            )
        ),
        timeout_seconds=(
            int(args.timeout_seconds)
            if args.timeout_seconds is not None
            else (
                int(board_defaults["timeout_seconds"])
                if "timeout_seconds" in board_defaults
                else None
            )
        ),
        limit_per_suite=args.limit_per_suite,
        resume=bool(args.resume),
        dry_run=bool(args.dry_run),
        preflight_manifest_map=preflight_manifest_map,
        preflight_manifest=preflight_manifest,
        preflight_lookup_key=preflight_lookup_key,
        allow_missing_preflight_manifest=bool(
            args.allow_missing_preflight_manifest
        ),
        allow_intermittent_preflight=bool(
            args.allow_intermittent_preflight
        ),
        allow_unknown_preflight=bool(args.allow_unknown_preflight),
        waive_preflight=args.waive_preflight,
    )


def write_board_metadata(config: BoardRunConfig) -> None:
    metadata = {
        "run_id": config.run_id,
        "created_at": utc_now_iso(),
        "board_id": config.board_id,
        "board_file": display_path(config.board_file),
        "model_id": config.model_id,
        "base_url": config.base_url,
        "suite_count": len(config.suite_files),
        "suite_files": [display_path(path) for path in config.suite_files],
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
        "timeout_seconds": config.timeout_seconds,
        "runner": "local_harness/run_model_audition_board.py",
    }
    if config.preflight_manifest_map is not None:
        metadata["preflight_manifest_map"] = {
            "path": display_path(config.preflight_manifest_map),
            "selected_manifest": (
                display_path(config.preflight_manifest)
                if config.preflight_manifest is not None
                else ""
            ),
            "lookup_key": config.preflight_lookup_key,
            "missing_manifest_allowed": (
                config.allow_missing_preflight_manifest
            ),
        }

    write_json(config.out_dir / "board_metadata.json", metadata)


def build_suite_audition_config(
    *,
    board_config: BoardRunConfig,
    suite_file: Path,
    suite_out_dir: Path,
) -> AuditionConfig:
    suite_config = load_json(suite_file)
    suite_defaults = suite_config.get("defaults", {})

    temperature = (
        board_config.temperature
        if board_config.temperature is not None
        else float(suite_defaults.get("temperature", 0))
    )
    max_tokens = (
        board_config.max_tokens
        if board_config.max_tokens is not None
        else int(suite_defaults.get("max_tokens", 300))
    )
    timeout_seconds = (
        board_config.timeout_seconds
        if board_config.timeout_seconds is not None
        else int(suite_defaults.get("timeout_seconds", 900))
    )

    suite_id = suite_config["suite_id"]

    return AuditionConfig(
        run_id=f"{board_config.run_id}_{suite_id}",
        model_id=board_config.model_id,
        base_url=board_config.base_url,
        api_key=board_config.api_key,
        suite_id=suite_id,
        suite_file=suite_file,
        prompt_file=resolve_suite_path(suite_file, suite_config["prompt_file"]),
        fixtures_file=resolve_suite_path(suite_file, suite_config["fixtures_file"]),
        scorer_profile=resolve_suite_path(suite_file, suite_config["scorer_profile"]),
        temperature=temperature,
        max_tokens=max_tokens,
        timeout_seconds=timeout_seconds,
        out_dir=suite_out_dir,
        dry_run=board_config.dry_run,
        limit=board_config.limit_per_suite,
        case_id=None,
        resume=board_config.resume,
        preflight_manifest=board_config.preflight_manifest,
        allow_intermittent_preflight=(
            board_config.allow_intermittent_preflight
            if board_config.preflight_manifest is not None
            else False
        ),
        allow_unknown_preflight=(
            board_config.allow_unknown_preflight
            if board_config.preflight_manifest is not None
            else False
        ),
        waive_preflight=(
            board_config.waive_preflight
            if board_config.preflight_manifest is not None
            else None
        ),
    )


def validate_board_preflight_gate(config: BoardRunConfig) -> None:
    if config.preflight_manifest is None:
        return
    first_suite = config.suite_files[0]
    audition_config = build_suite_audition_config(
        board_config=config,
        suite_file=first_suite,
        suite_out_dir=config.out_dir / "suites" / "_preflight_validation",
    )
    evaluate_preflight_gate(audition_config)


def aggregate_board_capability_card(
    *,
    config: BoardRunConfig,
    manifest_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    suite_scores: dict[str, float] = {}
    metric_values: dict[str, list[float]] = {}
    failure_modes: list[str] = []
    total_wall_time = 0.0
    suite_case_medians: list[float] = []

    for row in manifest_rows:
        if row["status"] not in {"completed", "skipped_existing"}:
            failure_modes.append("suite_failed")
            continue

        card_path = config.out_dir / row["capability_card_path"]
        if not card_path.exists():
            failure_modes.append("suite_card_missing")
            continue

        card = load_json(card_path)
        suite_id = str(card["suite_id"])
        suite_scores[suite_id] = float(card.get("overall", 0.0))
        failure_modes.extend(card.get("failure_modes", []))

        for metric_id, value in card.get("metric_averages", {}).items():
            metric_values.setdefault(metric_id, []).append(float(value))

        runtime = card.get("runtime", {})
        total_wall_time += float(runtime.get("total_wall_time_seconds", 0.0))
        suite_case_medians.append(
            float(runtime.get("median_case_wall_time_seconds", 0.0))
        )

    overall = (
        sum(suite_scores.values()) / len(suite_scores)
        if suite_scores
        else 0.0
    )
    metric_averages = {
        metric_id: sum(values) / len(values)
        for metric_id, values in metric_values.items()
    }

    return {
        "board_id": config.board_id,
        "run_id": config.run_id,
        "model_id": config.model_id,
        "overall": overall,
        "suite_scores": suite_scores,
        "metric_averages": metric_averages,
        "failure_modes": sorted(set(failure_modes)),
        "runtime": {
            "total_wall_time_seconds": total_wall_time,
            "median_case_wall_time_seconds": (
                statistics.median(suite_case_medians)
                if suite_case_medians
                else 0.0
            ),
        },
        "role_fit": {
            "status": "not_evaluated",
            "note": "Role eligibility is derived by later MTNG/ZTH policy layers.",
        },
    }


def board_capability_card_markdown(card: dict[str, Any]) -> str:
    lines = [
        f"# Model Audition Board Capability Card: {card['run_id']}",
        "",
        f"- Model: `{card['model_id']}`",
        f"- Board: `{card['board_id']}`",
        f"- Overall: {card['overall']:.3f}",
        "",
        "## Suite scores",
        "",
        "| Suite | Overall |",
        "|---|---:|",
    ]

    for suite_id, value in sorted(card.get("suite_scores", {}).items()):
        lines.append(f"| {suite_id} | {value:.3f} |")

    lines.extend(
        [
            "",
            "## Metric averages",
            "",
            "| Metric | Average |",
            "|---|---:|",
        ]
    )

    for metric_id, value in sorted(card.get("metric_averages", {}).items()):
        lines.append(f"| {metric_id} | {value:.3f} |")

    lines.extend(["", "## Failure modes", ""])

    failure_modes = card.get("failure_modes", [])
    if failure_modes:
        for mode in failure_modes:
            lines.append(f"- {mode}")
    else:
        lines.append("None recorded.")

    lines.extend(
        [
            "",
            "## Runtime",
            "",
            f"- Total wall time seconds: {card['runtime']['total_wall_time_seconds']:.3f}",
            "- Median case wall time seconds: "
            f"{card['runtime']['median_case_wall_time_seconds']:.3f}",
            "",
            "## Role fit",
            "",
            f"- Status: {card['role_fit']['status']}",
            f"- Note: {card['role_fit']['note']}",
            "",
        ]
    )

    return "\n".join(lines)


def run_board(
    config: BoardRunConfig,
    *,
    client: ApiClient | None = None,
) -> dict[str, Any]:
    validate_board_preflight_gate(config)
    prepare_board_output_dir(config.out_dir, resume=config.resume)
    write_board_metadata(config)

    manifest_path = config.out_dir / "board_manifest.jsonl"
    manifest_rows: list[dict[str, Any]] = []

    for suite_file in config.suite_files:
        suite_config = load_json(suite_file)
        suite_id = suite_config["suite_id"]
        suite_out_dir = config.out_dir / "suites" / suite_id
        capability_card_path = suite_out_dir / "capability_card.json"

        status = "completed"
        overall = 0.0
        error = ""

        try:
            if config.resume and capability_card_path.exists():
                status = "skipped_existing"
                suite_card = load_json(capability_card_path)
            else:
                audition_config = build_suite_audition_config(
                    board_config=config,
                    suite_file=suite_file,
                    suite_out_dir=suite_out_dir,
                )
                suite_card = run_audition(audition_config, client=client)

            overall = float(suite_card.get("overall", 0.0))
        except Exception as exc:
            status = "failed"
            error = str(exc)

        row = {
            "suite_id": suite_id,
            "status": status,
            "suite_out_dir": display_path(suite_out_dir, cwd=config.out_dir),
            "capability_card_path": display_path(
                capability_card_path,
                cwd=config.out_dir,
            ),
            "overall": overall,
            "error": error,
            "timestamp": utc_now_iso(),
        }
        append_jsonl(manifest_path, row)
        manifest_rows.append(row)

    card = aggregate_board_capability_card(
        config=config,
        manifest_rows=manifest_rows,
    )

    write_json(config.out_dir / "board_capability_card.json", card)
    (config.out_dir / "board_capability_card.md").write_text(
        board_capability_card_markdown(card),
        encoding="utf-8",
    )

    return card


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument("--model")
    parser.add_argument("--model-id")
    parser.add_argument("--base-url")
    parser.add_argument("--api-key")
    parser.add_argument("--board", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--run-id")
    parser.add_argument("--temperature", type=float)
    parser.add_argument("--max-tokens", type=int)
    parser.add_argument("--timeout-seconds", type=int)
    parser.add_argument("--limit-per-suite", type=int)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--preflight-manifest-map",
        help=(
            "Optional zth.preflight_manifest_map.v0.1 JSON file used to "
            "select a manifest for this board model."
        ),
    )
    parser.add_argument(
        "--allow-missing-preflight-manifest",
        action="store_true",
        help=(
            "Allow a model missing from a provided manifest map to run "
            "without preflight gating."
        ),
    )
    parser.add_argument(
        "--allow-intermittent-preflight",
        action="store_true",
        help="Pass the intermittent-status override to gated suite auditions.",
    )
    parser.add_argument(
        "--allow-unknown-preflight",
        action="store_true",
        help="Pass the unknown-status override to gated suite auditions.",
    )
    parser.add_argument(
        "--waive-preflight",
        help="Human-readable waiver passed to every gated suite audition.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        config = build_board_config_from_args(args)
        run_board(config)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
