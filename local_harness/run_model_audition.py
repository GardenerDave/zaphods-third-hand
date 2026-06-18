"""Generic model audition runner for Zaphod's Third Hand."""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from local_harness.model_audition_scorers import score_case

ApiClient = Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class AuditionConfig:
    run_id: str
    model_id: str
    base_url: str
    api_key: str
    suite_id: str
    suite_file: Path
    prompt_file: Path
    fixtures_file: Path
    scorer_profile: Path
    temperature: float
    max_tokens: int
    timeout_seconds: int
    out_dir: Path
    dry_run: bool = False
    limit: int | None = None
    case_id: str | None = None
    resume: bool = False


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def display_path(path: Path, *, cwd: Path | None = None) -> str:
    cwd = cwd or Path.cwd()
    try:
        return path.resolve().relative_to(cwd.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def resolve_suite_path(suite_file: Path, maybe_relative: str) -> Path:
    path = Path(maybe_relative)
    if path.is_absolute():
        return path
    return (suite_file.parent / path).resolve()


def resolve_cli_path(maybe_relative: str) -> Path:
    return Path(maybe_relative).expanduser().resolve()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue

            row = json.loads(stripped)

            for required in ("case_id", "task_type", "input"):
                if required not in row:
                    raise ValueError(
                        f"{path}:{line_number} missing required field {required!r}"
                    )

            rows.append(row)

    return rows


def render_prompt(template: str, fixture: dict[str, Any]) -> str:
    replacements = {
        "{{case_id}}": str(fixture.get("case_id", "")),
        "{{task_type}}": str(fixture.get("task_type", "")),
        "{{input}}": str(fixture.get("input", "")),
        "{{expected_schema}}": json.dumps(
            fixture.get("expected_schema", {}),
            indent=2,
            sort_keys=True,
        ),
        "{{expected_json}}": json.dumps(
            fixture.get("expected", {}),
            indent=2,
            sort_keys=True,
        ),
        "{{metadata_json}}": json.dumps(
            fixture.get("metadata", {}),
            indent=2,
            sort_keys=True,
        ),
    }

    rendered = template
    for needle, value in replacements.items():
        rendered = rendered.replace(needle, value)

    return rendered


def extract_text_from_response(response: dict[str, Any]) -> str:
    try:
        choices = response.get("choices", [])
        if not choices:
            return ""

        message = choices[0].get("message", {})
        content = message.get("content", "")

        if isinstance(content, str):
            return content

        return json.dumps(content, sort_keys=True)
    except AttributeError:
        return ""


def default_chat_completion_client(
    request_body: dict[str, Any],
    runtime_config: dict[str, Any],
) -> dict[str, Any]:
    base_url = str(runtime_config["base_url"]).rstrip("/")
    url = f"{base_url}/chat/completions"
    api_key = runtime_config.get("api_key") or ""
    timeout_seconds = float(runtime_config["timeout_seconds"])

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    request = urllib.request.Request(
        url,
        data=json.dumps(request_body).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        payload = response.read().decode("utf-8")

    return json.loads(payload)


def resolve_api_key(
    *,
    explicit_api_key: str | None,
    model_config: dict[str, Any],
) -> str:
    if explicit_api_key:
        return explicit_api_key

    api_key_env = model_config.get("api_key_env")
    if api_key_env:
        env_value = os.environ.get(str(api_key_env))
        if env_value:
            return env_value

    return str(model_config.get("api_key_default", ""))


def build_config_from_args(args: argparse.Namespace) -> AuditionConfig:
    suite_file = resolve_cli_path(args.suite)
    suite_config = load_json(suite_file)
    defaults = suite_config.get("defaults", {})

    model_config: dict[str, Any] = {}
    if args.model:
        model_config = load_json(resolve_cli_path(args.model))

    model_id = args.model_id or model_config.get("model_id")
    base_url = args.base_url or model_config.get("base_url")

    if not model_id:
        raise ValueError("--model-id is required unless provided by --model")
    if not base_url:
        raise ValueError("--base-url is required unless provided by --model")

    prompt_file = (
        resolve_cli_path(args.prompt_file)
        if args.prompt_file
        else resolve_suite_path(suite_file, suite_config["prompt_file"])
    )
    fixtures_file = (
        resolve_cli_path(args.fixtures_file)
        if args.fixtures_file
        else resolve_suite_path(suite_file, suite_config["fixtures_file"])
    )
    scorer_profile = (
        resolve_cli_path(args.scorer_profile)
        if args.scorer_profile
        else resolve_suite_path(suite_file, suite_config["scorer_profile"])
    )

    run_id = args.run_id or Path(args.out_dir).name

    return AuditionConfig(
        run_id=run_id,
        model_id=str(model_id),
        base_url=str(base_url),
        api_key=resolve_api_key(
            explicit_api_key=args.api_key,
            model_config=model_config,
        ),
        suite_id=suite_config["suite_id"],
        suite_file=suite_file,
        prompt_file=prompt_file,
        fixtures_file=fixtures_file,
        scorer_profile=scorer_profile,
        temperature=float(
            args.temperature
            if args.temperature is not None
            else defaults.get("temperature", 0)
        ),
        max_tokens=int(
            args.max_tokens
            if args.max_tokens is not None
            else defaults.get("max_tokens", 300)
        ),
        timeout_seconds=int(
            args.timeout_seconds
            if args.timeout_seconds is not None
            else defaults.get("timeout_seconds", 900)
        ),
        out_dir=resolve_cli_path(args.out_dir),
        dry_run=bool(args.dry_run),
        limit=args.limit,
        case_id=args.case_id,
        resume=bool(args.resume),
    )


def prepare_output_dir(out_dir: Path, *, resume: bool) -> None:
    if out_dir.exists() and any(out_dir.iterdir()) and not resume:
        raise FileExistsError(
            f"out_dir exists and is non-empty: {out_dir}. "
            "Use --resume to skip existing cases."
        )

    (out_dir / "raw_outputs").mkdir(parents=True, exist_ok=True)
    (out_dir / "rendered_prompts").mkdir(parents=True, exist_ok=True)
    (out_dir / "scores").mkdir(parents=True, exist_ok=True)


def write_run_metadata(config: AuditionConfig) -> None:
    metadata = {
        "run_id": config.run_id,
        "created_at": utc_now_iso(),
        "model_id": config.model_id,
        "base_url": config.base_url,
        "suite_id": config.suite_id,
        "suite_file": display_path(config.suite_file),
        "prompt_file": display_path(config.prompt_file),
        "fixtures_file": display_path(config.fixtures_file),
        "scorer_profile": display_path(config.scorer_profile),
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
        "timeout_seconds": config.timeout_seconds,
        "runner": "local_harness/run_model_audition.py",
    }

    write_json(config.out_dir / "run_metadata.json", metadata)


def request_body_for_case(config: AuditionConfig, rendered_prompt: str) -> dict[str, Any]:
    return {
        "model": config.model_id,
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
        "messages": [{"role": "user", "content": rendered_prompt}],
    }


def dry_run_response(fixture: dict[str, Any]) -> dict[str, Any]:
    expected = fixture.get("expected")
    content = json.dumps(expected if isinstance(expected, dict) else {}, sort_keys=True)

    return {
        "choices": [{"message": {"content": content}}],
        "dry_run": True,
    }


def run_single_case(
    *,
    config: AuditionConfig,
    fixture: dict[str, Any],
    prompt_template: str,
    scorer_profile: dict[str, Any],
    client: ApiClient | None = None,
) -> dict[str, Any]:
    case_id = str(fixture["case_id"])

    raw_output_path = config.out_dir / "raw_outputs" / f"{case_id}.json"
    rendered_prompt_path = config.out_dir / "rendered_prompts" / f"{case_id}.md"
    score_path = config.out_dir / "scores" / f"{case_id}.json"

    if config.resume and score_path.exists():
        return {
            "case_id": case_id,
            "task_type": fixture.get("task_type", ""),
            "status": "skipped_existing",
            "raw_output_path": display_path(raw_output_path, cwd=config.out_dir),
            "score_path": display_path(score_path, cwd=config.out_dir),
            "wall_time_seconds": 0.0,
            "error": "",
            "timestamp": utc_now_iso(),
        }

    rendered_prompt = render_prompt(prompt_template, fixture)
    rendered_prompt_path.write_text(rendered_prompt, encoding="utf-8")

    request_body = request_body_for_case(config, rendered_prompt)
    runtime_config = {
        "base_url": config.base_url,
        "api_key": config.api_key,
        "timeout_seconds": config.timeout_seconds,
    }

    start = time.monotonic()
    status = "completed"
    error = ""
    response: dict[str, Any] = {}
    model_text = ""

    try:
        if config.dry_run:
            response = dry_run_response(fixture)
        else:
            call_client = client or default_chat_completion_client
            response = call_client(request_body, runtime_config)

        model_text = extract_text_from_response(response)
    except TimeoutError as exc:
        status = "timeout"
        error = str(exc)
    except urllib.error.URLError as exc:
        status = "api_error"
        error = str(exc)
    except Exception as exc:
        status = "api_error"
        error = str(exc)

    wall_time_seconds = round(time.monotonic() - start, 6)

    raw_output = {
        "case_id": case_id,
        "request": {
            "model": config.model_id,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
        },
        "response": {"full_api_response": response},
        "text": model_text,
        "wall_time_seconds": wall_time_seconds,
    }
    write_json(raw_output_path, raw_output)

    if status == "completed":
        try:
            score = score_case(
                fixture=fixture,
                model_text=model_text,
                scorer_profile=scorer_profile,
                runtime={"wall_time_seconds": wall_time_seconds},
            )
            write_json(score_path, score)
        except Exception as exc:
            status = "scoring_error"
            error = str(exc)
            write_json(
                score_path,
                {
                    "case_id": case_id,
                    "overall": 0.0,
                    "metrics": {},
                    "failure_modes": ["scoring_error"],
                    "error": error,
                },
            )
    else:
        write_json(
            score_path,
            {
                "case_id": case_id,
                "overall": 0.0,
                "metrics": {},
                "failure_modes": [status],
                "error": error,
            },
        )

    return {
        "case_id": case_id,
        "task_type": fixture.get("task_type", ""),
        "status": status,
        "raw_output_path": display_path(raw_output_path, cwd=config.out_dir),
        "score_path": display_path(score_path, cwd=config.out_dir),
        "wall_time_seconds": wall_time_seconds,
        "error": error,
        "timestamp": utc_now_iso(),
    }


def filter_fixtures(
    fixtures: list[dict[str, Any]],
    *,
    case_id: str | None,
    limit: int | None,
) -> list[dict[str, Any]]:
    selected = [
        fixture for fixture in fixtures if case_id in (None, fixture["case_id"])
    ]

    if limit is not None:
        selected = selected[:limit]

    return selected


def aggregate_capability_card(
    *,
    config: AuditionConfig,
    manifest_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    scores: list[dict[str, Any]] = []
    failure_modes: list[str] = []
    wall_times: list[float] = []
    metric_values: dict[str, list[float]] = {}

    for row in manifest_rows:
        score_path = config.out_dir / row["score_path"]
        if not score_path.exists():
            continue

        score = load_json(score_path)
        scores.append(score)
        failure_modes.extend(score.get("failure_modes", []))

        for metric_id, metric in score.get("metrics", {}).items():
            metric_values.setdefault(metric_id, []).append(
                float(metric.get("score", 0.0))
            )

        wall_time = float(row.get("wall_time_seconds") or 0.0)
        if row["status"] != "skipped_existing":
            wall_times.append(wall_time)

    completed_count = sum(
        1
        for row in manifest_rows
        if row["status"] in {"completed", "skipped_existing"}
    )
    failed_count = sum(
        1
        for row in manifest_rows
        if row["status"] not in {"completed", "skipped_existing"}
    )

    overall = (
        sum(float(score.get("overall", 0.0)) for score in scores) / len(scores)
        if scores
        else 0.0
    )
    metric_averages = {
        metric_id: sum(values) / len(values)
        for metric_id, values in metric_values.items()
    }

    return {
        "run_id": config.run_id,
        "model_id": config.model_id,
        "suite_id": config.suite_id,
        "overall": overall,
        "case_count": len(manifest_rows),
        "completed_count": completed_count,
        "failed_count": failed_count,
        "metric_averages": metric_averages,
        "failure_modes": sorted(set(failure_modes)),
        "runtime": {
            "total_wall_time_seconds": sum(wall_times),
            "median_case_wall_time_seconds": (
                statistics.median(wall_times) if wall_times else 0.0
            ),
        },
    }


def capability_card_markdown(card: dict[str, Any]) -> str:
    lines = [
        f"# Model Audition Capability Card: {card['run_id']}",
        "",
        f"- Model: `{card['model_id']}`",
        f"- Suite: `{card['suite_id']}`",
        f"- Overall: {card['overall']:.3f}",
        f"- Cases: {card['case_count']}",
        f"- Completed: {card['completed_count']}",
        f"- Failed: {card['failed_count']}",
        "",
        "## Metric averages",
        "",
    ]

    for metric_id, value in sorted(card.get("metric_averages", {}).items()):
        lines.append(f"- {metric_id}: {value:.3f}")

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
        ]
    )

    return "\n".join(lines)


def run_audition(
    config: AuditionConfig,
    *,
    client: ApiClient | None = None,
) -> dict[str, Any]:
    prepare_output_dir(config.out_dir, resume=config.resume)
    write_run_metadata(config)

    prompt_template = config.prompt_file.read_text(encoding="utf-8")
    scorer_profile = load_json(config.scorer_profile)
    fixtures = filter_fixtures(
        load_jsonl(config.fixtures_file),
        case_id=config.case_id,
        limit=config.limit,
    )

    manifest_path = config.out_dir / "case_manifest.jsonl"
    manifest_rows: list[dict[str, Any]] = []

    for fixture in fixtures:
        row = run_single_case(
            config=config,
            fixture=fixture,
            prompt_template=prompt_template,
            scorer_profile=scorer_profile,
            client=client,
        )
        append_jsonl(manifest_path, row)
        manifest_rows.append(row)

    card = aggregate_capability_card(config=config, manifest_rows=manifest_rows)

    write_json(config.out_dir / "capability_card.json", card)
    (config.out_dir / "capability_card.md").write_text(
        capability_card_markdown(card),
        encoding="utf-8",
    )

    return card


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument("--model")
    parser.add_argument("--model-id")
    parser.add_argument("--base-url")
    parser.add_argument("--suite", required=True)
    parser.add_argument("--out-dir", required=True)

    parser.add_argument("--api-key")
    parser.add_argument("--prompt-file")
    parser.add_argument("--fixtures-file")
    parser.add_argument("--scorer-profile")
    parser.add_argument("--temperature", type=float)
    parser.add_argument("--max-tokens", type=int)
    parser.add_argument("--timeout-seconds", type=int)
    parser.add_argument("--run-id")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--case-id")
    parser.add_argument("--resume", action="store_true")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        config = build_config_from_args(args)
        run_audition(config)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
