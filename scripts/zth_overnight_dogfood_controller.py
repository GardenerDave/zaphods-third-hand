#!/usr/bin/env python3
from __future__ import annotations

import csv
import datetime as dt
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo

REPO = Path(os.environ.get("ZTH_REPO", Path(__file__).resolve().parents[1]))
WORK = REPO / ".work" / "dogfood" / "overnight"
QUEUE = REPO / ".work" / "dogfood" / "roadmap_queue.tsv"
STATE = WORK / "state.tsv"
STATUS_FILE = WORK / "status.json"
LOCK = WORK / "controller.lock"
TERMINAL_STATE = WORK / "terminal_state.json"
TERMINAL_LOCK = WORK / "terminal.lock"
CLOSEOUT_MANIFEST = WORK / "manifests" / "overnight_run_manifest.json"
RUNS_DIR = WORK / "runs"
LOG_DIR = WORK / "logs"
MANIFEST_DIR = WORK / "manifests"
DEFAULT_DEADLINE = dt.datetime(2026, 7, 19, 8, 0, tzinfo=ZoneInfo("America/New_York"))
MAX_STAGES = 3
MAX_MODEL_ATTEMPTS = 3
RUN_ID = dt.datetime.now(tz=ZoneInfo("America/New_York")).strftime("%Y%m%d_%H%M%S")


def load_env() -> None:
    env = REPO / ".env.local"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("export "):
                line = line[7:] if line.startswith("export ") else line
            if "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())
    os.environ.setdefault("ZTH_PUBLIC_HOST_ALIAS", "JARVIS_LOCAL")
    os.environ.setdefault("ZTH_MODEL_ID", "Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf")


def ensure_dirs() -> None:
    for path in [WORK, LOG_DIR, MANIFEST_DIR, RUNS_DIR]:
        path.mkdir(parents=True, exist_ok=True)
    STATE.touch(exist_ok=True)


def now() -> dt.datetime:
    return dt.datetime.now(tz=ZoneInfo("America/New_York"))


def deadline() -> dt.datetime:
    override = os.environ.get("ZTH_OVERNIGHT_DEADLINE")
    if override:
        return dt.datetime.fromisoformat(override)
    return DEFAULT_DEADLINE


def record(row: list[str]) -> None:
    with STATE.open("a", encoding="utf-8") as fh:
        fh.write("\t".join(row) + "\n")


def read_rows() -> list[list[str]]:
    if not STATE.exists():
        return []
    rows = []
    with STATE.open(encoding="utf-8") as fh:
        for row in csv.reader(fh, delimiter="\t"):
            if row:
                rows.append(row)
    return rows


def latest_stage_states() -> dict[str, dict[str, str]]:
    latest: dict[str, dict[str, str]] = {}
    for row in read_rows():
        if len(row) < 5:
            continue
        latest[row[1]] = {"event": row[2], "state": row[4], "timestamp": row[-1] if row else ""}
    return latest


def is_terminal() -> bool:
    return TERMINAL_STATE.exists()


def next_queue_stage() -> tuple[str, str, str] | None:
    if is_terminal():
        return None
    done = set(latest_stage_states())
    with QUEUE.open(encoding="utf-8") as fh:
        for row in csv.reader(fh, delimiter="\t"):
            if not row or row[0].startswith("#") or len(row) < 3:
                continue
            if row[1] not in done:
                return row[0], row[1], row[2]
    return None


def packet_for_stage(slug: str, title: str, desc: str, deadline_reached: bool) -> str:
    return "\n".join(
        [
            "# ZTH Overnight Dogfood Packet",
            "",
            f"Run ID: {RUN_ID}",
            f"Slug: {slug}",
            f"Title: {title}",
            "",
            "## Objective",
            "",
            desc,
            "",
            "## Controller Facts",
            "",
            json.dumps({"deadline_reached": deadline_reached}),
            "",
            "## Authority Boundary",
            "",
            "- Inspect repository evidence only.",
            "- Do not expand authority.",
            "- Do not push, merge, deploy, or modify secrets.",
            "",
            "## Allowed Targets",
            "",
            "- Existing repository files only.",
            "- Stage-local evidence under .work/dogfood/overnight/.",
            "",
            "## Verification Contract",
            "",
            "- Return exact JSON.",
            "- Use the fixed schema.",
            "",
            "Return strict JSON with keys: verdict, review_state, changed_paths, verification, evidence, notes.",
        ]
    )


def stage_dir(slug: str) -> Path:
    return RUNS_DIR / f"{RUN_ID}-{slug}"


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _transport_diag(exc: BaseException, *, attempt: int, retryable: bool, body: str | None = None, http_status: int | None = None) -> dict:
    diag = {
        "attempt": attempt,
        "exception_type": type(exc).__name__,
        "http_status": http_status,
        "response_excerpt": body[:512] if body else None,
        "stderr": str(getattr(exc, "reason", exc)),
        "timestamp": now().isoformat(),
        "endpoint_alias": os.environ.get("ZTH_PUBLIC_HOST_ALIAS", "JARVIS_LOCAL"),
        "retryable": retryable,
        "retryable_reason": "transport" if retryable else "non_retryable",
    }
    if isinstance(exc, urllib.error.HTTPError):
        diag["http_status"] = exc.code
        diag["stderr"] = str(exc.reason)
    return diag


def call_model(packet_path: Path, out_path: Path) -> dict:
    fixture = os.environ.get("ZTH_OVERNIGHT_MODEL_RESPONSE_FILE")
    if fixture:
        data = json.loads(Path(fixture).read_text(encoding="utf-8"))
        out_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        return data
    base_url = os.environ["ZTH_JARVIS_BASE_URL"]
    model = os.environ["ZTH_MODEL_ID"]
    packet = packet_path.read_text(encoding="utf-8")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Return valid JSON only."},
            {"role": "user", "content": packet},
        ],
        "temperature": 0.1,
        "max_tokens": 1600,
    }
    req = urllib.request.Request(
        base_url.rstrip("/") + "/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=1200) as resp:
        data = json.loads(resp.read().decode())
    out_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return data


def classify_output(content_path: Path, deadline_reached: bool, allow_paths: list[str]) -> tuple[str, list[str], dict]:
    validator = REPO / "scripts" / "zth_validate_overnight_review_output.py"
    proc = subprocess.run(
        [sys.executable, str(validator), str(content_path), "true" if deadline_reached else "false", *allow_paths],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
    )
    payload = json.loads(proc.stdout or "{}")
    state = payload.get("state", "semantic_validation_failed")
    return state, payload.get("errors", []), {"stdout": proc.stdout, "stderr": proc.stderr, "returncode": proc.returncode}


def queue_allowlist() -> list[str]:
    allow = []
    if QUEUE.exists():
        with QUEUE.open(encoding="utf-8") as fh:
            for row in csv.reader(fh, delimiter="\t"):
                if not row or row[0].startswith("#") or len(row) < 3:
                    continue
                allow.append(f".work/dogfood/overnight/runs/{row[0]}-{row[1]}")
    return allow


def write_terminal_marker_once() -> None:
    with open(TERMINAL_LOCK, "w", encoding="utf-8") as lock:
        try:
            import fcntl
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except Exception:
            return
        if TERMINAL_STATE.exists():
            return
        rows = read_rows()
        unique: dict[str, list[str]] = {}
        for row in rows:
            if len(row) >= 5:
                unique[row[1]] = row
        latest = rows[-1] if rows else []
        summary = {
            "terminal_state": "queue_exhausted",
            "closed_at": now().isoformat(),
            "attempted_unique_stages": len(unique),
            "completed_stages": sum(1 for row in unique.values() if len(row) >= 5 and row[4] == "ready_for_review"),
            "blocked_stages": sum(1 for row in unique.values() if len(row) >= 5 and row[4] == "blocked"),
            "queue_remaining": 0,
            "queue_exhausted": True,
            "deadline_reached": now() >= deadline(),
            "latest_stage": latest[1] if latest else None,
        }
        _write_json(TERMINAL_STATE, summary)
        if not CLOSEOUT_MANIFEST.exists():
            _write_json(CLOSEOUT_MANIFEST, summary)
        record([RUN_ID, "queue_exhausted", "terminal", str(WORK), "queue_exhausted", summary["closed_at"]])


def run_stage(slug: str, title: str, desc: str, dry_run: bool) -> int:
    if dry_run:
        print(f"{slug}\t{title}\tdry-run")
        return 0
    d = stage_dir(slug)
    d.mkdir(parents=True, exist_ok=True)
    packet = packet_for_stage(slug, title, desc, deadline_reached=now() >= deadline())
    packet_path = d / "stage_packet.md"
    packet_path.write_text(packet, encoding="utf-8")
    record([RUN_ID, slug, "started", str(d), "started", now().isoformat()])
    for attempt in range(1, MAX_MODEL_ATTEMPTS + 1):
        record([RUN_ID, slug, "model_call_attempted", str(d), "model_call_attempted", now().isoformat()])
        raw = d / f"model_output.raw.{attempt}.json"
        err = d / f"model_call.{attempt}.error"
        try:
            response = call_model(packet_path, raw)
            if isinstance(response, dict):
                record([RUN_ID, slug, "model_output_captured", str(d), "model_output_captured", now().isoformat()])
            else:
                raise ValueError("unexpected model response envelope")
        except urllib.error.HTTPError as exc:
            err.write_text(json.dumps(_transport_diag(exc, attempt=attempt, retryable=True, body=exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else None), indent=2) + "\n", encoding="utf-8")
            continue
        except urllib.error.URLError as exc:
            err.write_text(json.dumps(_transport_diag(exc, attempt=attempt, retryable=True), indent=2) + "\n", encoding="utf-8")
            continue
        except TimeoutError as exc:
            err.write_text(json.dumps(_transport_diag(exc, attempt=attempt, retryable=True), indent=2) + "\n", encoding="utf-8")
            continue
        except Exception as exc:
            err.write_text(json.dumps(_transport_diag(exc, attempt=attempt, retryable=False), indent=2) + "\n", encoding="utf-8")
            continue
        try:
            content = json.loads(raw.read_text(encoding="utf-8"))["choices"][0]["message"]["content"]
        except Exception as exc:
            err.write_text(json.dumps(_transport_diag(exc, attempt=attempt, retryable=False), indent=2) + "\n", encoding="utf-8")
            record([RUN_ID, slug, "structure_validation_failed", str(d), "structure_validation_failed", now().isoformat()])
            continue
        content_path = d / f"model_content.{attempt}.json"
        content_path.write_text(content, encoding="utf-8")
        try:
            json.loads(content)
        except json.JSONDecodeError as exc:
            err.write_text(json.dumps(_transport_diag(exc, attempt=attempt, retryable=False), indent=2) + "\n", encoding="utf-8")
            record([RUN_ID, slug, "structure_validation_failed", str(d), "structure_validation_failed", now().isoformat()])
            continue
        record([RUN_ID, slug, "structure_valid", str(d), "structure_valid", now().isoformat()])
        state, errors, validation = classify_output(content_path, deadline_reached=now() >= deadline(), allow_paths=queue_allowlist())
        _write_json(d / f"validation.{attempt}.json", {"state": state, "errors": errors, "validation": validation})
        if state == "semantic_validation_failed":
            record([RUN_ID, slug, "semantic_validation_failed", str(d), "semantic_validation_failed", now().isoformat()])
        if state == "ready_for_review":
            (d / "model_output.raw.json").write_text(raw.read_text(encoding="utf-8"), encoding="utf-8")
            (d / "model_content.json").write_text(content, encoding="utf-8")
            record([RUN_ID, slug, "semantic_validation_passed", str(d), "semantic_validation_passed", now().isoformat()])
            record([RUN_ID, slug, "ready_for_review", str(d), "ready_for_review", now().isoformat()])
            return 0
        if state == "structure_valid":
            record([RUN_ID, slug, "structure_validation_failed", str(d), "structure_validation_failed", now().isoformat()])
    record([RUN_ID, slug, "blocked", str(d), "blocked", now().isoformat()])
    return 1


def status_payload() -> dict:
    rows = read_rows()
    latest = latest_stage_states()
    queue_ids = []
    if QUEUE.exists():
        with QUEUE.open(encoding="utf-8") as fh:
            for row in csv.reader(fh, delimiter="\t"):
                if row and not row[0].startswith("#") and len(row) >= 2:
                    queue_ids.append(row[1])
    attempted = {stage for stage in latest if stage in queue_ids}
    completed = sum(1 for s in attempted if latest[s]["state"] == "ready_for_review")
    blocked = sum(1 for s in attempted if latest[s]["state"] == "blocked")
    semantic_failed = sum(1 for s in attempted if latest[s]["state"] == "semantic_validation_failed")
    ready = completed
    terminal = TERMINAL_STATE.exists()
    queue_total = len(queue_ids)
    queue_remaining = max(queue_total - len(attempted), 0)
    payload = {
        "deadline_local": deadline().isoformat(),
        "attempted_unique_stages": len(attempted),
        "queue_stage_total": queue_total,
        "queue_stages_attempted": len(attempted),
        "queue_stages_ready_for_review": ready,
        "queue_stages_failed_semantic_validation": semantic_failed,
        "queue_stages_blocked": blocked,
        "queue_stages_unresolved": sum(1 for s in attempted if latest[s]["state"] not in {"ready_for_review", "blocked", "semantic_validation_failed"}),
        "queue_path": str(QUEUE),
        "state_path": str(STATE),
        "completed_stages": completed,
        "blocked_stages": blocked,
        "semantic_validation_failures": semantic_failed,
        "ready_for_review_count": ready,
        "unresolved_count": sum(1 for s in attempted if latest[s]["state"] not in {"ready_for_review", "blocked", "semantic_validation_failed"}),
        "queue_remaining": 0 if terminal else queue_remaining,
        "queue_exhausted": terminal,
        "deadline_reached": now() >= deadline(),
        "terminal_run_state": json.loads(TERMINAL_STATE.read_text(encoding="utf-8"))["terminal_state"] if terminal else None,
        "latest_stage": rows[-1][1] if rows else None,
        "latest_transition_time": rows[-1][-1] if rows else None,
        "working_tree_state": subprocess.run(["git", "status", "--short", "--untracked-files=all"], cwd=REPO, text=True, capture_output=True).stdout.strip() or "clean",
        "closeout_path": str(CLOSEOUT_MANIFEST) if CLOSEOUT_MANIFEST.exists() else None,
    }
    _write_json(STATUS_FILE, payload)
    return payload


def main(argv: list[str]) -> int:
    mode = argv[1] if len(argv) > 1 else "--tick"
    ensure_dirs()
    if mode == "--status":
        print(json.dumps(status_payload(), indent=2))
        return 0
    if mode not in {"--tick", "--dry-run"}:
        print("usage: --tick|--dry-run|--status", file=sys.stderr)
        return 2
    if mode != "--dry-run":
        load_env()
    if mode == "--tick" and now() >= deadline():
        print("deadline reached before new work")
        print(json.dumps(status_payload(), indent=2))
        return 0
    import fcntl
    with open(LOCK, "w", encoding="utf-8") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 0
        if is_terminal():
            print(json.dumps(status_payload(), indent=2))
            return 0
        for _ in range(MAX_STAGES):
            if now() >= deadline():
                break
            nxt = next_queue_stage()
            if nxt is None:
                write_terminal_marker_once()
                break
            _, slug, title = nxt
            rc = run_stage(slug, title, title, dry_run=(mode == "--dry-run"))
            if rc != 0:
                continue
        print(json.dumps(status_payload(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
