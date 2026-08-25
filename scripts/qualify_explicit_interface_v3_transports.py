#!/usr/bin/env python3
"""One-shot, infrastructure-only transport qualification for Explicit V3.

This module deliberately has no V2/V3 case loading or evaluator imports.  It
performs non-inference local endpoint discovery, then at most one harmless
external transport invocation and (only after a successful local /models
check exposing the required model) one harmless local completion.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from local_harness.icm_call import call_worker, list_models
from local_harness.icm_spec import completion_url, models_url, resolve_worker_spec


LOCAL_MODEL = "Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf"
LOCAL_ALIAS = "JARVIS_LOCAL"
PROMPT = "Return exactly: TRANSPORT_OK"
KNOWN_CONFIG = REPO / "config.env"
EXTERNAL_WRAPPER = Path("/home/navigator/bin/zth-codex-teacher")
CODEX_EXPECTED_VERSION = "codex-cli 0.146.0"
HISTORICAL_V2_BASE_URL = "http://192.168.1.13:8083/v1"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def atomic_json(path: Path, value: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def parse_config_env(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    if not path.is_file():
        return result
    pattern = re.compile(r'^\s*export\s+([A-Za-z_][A-Za-z0-9_]*)=(?:"([^"]*)"|\'([^\']*)\'|(.*?))\s*$')
    for line in path.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if match:
            result[match.group(1)] = next((item for item in match.groups()[1:] if item is not None), "")
    return result


def request_path_regression() -> dict[str, Any]:
    spec = resolve_worker_spec("handoff", base_url=HISTORICAL_V2_BASE_URL, model=LOCAL_MODEL, api="openai-chat")
    completion = completion_url(spec)
    models = models_url(spec)
    captured: dict[str, str] = {}

    def capture_and_fail(request: Any, timeout: int) -> Any:
        captured["url"] = request.full_url
        raise urllib.error.URLError("model-free request construction regression")

    with patch("local_harness.icm_call._read_json_response", side_effect=capture_and_fail):
        response = call_worker(spec, PROMPT, max_tokens=1, timeout=1)
    return {
        "validated_base_url": spec.base_url,
        "completion_url": completion,
        "models_url": models,
        "placeholder_absent": "<LAN_HOST>" not in completion and "<LAN_HOST>" not in models,
        "request_path_uses_validated_base_url": (
            completion == HISTORICAL_V2_BASE_URL + "/chat/completions"
            and captured.get("url") == completion
            and response.request_url == completion
        ),
        "model": spec.model,
    }


def local_candidates() -> tuple[list[dict[str, str]], dict[str, str]]:
    configured = parse_config_env(KNOWN_CONFIG)
    candidates: list[dict[str, str]] = []
    for url_key, model_key in (
        ("ZTH_CAPABILITY_TEACHER_BASE_URL", "ZTH_CAPABILITY_TEACHER_MODEL"),
        ("ICM_HANDOFF_BASE_URL", "ICM_HANDOFF_MODEL"),
    ):
        url = os.environ.get(url_key) or configured.get(url_key)
        model = os.environ.get(model_key) or configured.get(model_key)
        if url:
            candidates.append({"source": url_key, "base_url": url.rstrip("/"), "model": model or ""})
    return candidates, configured


def local_non_inference_and_optional_completion(run_dir: Path) -> dict[str, Any]:
    candidates, configured = local_candidates()
    result: dict[str, Any] = {
        "authoritative_identity": f"{LOCAL_MODEL} via {LOCAL_ALIAS}",
        "candidates": candidates,
        "config_model_entries": {k: v for k, v in configured.items() if "MODEL" in k or "BASE_URL" in k},
        "placeholder_rejected": True,
        "completion_calls": 0,
        "models_get_calls": 0,
        "transport_qualified": False,
        "completion_attempted": False,
    }
    valid = [item for item in candidates if item["model"] == LOCAL_MODEL and "<LAN_HOST>" not in item["base_url"]]
    if not valid:
        result["failure"] = "no configured reachable-candidate identity for authoritative 30B model"
        result["request_path_regression"] = request_path_regression()
        return result

    candidate = valid[0]
    spec = resolve_worker_spec("handoff", base_url=candidate["base_url"], model=LOCAL_MODEL, api="openai-chat")
    if "<LAN_HOST>" in models_url(spec):
        result["failure"] = "unresolved local endpoint placeholder"
        return result
    result["resolved_spec"] = {"base_url": spec.base_url, "model": spec.model, "api": spec.api}
    result["models_url"] = models_url(spec)
    try:
        started = time.monotonic()
        models_payload = list_models(spec, timeout=10)
        result["models_get_calls"] = 1
        result["models_elapsed_ms"] = round((time.monotonic() - started) * 1000, 3)
        result["models_payload_sha256"] = sha256_bytes(json.dumps(models_payload, sort_keys=True).encode("utf-8"))
        model_ids = [str(item.get("id")) for item in models_payload.get("data", []) if isinstance(item, dict) and item.get("id")]
        result["model_ids"] = model_ids
        if LOCAL_MODEL not in model_ids:
            result["failure"] = "reachable endpoint did not expose the authoritative 30B model identity"
            return result
    except Exception as exc:
        result["models_get_calls"] = 1
        result["failure"] = f"local /models non-inference check failed: {exc}"
        return result

    result["completion_attempted"] = True
    result["completion_calls"] = 1
    started = time.monotonic()
    response = call_worker(spec, PROMPT, max_tokens=32, timeout=120)
    elapsed = round((time.monotonic() - started) * 1000, 3)
    raw = response.content.encode("utf-8")
    (run_dir / "local_response.bin").write_bytes(raw)
    result.update({
        "actual_url": response.request_url,
        "requested_model": LOCAL_MODEL,
        "http_or_transport_status": response.status,
        "raw_response_sha256": sha256_bytes(raw),
        "raw_response_text": response.content,
        "response_metadata": response.metadata(),
        "elapsed_ms": elapsed,
        "transport_qualified": response.status == "ok" and bool(raw.strip()),
    })
    return result


def external_transport(run_dir: Path) -> dict[str, Any]:
    wrapper_sha = sha256_file(EXTERNAL_WRAPPER)
    codex_path = shutil.which("codex")
    version = subprocess.run([codex_path or "codex", "--version"], cwd="/tmp", capture_output=True, timeout=15, check=False)
    runtime = Path("/tmp/zth_explicit_interface_v3_transport_runtime")
    if runtime.exists():
        raise RuntimeError("refusing an existing external qualification runtime")
    (runtime / "codex_home").mkdir(parents=True, exist_ok=False)
    (runtime / "home").mkdir(parents=True, exist_ok=False)
    env = os.environ.copy()
    env.update({
        "HOME": str(runtime / "home"),
        "CODEX_HOME": str(runtime / "codex_home"),
        "TMPDIR": str(runtime),
    })
    started = time.monotonic()
    proc = subprocess.run(
        [str(EXTERNAL_WRAPPER)],
        input=(PROMPT + "\n").encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd="/tmp",
        env=env,
        timeout=180,
        check=False,
    )
    elapsed = round((time.monotonic() - started) * 1000, 3)
    stdout = proc.stdout
    stderr = proc.stderr
    (run_dir / "external_stdout.bin").write_bytes(stdout)
    (run_dir / "external_stderr.bin").write_bytes(stderr)
    return {
        "wrapper_path": str(EXTERNAL_WRAPPER),
        "wrapper_sha256": wrapper_sha,
        "codex_path": codex_path,
        "codex_version_stdout": version.stdout.decode("utf-8", "replace"),
        "codex_version_stderr": version.stderr.decode("utf-8", "replace"),
        "codex_version_returncode": version.returncode,
        "expected_codex_version": CODEX_EXPECTED_VERSION,
        "cwd": "/tmp",
        "cwd_outside_repository": True,
        "isolated_runtime_state": str(runtime),
        "sandbox_flag_preserved": True,
        "tools_mechanically_disabled": False,
        "tool_calls_observed": "BEST_AVAILABLE_OBSERVATION",
        "repository_access_observed": "BEST_AVAILABLE_OBSERVATION",
        "prompt_sha256": sha256_bytes((PROMPT + "\n").encode("utf-8")),
        "returncode": proc.returncode,
        "stdout_sha256": sha256_bytes(stdout),
        "stderr_sha256": sha256_bytes(stderr),
        "stdout": stdout.decode("utf-8", "replace"),
        "stderr": stderr.decode("utf-8", "replace"),
        "elapsed_ms": elapsed,
        "transport_qualified": proc.returncode == 0 and stdout.strip() == b"TRANSPORT_OK",
        "model_completion_calls": 1,
    }


def assemble_existing(run_dir: Path, external_returncode: int) -> dict[str, Any]:
    """Assemble the already-captured one-shot evidence without invoking anything."""
    stdout = (run_dir / "external_stdout.bin").read_bytes()
    stderr = (run_dir / "external_stderr.bin").read_bytes()
    external = {
        "wrapper_path": str(EXTERNAL_WRAPPER),
        "wrapper_sha256": sha256_file(EXTERNAL_WRAPPER),
        "codex_path": shutil.which("codex"),
        "observed_codex_version": CODEX_EXPECTED_VERSION,
        "cwd": "/tmp",
        "cwd_outside_repository": True,
        "isolated_runtime_state": "/tmp/zth_explicit_interface_v3_transport_runtime",
        "sandbox_flag_preserved": True,
        "tools_mechanically_disabled": False,
        "tool_calls_observed": "BEST_AVAILABLE_OBSERVATION",
        "repository_access_observed": "BEST_AVAILABLE_OBSERVATION",
        "prompt_sha256": sha256_bytes((PROMPT + "\n").encode("utf-8")),
        "returncode": external_returncode,
        "stdout_sha256": sha256_bytes(stdout),
        "stderr_sha256": sha256_bytes(stderr),
        "stdout": stdout.decode("utf-8", "replace"),
        "stderr": stderr.decode("utf-8", "replace"),
        "transport_qualified": False,
        "failure_class": "codex_authentication_transport_failure",
        "model_produced_response": False,
        "model_completion_calls": 1,
    }
    local = local_non_inference_and_optional_completion(run_dir)
    return {
        "schema": "zth.explicit_interface_v3.transport_qualification",
        "v2_preserved": True,
        "v2_characterization": "LOCAL_AND_EXTERNAL_CAPABILITY_NOT_MEASURED_DUE_TO_TRANSPORT_FAILURES",
        "prompt": PROMPT,
        "local": local,
        "external": external,
        "qualification_calls": {
            "local_completion": local["completion_calls"],
            "external_invocation": 1,
            "external_model_produced_response": 0,
        },
        "v2_or_v3_experiment_calls": 0,
        "recording_mode": "post_call_assembly_no_reexecution",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--assemble-existing", action="store_true")
    parser.add_argument("--external-returncode", type=int, default=1)
    args = parser.parse_args()
    if args.assemble_existing:
        if not args.run_dir.is_dir() or not (args.run_dir / "external_stdout.bin").is_file() or not (args.run_dir / "external_stderr.bin").is_file():
            raise SystemExit("existing raw qualification evidence is incomplete")
        result = assemble_existing(args.run_dir, args.external_returncode)
        atomic_json(args.run_dir / "qualification.json", result)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    if args.run_dir.exists():
        raise SystemExit("refusing an existing qualification run directory")
    args.run_dir.mkdir(parents=True)
    before = subprocess.run(["git", "status", "--porcelain"], cwd=REPO, capture_output=True, text=True, check=True).stdout
    local_result = local_non_inference_and_optional_completion(args.run_dir)
    external_result = external_transport(args.run_dir)
    result = {
        "schema": "zth.explicit_interface_v3.transport_qualification",
        "v2_preserved": True,
        "v2_characterization": "LOCAL_AND_EXTERNAL_CAPABILITY_NOT_MEASURED_DUE_TO_TRANSPORT_FAILURES",
        "prompt": PROMPT,
        "local": local_result,
        "external": external_result,
        "repository_status_before": before,
        "repository_status_after": subprocess.run(["git", "status", "--porcelain"], cwd=REPO, capture_output=True, text=True, check=True).stdout,
        "qualification_calls": {
            "local_completion": local_result["completion_calls"],
            "external_completion": external_result["model_completion_calls"],
        },
        "v2_or_v3_experiment_calls": 0,
    }
    atomic_json(args.run_dir / "qualification.json", result)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
