from __future__ import annotations

import json
import io
import subprocess
import sys
import threading
import socket
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from contextlib import redirect_stdout, redirect_stderr
from unittest.mock import patch
import urllib.error

import local_harness.run_manual_supervised_attempt as manual_attempt

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness" / "run_manual_supervised_attempt.py"


def run_script(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def _valid_raw_output_json() -> str:
    return json.dumps(
        {
            "allowed_targets": ["docs/reports/"],
            "held_targets": [
                "production automation",
                "automatic curriculum capture",
                "automatic promotion",
                "implementation_packet",
            ],
            "scope_expansion_required": False,
            "claims": [
                "The request is a design-planning task involving LoRA and prompt injection.",
                "docs/reports/ is the only allowed target in this packet.",
            ],
            "evidence_basis": [
                "Task summary mentions matched keywords: lora, prompt injection.",
                "Allowed Targets lists docs/reports/.",
            ],
            "unverified_claims": [],
            "format": "json",
            "required_fields_present": True,
            "reason": "The output remains bounded and supervised.",
        }
    )


def _captured_model_call_metadata(
    *,
    prompt_text: str,
    raw_output_text: str,
    model: str = "Qwen_Qwen3-1.7B-Q4_K_M.gguf",
    endpoint: str = "http://192.168.1.16:8081/v1",
) -> dict[str, object]:
    return {
        "source": "local_openai_compatible_endpoint",
        "endpoint": endpoint,
        "model": model,
        "temperature": 0,
        "max_tokens": 1024,
        "prompt_path": "prompt_to_paste.md",
        "prompt_sha256": manual_attempt._sha256_text(prompt_text),
        "prompt_length": len(prompt_text),
        "raw_output_path": "raw_model_output.txt",
        "raw_output_sha256": manual_attempt._sha256_text(raw_output_text),
        "raw_output_length": len(raw_output_text),
        "call_status": "completed",
        "review_required": True,
        "request_provenance": {
            "api": "openai-chat",
            "endpoint": endpoint,
            "request_url": f"{endpoint.rstrip('/')}/chat/completions",
            "model": model,
            "configured_model": model,
            "resolved_model": model,
            "prompt_path": "prompt_to_paste.md",
            "prompt_sha256": manual_attempt._sha256_text(prompt_text),
            "prompt_length": len(prompt_text),
            "max_tokens": 1024,
            "temperature": 0,
        },
        "response_provenance": {
            "raw_output_path": "raw_model_output.txt",
            "raw_output_sha256": manual_attempt._sha256_text(raw_output_text),
            "raw_output_length": len(raw_output_text),
            "model": model,
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


def _write_captured_model_call_metadata(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _prepare_run(tmp_path: Path, *, timestamp: str = "20260707T010101Z") -> Path:
    out_dir = tmp_path / "runs"
    result = run_script(
        "prepare",
        "--messy-input",
        "The LoRA and prompt injection work got messy. Build a bounded design packet.",
        "--out-dir",
        out_dir,
        "--timestamp",
        timestamp,
    )
    assert result.returncode == 0
    run_dir = out_dir / timestamp
    (run_dir / "prompt_to_paste.md").write_text(
        (run_dir / "model_prompt_packet.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return run_dir


def _session_run(
    tmp_path: Path,
    *,
    timestamp: str = "20260707T010101Z",
    print_prompt: bool = False,
    write_prompt_copy: bool = False,
) -> tuple[Path, subprocess.CompletedProcess[str]]:
    out_dir = tmp_path / "runs"
    command: list[str | Path] = [
        "session",
        "--messy-input",
        "The LoRA and prompt injection work got messy. Build a bounded design packet.",
        "--out-dir",
        out_dir,
        "--timestamp",
        timestamp,
    ]
    if print_prompt:
        command.append("--print-prompt")
    if write_prompt_copy:
        command.append("--write-prompt-copy")
    result = run_script(*command)
    assert result.returncode == 0
    return out_dir / timestamp, result


class _LocalHandler(BaseHTTPRequestHandler):
    response_code = 200
    response_body = {"choices": [{"message": {"content": "{\"reason\": \"ok\"}"}}]}
    seen_path = ""
    seen_request_body: dict[str, object] | None = None

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", "0"))).decode("utf-8")
        try:
            _LocalHandler.seen_request_body = json.loads(body)
        except json.JSONDecodeError:
            _LocalHandler.seen_request_body = None
        _LocalHandler.seen_path = self.path
        payload = json.dumps(_LocalHandler.response_body).encode("utf-8")
        self.send_response(_LocalHandler.response_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args):
        return


def _start_local_server(*, response_code: int, response_body: dict[str, object]) -> tuple[HTTPServer, str, threading.Thread]:
    _LocalHandler.response_code = response_code
    _LocalHandler.response_body = response_body
    _LocalHandler.seen_path = ""
    _LocalHandler.seen_request_body = None
    server = HTTPServer(("127.0.0.1", 0), _LocalHandler)
    endpoint = f"http://127.0.0.1:{server.server_port}/v1"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, endpoint, thread


class _FakeUrlopenResponse:
    def __init__(self, *, status_code: int, body: dict[str, object]):
        self.status = status_code
        self._body = json.dumps(body).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self._body

    def getcode(self):
        return self.status


def _run_call_local_in_process(
    *,
    run_dir: Path,
    endpoint: str,
    model: str,
    temperature: float = 0,
    max_tokens: int = 1024,
    timeout_seconds: float = 30,
    overwrite: bool = False,
    response_code: int = 200,
    response_body: dict[str, object] | None = None,
    urlopen_side_effect=None,
) -> subprocess.CompletedProcess[str]:
    seen_request: dict[str, object] | None = None

    def fake_urlopen(request, timeout=None):
        nonlocal seen_request
        _ = timeout
        seen_request = json.loads(request.data.decode("utf-8")) if getattr(request, "data", None) else None
        if response_code >= 400:
            body = response_body or {}
            raise urllib.error.HTTPError(
                request.full_url,
                response_code,
                "mocked error",
                hdrs=None,
                fp=io.BytesIO(json.dumps(body).encode("utf-8")),
            )
        return _FakeUrlopenResponse(status_code=response_code, body=response_body or {"choices": []})

    stdout = io.StringIO()
    stderr = io.StringIO()
    side_effect = urlopen_side_effect or fake_urlopen
    with patch.object(manual_attempt.urllib.request, "urlopen", side_effect=side_effect):
        try:
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = manual_attempt.main(
                    [
                        "call-local",
                        "--run-dir",
                        str(run_dir),
                        "--endpoint",
                        endpoint,
                        "--model",
                        model,
                        "--temperature",
                        str(temperature),
                        "--max-tokens",
                        str(max_tokens),
                        "--timeout-seconds",
                        str(timeout_seconds),
                        *(["--overwrite"] if overwrite else []),
                    ]
                )
        except SystemExit as exc:
            exit_code = int(exc.code or 0)
    stdout_text = stdout.getvalue()
    if seen_request is not None:
        stdout_text += f"request_payload: {json.dumps(seen_request)}\n"
    return subprocess.CompletedProcess(
        args=[],
        returncode=exit_code,
        stdout=stdout_text,
        stderr=stderr.getvalue(),
    )


def _read_json_if_exists(path: Path) -> dict[str, object] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _write_export_pattern_inputs(run_dir: Path) -> dict[str, str]:
    failure_raw_name = "raw_model_output.failed_001.txt"
    failure_validation_name = "output_validation.failed_001.json"
    retry_prompt_name = "retry_prompt_to_paste_001.md"
    success_raw_name = "raw_model_output.success_001.txt"
    success_validation_name = "output_validation.success_001.json"

    (run_dir / failure_raw_name).write_text('{"required_fields_present": true}', encoding="utf-8")
    (run_dir / retry_prompt_name).write_text("Return all required top-level fields exactly.\n", encoding="utf-8")
    (run_dir / success_raw_name).write_text('{"allowed_targets": ["docs/reports/"]}', encoding="utf-8")
    (run_dir / failure_validation_name).write_text(
        json.dumps(
            {
                "validation_status": "failed",
                "checks": [
                    {
                        "check_id": "required_fields",
                        "status": "failed",
                        "message": "Missing required fields: allowed_targets, held_targets",
                    }
                ],
                "diagnostics": [
                    "Required fields missing from parsed output: allowed_targets, held_targets"
                ],
            }
        ),
        encoding="utf-8",
    )
    (run_dir / success_validation_name).write_text(
        json.dumps({"validation_status": "passed", "validator_diagnostics": []}),
        encoding="utf-8",
    )
    return {
        "failure_raw": failure_raw_name,
        "failure_validation": failure_validation_name,
        "retry_prompt": retry_prompt_name,
        "success_raw": success_raw_name,
        "success_validation": success_validation_name,
    }


def _write_retry_contract_inputs(run_dir: Path, *, validation_status: str = "failed") -> None:
    (run_dir / "raw_model_output.txt").write_text(
        '{"format":"json","required_fields_present":true,"reason":"output contract metadata instead of payload"}',
        encoding="utf-8",
    )
    (run_dir / "output_validation.json").write_text(
        json.dumps(
            {
                "validation_status": validation_status,
                "checks": [
                    {
                        "check_id": "required_fields",
                        "status": "failed",
                        "message": "Missing required fields: allowed_targets, held_targets",
                    }
                ],
                "diagnostics": [
                    "Required fields missing from parsed output: allowed_targets, held_targets"
                ],
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "output_validation_report.txt").write_text(
        "validation_status: failed\nvalidator diagnostics: missing required fields\n",
        encoding="utf-8",
    )
    (run_dir / "model_prompt_packet.md").write_text(
        "Original model prompt packet text.\n",
        encoding="utf-8",
    )
    (run_dir / "output_contract.json").write_text(
        json.dumps(
            {
                "format": "json",
                "required_fields": [
                    "allowed_targets",
                    "held_targets",
                    "scope_expansion_required",
                    "claims",
                    "evidence_basis",
                    "unverified_claims",
                    "format",
                    "required_fields_present",
                    "reason",
                ],
                "requires_reason": True,
            }
        ),
        encoding="utf-8",
    )


def test_prepare_from_messy_input_writes_required_artifacts(tmp_path: Path):
    out_dir = tmp_path / "runs"
    ts = "20260707T020202Z"
    result = run_script(
        "prepare",
        "--messy-input",
        "The LoRA and prompt injection work got messy. Build a bounded design packet.",
        "--out-dir",
        out_dir,
        "--timestamp",
        ts,
    )
    assert result.returncode == 0
    run_dir = out_dir / ts
    assert run_dir.is_dir()
    assert (run_dir / "messy_input.txt").is_file()
    assert (run_dir / "model_prompt_packet.md").is_file()
    assert (run_dir / "operator_instructions.txt").is_file()
    assert (run_dir / "run_manifest.json").is_file()
    assert (run_dir / "output_contract.json").is_file()


def test_prepare_from_messy_input_file(tmp_path: Path):
    out_dir = tmp_path / "runs"
    ts = "20260707T030303Z"
    messy_path = tmp_path / "messy.txt"
    messy_path.write_text("The LoRA and prompt injection work got messy. Build a bounded design packet.\n", encoding="utf-8")
    result = run_script(
        "prepare",
        "--messy-input-file",
        messy_path,
        "--out-dir",
        out_dir,
        "--timestamp",
        ts,
    )
    assert result.returncode == 0
    assert (out_dir / ts / "messy_input.txt").is_file()


def test_prepare_stores_tightened_output_contract(tmp_path: Path):
    run_dir = _prepare_run(tmp_path, timestamp="20260707T040404Z")
    contract = json.loads((run_dir / "output_contract.json").read_text(encoding="utf-8"))
    assert contract["format"] == "json"
    assert contract["requires_reason"] is True
    assert contract["required_fields"] == [
        "allowed_targets",
        "held_targets",
        "scope_expansion_required",
        "claims",
        "evidence_basis",
        "unverified_claims",
        "format",
        "required_fields_present",
        "reason",
    ]


def test_prepare_refuses_overwrite_by_default(tmp_path: Path):
    out_dir = tmp_path / "runs"
    ts = "20260707T050505Z"
    (out_dir / ts).mkdir(parents=True)
    result = run_script(
        "prepare",
        "--messy-input",
        "Bounded operator input.",
        "--out-dir",
        out_dir,
        "--timestamp",
        ts,
    )
    assert result.returncode != 0
    assert "already exists" in result.stderr


def test_prepare_supports_deterministic_timestamp(tmp_path: Path):
    out_dir = tmp_path / "runs"
    ts = "20260707T060606Z"
    result = run_script(
        "prepare",
        "--messy-input",
        "Bounded operator input.",
        "--out-dir",
        out_dir,
        "--timestamp",
        ts,
    )
    assert result.returncode == 0
    assert f"run_dir: {out_dir / ts}" in result.stdout


def test_prepare_rejects_missing_messy_input(tmp_path: Path):
    result = run_script(
        "prepare",
        "--out-dir",
        tmp_path / "runs",
    )
    assert result.returncode != 0
    assert "exactly one of --messy-input or --messy-input-file" in result.stderr


def test_prepare_rejects_both_messy_input_variants(tmp_path: Path):
    messy_path = tmp_path / "messy.txt"
    messy_path.write_text("bounded input\n", encoding="utf-8")
    result = run_script(
        "prepare",
        "--messy-input",
        "bounded input",
        "--messy-input-file",
        messy_path,
        "--out-dir",
        tmp_path / "runs",
    )
    assert result.returncode != 0
    assert "exactly one of --messy-input or --messy-input-file" in result.stderr


def test_session_mode_writes_required_artifacts_and_prompt_copy(tmp_path: Path):
    run_dir, result = _session_run(tmp_path, timestamp="20260707T171717Z")
    assert run_dir.is_dir()
    assert (run_dir / "messy_input.txt").is_file()
    assert (run_dir / "model_prompt_packet.md").is_file()
    assert (run_dir / "prompt_to_paste.md").is_file()
    assert (run_dir / "raw_model_output.txt").is_file()
    assert (run_dir / "operator_instructions.txt").is_file()
    assert (run_dir / "run_manifest.json").is_file()
    assert (run_dir / "output_contract.json").is_file()

    prompt_packet = (run_dir / "model_prompt_packet.md").read_text(encoding="utf-8")
    prompt_copy = (run_dir / "prompt_to_paste.md").read_text(encoding="utf-8")
    assert prompt_copy == prompt_packet
    assert "Manual Supervised Attempt Instructions" not in prompt_copy

    assert f"run_dir: {run_dir}" in result.stdout
    assert f"prompt_to_paste: {run_dir / 'prompt_to_paste.md'}" in result.stdout
    assert f"raw_output_file: {run_dir / 'raw_model_output.txt'}" in result.stdout
    assert (
        f"python3 local_harness/run_manual_supervised_attempt.py ingest --run-dir {run_dir} "
        f"--raw-output-file {run_dir / 'raw_model_output.txt'}"
    ) in result.stdout


def test_session_mode_print_prompt_uses_markers_and_excludes_operator_instructions(tmp_path: Path):
    run_dir, result = _session_run(tmp_path, timestamp="20260707T181818Z", print_prompt=True)
    assert "----- BEGIN MODEL PROMPT PACKET -----" in result.stdout
    assert "----- END MODEL PROMPT PACKET -----" in result.stdout
    begin = result.stdout.index("----- BEGIN MODEL PROMPT PACKET -----")
    end = result.stdout.index("----- END MODEL PROMPT PACKET -----")
    prompt_block = result.stdout[begin:end]
    assert "# ZTH Model Prompt Packet" in prompt_block
    assert "Manual Supervised Attempt Instructions" not in prompt_block
    assert str(run_dir / "prompt_to_paste.md") in result.stdout


def test_session_mode_supports_deterministic_timestamp(tmp_path: Path):
    out_dir = tmp_path / "runs"
    ts = "20260707T191919Z"
    result = run_script(
        "session",
        "--messy-input",
        "Bounded operator input.",
        "--out-dir",
        out_dir,
        "--timestamp",
        ts,
    )
    assert result.returncode == 0
    assert f"run_dir: {out_dir / ts}" in result.stdout


def test_session_mode_rejects_missing_messy_input(tmp_path: Path):
    result = run_script(
        "session",
        "--out-dir",
        tmp_path / "runs",
    )
    assert result.returncode != 0
    assert "exactly one of --messy-input or --messy-input-file" in result.stderr


def test_session_mode_accepts_write_prompt_copy_flag(tmp_path: Path):
    run_dir, result = _session_run(tmp_path, timestamp="20260707T202020Z", write_prompt_copy=True)
    assert result.returncode == 0
    prompt_packet = (run_dir / "model_prompt_packet.md").read_text(encoding="utf-8")
    prompt_copy = (run_dir / "prompt_to_paste.md").read_text(encoding="utf-8")
    assert prompt_copy == prompt_packet


def test_retry_contract_help_includes_retry_contract():
    result = run_script("--help")
    assert result.returncode == 0
    assert "retry-contract" in result.stdout


def test_retry_contract_writes_failed_snapshots_and_updates_prompt(tmp_path: Path):
    run_dir, _ = _session_run(tmp_path, timestamp="20260707T212122Z")
    _write_retry_contract_inputs(run_dir)
    result = run_script("retry-contract", "--run-dir", run_dir, "--retry-id", "1")
    assert result.returncode == 0
    assert (run_dir / "raw_model_output.failed_1.txt").read_text(encoding="utf-8") == (
        run_dir / "raw_model_output.txt"
    ).read_text(encoding="utf-8")
    assert json.loads((run_dir / "output_validation.failed_1.json").read_text(encoding="utf-8"))["validation_status"] == "failed"
    assert (run_dir / "output_validation_report.failed_1.txt").read_text(encoding="utf-8") == (
        run_dir / "output_validation_report.txt"
    ).read_text(encoding="utf-8")
    retry_prompt = (run_dir / "retry_prompt_to_paste_1.md").read_text(encoding="utf-8")
    assert "Required output contract:" in retry_prompt
    assert "Payload repair instructions" in retry_prompt
    assert "Previous failed output" in retry_prompt
    assert "Final required JSON payload skeleton" in retry_prompt
    assert "Do not omit any skeleton key" in retry_prompt
    assert "The final answer must be this payload shape, not the previous failed output" in retry_prompt
    assert retry_prompt.index("Previous failed output") < retry_prompt.index("Final required JSON payload skeleton")
    assert (run_dir / "prompt_to_paste.md").read_text(encoding="utf-8") == retry_prompt


def test_retry_contract_prompt_includes_validator_diagnostics_and_contract_fields(tmp_path: Path):
    run_dir, _ = _session_run(tmp_path, timestamp="20260707T212123Z")
    _write_retry_contract_inputs(run_dir)
    result = run_script("retry-contract", "--run-dir", run_dir, "--retry-id", "1")
    assert result.returncode == 0
    retry_prompt = (run_dir / "retry_prompt_to_paste_1.md").read_text(encoding="utf-8")
    assert "Validator diagnostics:" in retry_prompt
    assert "Required fields missing from parsed output: allowed_targets, held_targets" in retry_prompt
    assert "Do not return the output contract itself." in retry_prompt
    assert "Do not omit any skeleton key" in retry_prompt
    assert "The final answer must be this payload shape, not the previous failed output" in retry_prompt
    assert "Return the actual payload fields required by the contract." in retry_prompt
    assert "allowed_targets: list only the task-authorized targets." in retry_prompt
    assert "claims: list claims supported by the provided task/evidence only." in retry_prompt
    assert '"required_fields": [' in retry_prompt
    assert '"requires_reason": true' in retry_prompt
    assert '"required_fields_present": true' in retry_prompt
    assert '"format": "json"' in retry_prompt
    assert '"allowed_targets": []' in retry_prompt
    assert '"held_targets": []' in retry_prompt
    assert '"claims": []' in retry_prompt
    assert '"evidence_basis": []' in retry_prompt
    assert '"unverified_claims": []' in retry_prompt
    assert '"scope_expansion_required": false' in retry_prompt
    assert "output contract metadata instead of payload" in retry_prompt
    assert retry_prompt.index("Previous failed output") < retry_prompt.index("Final required JSON payload skeleton")


def test_retry_contract_includes_direct_structured_authority_guidance(tmp_path: Path):
    run_dir, _ = _session_run(tmp_path, timestamp="20260707T212129Z")
    _write_retry_contract_inputs(run_dir)
    (run_dir / "triage_packet.json").write_text(
        json.dumps({"allowed_targets": ["docs/reports/"]}),
        encoding="utf-8",
    )
    result = run_script("retry-contract", "--run-dir", run_dir, "--retry-id", "1")
    assert result.returncode == 0
    retry_prompt = (run_dir / "retry_prompt_to_paste_1.md").read_text(encoding="utf-8")
    assert "Structured authorized targets available for this run:" in retry_prompt
    assert "- docs/reports/" in retry_prompt
    assert "allowed_targets must be a subset of the structured authorized targets." in retry_prompt


def test_retry_contract_refuses_existing_failed_snapshots(tmp_path: Path):
    run_dir, _ = _session_run(tmp_path, timestamp="20260707T212124Z")
    _write_retry_contract_inputs(run_dir)
    assert run_script("retry-contract", "--run-dir", run_dir, "--retry-id", "1").returncode == 0
    result = run_script("retry-contract", "--run-dir", run_dir, "--retry-id", "1")
    assert result.returncode != 0
    assert "failed_1 artifacts already exist" in result.stderr


def test_retry_contract_rejects_passed_validation(tmp_path: Path):
    run_dir, _ = _session_run(tmp_path, timestamp="20260707T212125Z")
    _write_retry_contract_inputs(run_dir, validation_status="passed")
    result = run_script("retry-contract", "--run-dir", run_dir, "--retry-id", "1")
    assert result.returncode != 0
    assert "validation_status == 'failed'" in result.stderr


def test_retry_contract_rejects_missing_raw_output(tmp_path: Path):
    run_dir, _ = _session_run(tmp_path, timestamp="20260707T212126Z")
    _write_retry_contract_inputs(run_dir)
    (run_dir / "raw_model_output.txt").unlink()
    result = run_script("retry-contract", "--run-dir", run_dir, "--retry-id", "1")
    assert result.returncode != 0
    assert "missing raw_model_output.txt" in result.stderr


def test_retry_contract_creates_no_acceptance_artifacts(tmp_path: Path):
    run_dir, _ = _session_run(tmp_path, timestamp="20260707T212127Z")
    _write_retry_contract_inputs(run_dir)
    result = run_script("retry-contract", "--run-dir", run_dir, "--retry-id", "1")
    assert result.returncode == 0
    assert not (run_dir / "review_decision.json").exists()
    assert not (run_dir / "downstream_use_gate.json").exists()
    assert not (run_dir / "handoff_packet.json").exists()


def test_retry_contract_performs_no_model_or_export_side_effects(tmp_path: Path):
    run_dir, _ = _session_run(tmp_path, timestamp="20260707T212128Z")
    _write_retry_contract_inputs(run_dir)
    result = run_script("retry-contract", "--run-dir", run_dir, "--retry-id", "1")
    assert result.returncode == 0
    assert not (run_dir / "local_model_call.json").exists()
    assert not (run_dir / "local_model_call.failed.json").exists()
    assert not (run_dir / "local_model_response.failed.json").exists()
    assert not any(path.name.startswith("examples") for path in run_dir.iterdir())


def test_call_local_reads_prompt_posts_to_chat_completions_and_writes_raw_output_and_metadata(tmp_path: Path):
    run_dir, _ = _session_run(tmp_path, timestamp="20260707T212121Z")
    endpoint = "http://127.0.0.1:65500/v1"
    result = _run_call_local_in_process(
        run_dir=run_dir,
        endpoint=endpoint,
        model="qwen3-1.7b-gpu-40k",
        response_body={"choices": [{"message": {"content": "{\"reason\":\"local\"}"}}]},
    )

    assert result.returncode == 0
    assert result.stderr == ""
    body = json.loads(result.stdout.split("request_payload: ", 1)[1]) if "request_payload: " in result.stdout else None
    assert isinstance(body, dict)
    assert body["model"] == "qwen3-1.7b-gpu-40k"
    assert body["temperature"] == 0
    assert body["max_tokens"] == 1024
    assert isinstance(body["messages"], list)
    assert len(body["messages"]) == 1
    assert body["messages"][0]["role"] == "user"
    prompt = (run_dir / "prompt_to_paste.md").read_text(encoding="utf-8")
    assert body["messages"][0]["content"] == prompt

    raw = (run_dir / "raw_model_output.txt").read_text(encoding="utf-8")
    assert raw == "{\"reason\":\"local\"}"

    metadata = json.loads((run_dir / "local_model_call.json").read_text(encoding="utf-8"))
    assert not (run_dir / "local_model_call.failed.json").exists()
    assert not (run_dir / "local_model_response.failed.json").exists()
    assert metadata["source"] == "local_openai_compatible_endpoint"
    assert metadata["endpoint"] == endpoint
    assert metadata["model"] == "qwen3-1.7b-gpu-40k"
    assert metadata["temperature"] == 0
    assert metadata["max_tokens"] == 1024
    assert metadata["call_status"] == "completed"
    assert metadata["review_required"] is True
    boundaries = metadata["authority_boundaries"]
    assert "Local model call is not command execution authority." in boundaries
    assert "Local model call is not file modification authority." in boundaries
    assert "No automatic patch promotion authority is granted." in boundaries
    assert "No automatic training authority is granted." in boundaries
    assert "No default failure-to-curriculum capture authority is granted." in boundaries
    assert "Ingest and explicit review are required before downstream use." in boundaries

    assert "next_ingest_command:" in result.stdout
    assert "run_manual_supervised_attempt.py ingest" in result.stdout
    assert not (run_dir / "review_decision.json").exists()
    assert not (run_dir / "downstream_use_gate.json").exists()
    assert not (run_dir / "handoff_packet.json").exists()


def test_call_local_honors_optional_temperature_and_max_tokens(tmp_path: Path):
    run_dir, _ = _session_run(tmp_path, timestamp="20260707T222222Z")
    result = _run_call_local_in_process(
        run_dir=run_dir,
        endpoint="http://127.0.0.1:65500/v1",
        model="qwen3-1.7b-gpu-40k",
        temperature=0.2,
        max_tokens=256,
        response_body={"choices": [{"message": {"content": "{}"}}]},
    )

    assert result.returncode == 0
    body = json.loads(result.stdout.split("request_payload: ", 1)[1]) if "request_payload: " in result.stdout else None
    assert isinstance(body, dict)
    assert body["temperature"] == 0.2
    assert body["max_tokens"] == 256


def test_call_local_refuses_overwrite_nonempty_raw_output_without_overwrite(tmp_path: Path):
    run_dir, _ = _session_run(tmp_path, timestamp="20260707T232323Z")
    raw_path = run_dir / "raw_model_output.txt"
    raw_path.write_text("already present", encoding="utf-8")

    result = run_script(
        "call-local",
        "--run-dir",
        run_dir,
        "--endpoint",
        "http://127.0.0.1:65500/v1",
        "--model",
        "qwen3-1.7b-gpu-40k",
    )

    assert result.returncode != 0
    assert "non-empty" in result.stderr
    assert raw_path.read_text(encoding="utf-8") == "already present"


def test_call_local_overwrite_allows_replacement(tmp_path: Path):
    run_dir, _ = _session_run(tmp_path, timestamp="20260708T000000Z")
    raw_path = run_dir / "raw_model_output.txt"
    raw_path.write_text("already present", encoding="utf-8")
    result = _run_call_local_in_process(
        run_dir=run_dir,
        endpoint="http://127.0.0.1:65500/v1",
        model="qwen3-1.7b-gpu-40k",
        overwrite=True,
        response_body={"choices": [{"message": {"content": "replacement"}}]},
    )

    assert result.returncode == 0
    assert raw_path.read_text(encoding="utf-8") == "replacement"


def test_call_local_missing_assistant_content_exits_nonzero(tmp_path: Path):
    run_dir, _ = _session_run(tmp_path, timestamp="20260708T010101Z")
    result = _run_call_local_in_process(
        run_dir=run_dir,
        endpoint="http://127.0.0.1:65500/v1",
        model="qwen3-1.7b-gpu-40k",
        response_body={"choices": [{"message": {}}]},
    )

    assert result.returncode != 0
    assert "missing assistant content" in result.stderr
    failure_metadata = _read_json_if_exists(run_dir / "local_model_call.failed.json")
    response_metadata = _read_json_if_exists(run_dir / "local_model_response.failed.json")
    assert isinstance(failure_metadata, dict)
    assert failure_metadata["call_status"] == "failed"
    assert failure_metadata["failure_reason"] == "missing_assistant_content"
    assert failure_metadata["response_status"] == 200
    assert isinstance(failure_metadata["response_body_json"], dict)
    assert failure_metadata["response_body_json"]["choices"][0]["message"] == {}
    assert "No command execution authority is granted." in failure_metadata["authority_boundaries"]
    assert "No file modification authority is granted." in failure_metadata["authority_boundaries"]
    assert isinstance(response_metadata, dict)
    assert response_metadata["failure_reason"] == "missing_assistant_content"
    assert response_metadata["response_body_json"]["choices"][0]["message"] == {}
    assert not (run_dir / "local_model_call.json").exists()
    assert (run_dir / "raw_model_output.txt").read_text(encoding="utf-8") == ""


def test_call_local_non_2xx_exits_nonzero(tmp_path: Path):
    run_dir, _ = _session_run(tmp_path, timestamp="20260708T020202Z")
    result = _run_call_local_in_process(
        run_dir=run_dir,
        endpoint="http://127.0.0.1:65500/v1",
        model="qwen3-1.7b-gpu-40k",
        response_code=500,
        response_body={"error": "boom"},
    )

    assert result.returncode != 0
    assert "HTTP 500" in result.stderr
    failure_metadata = _read_json_if_exists(run_dir / "local_model_call.failed.json")
    response_metadata = _read_json_if_exists(run_dir / "local_model_response.failed.json")
    assert isinstance(failure_metadata, dict)
    assert failure_metadata["failure_reason"] == "http_error"
    assert failure_metadata["response_status"] == 500
    assert failure_metadata["response_body_json"] == {"error": "boom"}
    assert isinstance(response_metadata, dict)
    assert response_metadata["response_status"] == 500
    assert response_metadata["response_body_json"] == {"error": "boom"}


def test_call_local_reasoning_content_only_fails_and_does_not_write_reasoning_text(tmp_path: Path):
    run_dir, _ = _session_run(tmp_path, timestamp="20260708T020203Z")
    result = _run_call_local_in_process(
        run_dir=run_dir,
        endpoint="http://127.0.0.1:65500/v1",
        model="qwen3-1.7b-gpu-40k",
        response_body={"choices": [{"message": {"content": "", "reasoning_content": "hidden chain"}}]},
    )

    assert result.returncode != 0
    assert "missing assistant content" in result.stderr
    assert (run_dir / "raw_model_output.txt").read_text(encoding="utf-8") == ""
    failure_metadata = _read_json_if_exists(run_dir / "local_model_call.failed.json")
    assert isinstance(failure_metadata, dict)
    assert failure_metadata["failure_reason"] == "missing_assistant_content"
    assert failure_metadata["response_body_json"]["choices"][0]["message"]["reasoning_content"] == "hidden chain"


def test_call_local_malformed_response_json_writes_failure_metadata(tmp_path: Path):
    run_dir, _ = _session_run(tmp_path, timestamp="20260708T020204Z")

    def fake_urlopen(request, timeout=None):
        _ = request
        _ = timeout

        class _Resp:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return b"not-json"

            def getcode(self):
                return 200

        return _Resp()

    with patch.object(manual_attempt.urllib.request, "urlopen", side_effect=fake_urlopen):
        result = manual_attempt.main(
            [
                "call-local",
                "--run-dir",
                str(run_dir),
                "--endpoint",
                "http://127.0.0.1:65500/v1",
                "--model",
                "qwen3-1.7b-gpu-40k",
            ]
        )

    assert result == 1
    failure_metadata = _read_json_if_exists(run_dir / "local_model_call.failed.json")
    assert isinstance(failure_metadata, dict)
    assert failure_metadata["failure_reason"] == "malformed_response_json"
    assert failure_metadata["response_body_text"] == "not-json"


def test_call_local_connection_failure_writes_failure_metadata_without_body(tmp_path: Path):
    run_dir, _ = _session_run(tmp_path, timestamp="20260708T020205Z")
    result = run_script(
        "call-local",
        "--run-dir",
        run_dir,
        "--endpoint",
        "http://127.0.0.1:1/v1",
        "--model",
        "qwen3-1.7b-gpu-40k",
        "--timeout-seconds",
        "0.1",
    )
    assert result.returncode != 0
    failure_metadata = _read_json_if_exists(run_dir / "local_model_call.failed.json")
    assert isinstance(failure_metadata, dict)
    assert failure_metadata["failure_reason"] == "connection_failed"
    assert "error_message" in failure_metadata
    assert "response_body_json" not in failure_metadata
    assert "response_body_text" not in failure_metadata


def test_call_local_timeout_exits_nonzero_and_writes_failure_metadata(tmp_path: Path):
    run_dir, _ = _session_run(tmp_path, timestamp="20260708T020206Z")
    raw_path = run_dir / "raw_model_output.txt"
    raw_path.write_text("preserve-me", encoding="utf-8")

    def timeout_urlopen(request, timeout=None):
        _ = request
        _ = timeout
        raise TimeoutError("timed out waiting for response")

    result = _run_call_local_in_process(
        run_dir=run_dir,
        endpoint="http://127.0.0.1:65500/v1",
        model="qwen3-1.7b-gpu-40k",
        timeout_seconds=480,
        overwrite=True,
        urlopen_side_effect=timeout_urlopen,
    )

    assert result.returncode != 0
    assert "timed out" in result.stderr
    failure_metadata = _read_json_if_exists(run_dir / "local_model_call.failed.json")
    assert isinstance(failure_metadata, dict)
    assert failure_metadata["failure_reason"] == "timeout"
    assert failure_metadata["timeout_seconds"] == 480
    assert failure_metadata["review_required"] is True
    assert "Failed local model call is evidence, not acceptance." in failure_metadata["authority_boundaries"]
    assert not (run_dir / "local_model_response.failed.json").exists()
    assert raw_path.read_text(encoding="utf-8") == "preserve-me"
    assert not (run_dir / "review_decision.json").exists()
    assert not (run_dir / "downstream_use_gate.json").exists()
    assert not (run_dir / "handoff_packet.json").exists()


def test_call_local_timeout_from_urlerror_reason_writes_failure_metadata(tmp_path: Path):
    run_dir, _ = _session_run(tmp_path, timestamp="20260708T020207Z")

    def timeout_urlopen(request, timeout=None):
        _ = request
        _ = timeout
        raise urllib.error.URLError("timed out")

    result = _run_call_local_in_process(
        run_dir=run_dir,
        endpoint="http://127.0.0.1:65500/v1",
        model="qwen3-1.7b-gpu-40k",
        timeout_seconds=480,
        urlopen_side_effect=timeout_urlopen,
    )

    assert result.returncode != 0
    failure_metadata = _read_json_if_exists(run_dir / "local_model_call.failed.json")
    assert isinstance(failure_metadata, dict)
    assert failure_metadata["failure_reason"] == "timeout"
    assert failure_metadata["timeout_seconds"] == 480


def test_call_local_timeout_from_socket_timeout_writes_failure_metadata(tmp_path: Path):
    run_dir, _ = _session_run(tmp_path, timestamp="20260708T020208Z")

    def timeout_urlopen(request, timeout=None):
        _ = request
        _ = timeout
        raise socket.timeout("timed out")

    result = _run_call_local_in_process(
        run_dir=run_dir,
        endpoint="http://127.0.0.1:65500/v1",
        model="qwen3-1.7b-gpu-40k",
        timeout_seconds=480,
        urlopen_side_effect=timeout_urlopen,
    )

    assert result.returncode != 0
    failure_metadata = _read_json_if_exists(run_dir / "local_model_call.failed.json")
    assert isinstance(failure_metadata, dict)
    assert failure_metadata["failure_reason"] == "timeout"
    assert failure_metadata["timeout_seconds"] == 480


def test_call_local_connection_failure_exits_nonzero(tmp_path: Path):
    run_dir, _ = _session_run(tmp_path, timestamp="20260708T030303Z")
    result = run_script(
        "call-local",
        "--run-dir",
        run_dir,
        "--endpoint",
        "http://127.0.0.1:1/v1",
        "--model",
        "qwen3-1.7b-gpu-40k",
        "--timeout-seconds",
        "0.1",
    )
    assert result.returncode != 0
    assert "connection failed" in result.stderr


def test_export_pattern_writes_candidate_artifact_and_preserves_failure_success_inputs(tmp_path: Path):
    run_dir, _ = _session_run(tmp_path, timestamp="20260708T040404Z")
    inputs = _write_export_pattern_inputs(run_dir)
    metadata = {
        "source": "local_openai_compatible_endpoint",
        "model": "qwen3-1.7b-gpu-40k",
        "temperature": 0,
        "max_tokens": 1024,
    }
    (run_dir / "local_model_call.json").write_text(json.dumps(metadata), encoding="utf-8")
    out_dir = tmp_path / "patterns"

    result = run_script(
        "export-pattern",
        "--run-dir",
        run_dir,
        "--failure-raw",
        inputs["failure_raw"],
        "--failure-validation",
        inputs["failure_validation"],
        "--retry-prompt",
        inputs["retry_prompt"],
        "--success-raw",
        inputs["success_raw"],
        "--success-validation",
        inputs["success_validation"],
        "--out-dir",
        out_dir,
        "--pattern-id",
        "zth_contract_missing_fields_retry_001",
    )

    assert result.returncode == 0
    pattern_path = out_dir / "zth_contract_missing_fields_retry_001.json"
    assert pattern_path.is_file()
    pattern = json.loads(pattern_path.read_text(encoding="utf-8"))
    assert pattern["artifact_type"] == "supervised_failure_success_training_pattern_candidate"
    assert pattern["status"] == "candidate"
    assert pattern["not_training_data_until_reviewed"] is True
    assert pattern["not_automatic_curriculum_capture"] is True
    assert pattern["failure"]["raw_output"] == '{"required_fields_present": true}'
    assert pattern["success"]["raw_output"] == '{"allowed_targets": ["docs/reports/"]}'
    assert pattern["correction"]["retry_prompt"] == "Return all required top-level fields exactly.\n"
    assert pattern["failure"]["validator_diagnostics"] == [
        "Required fields missing from parsed output: allowed_targets, held_targets"
    ]
    assert pattern["failure"]["missing_required_fields"] == ["allowed_targets", "held_targets"]
    assert pattern["success"]["validation_status"] == "passed"
    assert pattern["run_provenance"]["model"] == "qwen3-1.7b-gpu-40k"
    assert pattern["run_provenance"]["endpoint_kind"] == "local_openai_compatible_endpoint"
    boundaries = pattern["authority_boundaries"]
    assert "This artifact is evidence, not training authority." in boundaries
    assert "No automatic training authority is granted." in boundaries
    assert "No patch promotion authority is granted." in boundaries
    assert "No command execution authority is granted." in boundaries
    assert "No file modification authority is granted." in boundaries
    assert not (run_dir / "review_decision.json").exists()
    assert not (run_dir / "downstream_use_gate.json").exists()
    assert not (run_dir / "handoff_packet.json").exists()


def test_export_pattern_preserves_legacy_synthetic_failure_fields_when_present(tmp_path: Path):
    run_dir, _ = _session_run(tmp_path, timestamp="20260708T040405Z")
    inputs = _write_export_pattern_inputs(run_dir)
    failure_validation_name = inputs["failure_validation"]
    (run_dir / failure_validation_name).write_text(
        json.dumps(
            {
                "validation_status": "failed",
                "missing_required_fields": ["allowed_targets", "held_targets"],
                "validator_diagnostics": ["missing required fields"],
            }
        ),
        encoding="utf-8",
    )
    out_dir = tmp_path / "patterns"

    result = run_script(
        "export-pattern",
        "--run-dir",
        run_dir,
        "--failure-raw",
        inputs["failure_raw"],
        "--failure-validation",
        inputs["failure_validation"],
        "--retry-prompt",
        inputs["retry_prompt"],
        "--success-raw",
        inputs["success_raw"],
        "--success-validation",
        inputs["success_validation"],
        "--out-dir",
        out_dir,
        "--pattern-id",
        "zth_contract_missing_fields_retry_legacy_001",
    )

    assert result.returncode == 0
    pattern_path = out_dir / "zth_contract_missing_fields_retry_legacy_001.json"
    pattern = json.loads(pattern_path.read_text(encoding="utf-8"))
    assert pattern["failure"]["missing_required_fields"] == ["allowed_targets", "held_targets"]
    assert pattern["failure"]["validator_diagnostics"] == ["missing required fields"]


def test_export_pattern_does_not_mutate_source_run_artifacts(tmp_path: Path):
    run_dir, _ = _session_run(tmp_path, timestamp="20260708T050505Z")
    inputs = _write_export_pattern_inputs(run_dir)
    before_failure_raw = (run_dir / inputs["failure_raw"]).read_text(encoding="utf-8")
    before_success_raw = (run_dir / inputs["success_raw"]).read_text(encoding="utf-8")
    out_dir = tmp_path / "patterns"

    result = run_script(
        "export-pattern",
        "--run-dir",
        run_dir,
        "--failure-raw",
        inputs["failure_raw"],
        "--failure-validation",
        inputs["failure_validation"],
        "--retry-prompt",
        inputs["retry_prompt"],
        "--success-raw",
        inputs["success_raw"],
        "--success-validation",
        inputs["success_validation"],
        "--out-dir",
        out_dir,
        "--pattern-id",
        "zth_contract_missing_fields_retry_002",
    )
    assert result.returncode == 0
    assert (run_dir / inputs["failure_raw"]).read_text(encoding="utf-8") == before_failure_raw
    assert (run_dir / inputs["success_raw"]).read_text(encoding="utf-8") == before_success_raw


def test_export_pattern_refuses_missing_failure_files(tmp_path: Path):
    run_dir, _ = _session_run(tmp_path, timestamp="20260708T060606Z")
    out_dir = tmp_path / "patterns"
    result = run_script(
        "export-pattern",
        "--run-dir",
        run_dir,
        "--failure-raw",
        "missing_failure.txt",
        "--failure-validation",
        "output_validation.failed_001.json",
        "--retry-prompt",
        "retry_prompt_to_paste_001.md",
        "--success-raw",
        "raw_model_output.success_001.txt",
        "--success-validation",
        "output_validation.success_001.json",
        "--out-dir",
        out_dir,
        "--pattern-id",
        "zth_contract_missing_fields_retry_003",
    )
    assert result.returncode != 0
    assert "missing --failure-raw" in result.stderr


def test_export_pattern_refuses_missing_success_files(tmp_path: Path):
    run_dir, _ = _session_run(tmp_path, timestamp="20260708T070707Z")
    inputs = _write_export_pattern_inputs(run_dir)
    out_dir = tmp_path / "patterns"
    result = run_script(
        "export-pattern",
        "--run-dir",
        run_dir,
        "--failure-raw",
        inputs["failure_raw"],
        "--failure-validation",
        inputs["failure_validation"],
        "--retry-prompt",
        inputs["retry_prompt"],
        "--success-raw",
        "missing_success.txt",
        "--success-validation",
        inputs["success_validation"],
        "--out-dir",
        out_dir,
        "--pattern-id",
        "zth_contract_missing_fields_retry_004",
    )
    assert result.returncode != 0
    assert "missing --success-raw" in result.stderr


def test_export_pattern_refuses_overwrite_without_flag_and_allows_with_overwrite(tmp_path: Path):
    run_dir, _ = _session_run(tmp_path, timestamp="20260708T080808Z")
    inputs = _write_export_pattern_inputs(run_dir)
    out_dir = tmp_path / "patterns"
    pattern_id = "zth_contract_missing_fields_retry_005"
    first = run_script(
        "export-pattern",
        "--run-dir",
        run_dir,
        "--failure-raw",
        inputs["failure_raw"],
        "--failure-validation",
        inputs["failure_validation"],
        "--retry-prompt",
        inputs["retry_prompt"],
        "--success-raw",
        inputs["success_raw"],
        "--success-validation",
        inputs["success_validation"],
        "--out-dir",
        out_dir,
        "--pattern-id",
        pattern_id,
    )
    assert first.returncode == 0

    second = run_script(
        "export-pattern",
        "--run-dir",
        run_dir,
        "--failure-raw",
        inputs["failure_raw"],
        "--failure-validation",
        inputs["failure_validation"],
        "--retry-prompt",
        inputs["retry_prompt"],
        "--success-raw",
        inputs["success_raw"],
        "--success-validation",
        inputs["success_validation"],
        "--out-dir",
        out_dir,
        "--pattern-id",
        pattern_id,
    )
    assert second.returncode != 0
    assert "pattern already exists" in second.stderr

    third = run_script(
        "export-pattern",
        "--run-dir",
        run_dir,
        "--failure-raw",
        inputs["failure_raw"],
        "--failure-validation",
        inputs["failure_validation"],
        "--retry-prompt",
        inputs["retry_prompt"],
        "--success-raw",
        inputs["success_raw"],
        "--success-validation",
        inputs["success_validation"],
        "--out-dir",
        out_dir,
        "--pattern-id",
        pattern_id,
        "--overwrite",
    )
    assert third.returncode == 0


def test_ingest_valid_output_writes_attempt_validation_and_preserves_raw_output(tmp_path: Path):
    run_dir = _prepare_run(tmp_path, timestamp="20260707T070707Z")
    source_raw = tmp_path / "raw_model_output.txt"
    raw_text = _valid_raw_output_json()
    source_raw.write_text(raw_text, encoding="utf-8")

    result = run_script(
        "ingest",
        "--run-dir",
        run_dir,
        "--raw-output-file",
        source_raw,
    )
    assert result.returncode == 0
    assert (run_dir / "supervised_model_attempt.json").is_file()
    assert (run_dir / "output_validation.json").is_file()
    assert (run_dir / "output_validation_report.txt").is_file()


def test_ingest_rejects_unauthorized_allowed_targets(tmp_path: Path):
    run_dir = _prepare_run(tmp_path, timestamp="20260707T080808Z")
    raw_output = tmp_path / "raw_model_output.txt"
    raw_output.write_text(
        '{"allowed_targets": ["design_packet"], "held_targets": [], "scope_expansion_required": false, "claims": [], "evidence_basis": [], "unverified_claims": [], "format": "json", "required_fields_present": true, "reason": "bounded"}',
        encoding="utf-8",
    )
    result = run_script(
        "ingest",
        "--run-dir",
        run_dir,
        "--raw-output-file",
        raw_output,
    )
    assert result.returncode == 0
    validation = json.loads((run_dir / "output_validation.json").read_text(encoding="utf-8"))
    assert validation["validation_status"] == "failed"
    assert any(
        check["check_id"] == "target_authority" and check["status"] == "failed"
        for check in validation["checks"]
    )
    assert "Unauthorized allowed target in raw model output: design_packet" in "\n".join(
        validation["diagnostics"]
    )
    assert (run_dir / "raw_model_output.txt").read_text(encoding="utf-8") == raw_output.read_text(encoding="utf-8")
    assert "validation_status: failed" in result.stdout


def test_load_structured_authorized_targets_prefers_direct_triage_packet(tmp_path: Path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "triage_packet.json").write_text(
        json.dumps({"allowed_targets": ["docs/reports/"]}),
        encoding="utf-8",
    )
    manifest = {"artifacts": {}}
    assert manual_attempt._load_structured_authorized_targets(run_dir, manifest) == ["docs/reports/"]


def test_load_structured_authorized_targets_uses_direct_orchestration_packet_when_triage_missing(tmp_path: Path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "orchestration_packet.json").write_text(
        json.dumps({"allowed_targets": ["docs/reports/"]}),
        encoding="utf-8",
    )
    manifest = {"artifacts": {}}
    assert manual_attempt._load_structured_authorized_targets(run_dir, manifest) == ["docs/reports/"]


def test_load_structured_authorized_targets_prefers_triage_over_orchestration(tmp_path: Path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "triage_packet.json").write_text(
        json.dumps({"allowed_targets": ["docs/reports/"]}),
        encoding="utf-8",
    )
    (run_dir / "orchestration_packet.json").write_text(
        json.dumps({"allowed_targets": ["design_packet"]}),
        encoding="utf-8",
    )
    manifest = {"artifacts": {}}
    assert manual_attempt._load_structured_authorized_targets(run_dir, manifest) == ["docs/reports/"]


def test_load_structured_authorized_targets_returns_none_when_missing_structured_packets(tmp_path: Path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    manifest = {"artifacts": {}}
    assert manual_attempt._load_structured_authorized_targets(run_dir, manifest) is None


def test_ingest_without_review_keeps_not_reviewed_and_prints_review_required(tmp_path: Path):
    run_dir = _prepare_run(tmp_path, timestamp="20260707T080808Z")
    source_raw = tmp_path / "raw_model_output.txt"
    source_raw.write_text(_valid_raw_output_json(), encoding="utf-8")

    result = run_script(
        "ingest",
        "--run-dir",
        run_dir,
        "--raw-output-file",
        source_raw,
    )
    assert result.returncode == 0
    assert "review_required: explicit review decision is required before downstream use" in result.stdout

    attempt = json.loads((run_dir / "supervised_model_attempt.json").read_text(encoding="utf-8"))
    validation = json.loads((run_dir / "output_validation.json").read_text(encoding="utf-8"))
    assert attempt["acceptance_status"] == "not_reviewed"
    assert validation["acceptance_status"] == "not_reviewed"
    assert not (run_dir / "review_decision.json").exists()
    assert not (run_dir / "downstream_use_gate.json").exists()
    assert not (run_dir / "handoff_packet.json").exists()


def test_ingest_validation_fails_when_required_field_missing(tmp_path: Path):
    run_dir = _prepare_run(tmp_path, timestamp="20260707T090909Z")
    source_raw = tmp_path / "raw_model_output.txt"
    payload = json.loads(_valid_raw_output_json())
    del payload["scope_expansion_required"]
    source_raw.write_text(json.dumps(payload), encoding="utf-8")

    result = run_script(
        "ingest",
        "--run-dir",
        run_dir,
        "--raw-output-file",
        source_raw,
    )
    assert result.returncode == 0
    assert "validation_status: failed" in result.stdout
    validation = json.loads((run_dir / "output_validation.json").read_text(encoding="utf-8"))
    assert validation["validation_status"] == "failed"


def test_ingest_with_explicit_accepted_review_writes_decision_gate_handoff(tmp_path: Path):
    run_dir = _prepare_run(tmp_path, timestamp="20260707T101010Z")
    source_raw = tmp_path / "raw_model_output.txt"
    source_raw.write_text(_valid_raw_output_json(), encoding="utf-8")

    result = run_script(
        "ingest",
        "--run-dir",
        run_dir,
        "--raw-output-file",
        source_raw,
        "--decision",
        "accepted",
        "--decision-reason",
        "Output satisfies the required contract and remains within scope.",
        "--operator",
        "manual",
    )
    assert result.returncode == 0
    assert (run_dir / "review_decision.json").is_file()
    assert (run_dir / "downstream_use_gate.json").is_file()
    assert (run_dir / "handoff_packet.json").is_file()


def test_ingest_rejects_explicit_accepted_review_when_validation_failed(tmp_path: Path):
    run_dir = _prepare_run(tmp_path, timestamp="20260707T111111Z")
    source_raw = tmp_path / "raw_model_output.txt"
    source_raw.write_text('{"reason":"ok"}', encoding="utf-8")

    result = run_script(
        "ingest",
        "--run-dir",
        run_dir,
        "--raw-output-file",
        source_raw,
        "--decision",
        "accepted",
        "--decision-reason",
        "accept anyway",
        "--operator",
        "manual",
    )
    assert result.returncode != 0
    assert "accepted decision requires validation_status 'passed'" in result.stderr


def test_ingest_rejected_decision_keeps_gate_and_handoff_blocked(tmp_path: Path):
    run_dir = _prepare_run(tmp_path, timestamp="20260707T121212Z")
    source_raw = tmp_path / "raw_model_output.txt"
    source_raw.write_text(_valid_raw_output_json(), encoding="utf-8")

    result = run_script(
        "ingest",
        "--run-dir",
        run_dir,
        "--raw-output-file",
        source_raw,
        "--decision",
        "rejected",
        "--decision-reason",
        "Needs revisions.",
        "--operator",
        "manual",
    )
    assert result.returncode == 0
    gate = json.loads((run_dir / "downstream_use_gate.json").read_text(encoding="utf-8"))
    handoff = json.loads((run_dir / "handoff_packet.json").read_text(encoding="utf-8"))
    assert gate["gate_status"] == "blocked"
    assert handoff["handoff_status"] == "blocked"
    prohibited = handoff["prohibited_downstream_use"]
    assert "no_command_execution" in prohibited
    assert "no_direct_file_modification" in prohibited
    assert "no_patch_application" in prohibited
    assert "no_automatic_patch_promotion" in prohibited
    assert "no_automatic_training" in prohibited
    assert "no_default_failure_to_curriculum_capture" in prohibited


def test_ingest_revision_requested_decision_keeps_gate_and_handoff_blocked(tmp_path: Path):
    run_dir = _prepare_run(tmp_path, timestamp="20260707T131313Z")
    source_raw = tmp_path / "raw_model_output.txt"
    source_raw.write_text(_valid_raw_output_json(), encoding="utf-8")

    result = run_script(
        "ingest",
        "--run-dir",
        run_dir,
        "--raw-output-file",
        source_raw,
        "--decision",
        "revision_requested",
        "--decision-reason",
        "Clarify evidence basis.",
        "--operator",
        "manual",
    )
    assert result.returncode == 0
    gate = json.loads((run_dir / "downstream_use_gate.json").read_text(encoding="utf-8"))
    handoff = json.loads((run_dir / "handoff_packet.json").read_text(encoding="utf-8"))
    assert gate["gate_status"] == "blocked"
    assert handoff["handoff_status"] == "blocked"


def test_ingest_marks_manual_operator_provenance_and_no_endpoint_usage_fields(tmp_path: Path):
    run_dir = _prepare_run(tmp_path, timestamp="20260707T141414Z")
    source_raw = tmp_path / "raw_model_output.txt"
    source_raw.write_text(_valid_raw_output_json(), encoding="utf-8")

    result = run_script(
        "ingest",
        "--run-dir",
        run_dir,
        "--raw-output-file",
        source_raw,
    )
    assert result.returncode == 0
    attempt = json.loads((run_dir / "supervised_model_attempt.json").read_text(encoding="utf-8"))
    assert attempt["provenance"]["source"] == "manual_operator_pasted_model_output"
    assert attempt["model_metadata"]["provider"] == "manual_operator"
    assert "endpoint_url" not in attempt
    assert "raw_model_output" in attempt


def test_ingest_with_model_call_metadata_records_captured_model_provenance(tmp_path: Path):
    run_dir = _prepare_run(tmp_path, timestamp="20260707T151616Z")
    prompt_text = (run_dir / "prompt_to_paste.md").read_text(encoding="utf-8")
    source_raw = tmp_path / "raw_model_output.txt"
    raw_text = _valid_raw_output_json()
    source_raw.write_text(raw_text, encoding="utf-8")
    metadata = tmp_path / "local_model_call.json"
    metadata_payload = _captured_model_call_metadata(prompt_text=prompt_text, raw_output_text=raw_text)
    _write_captured_model_call_metadata(metadata, metadata_payload)

    result = run_script(
        "ingest",
        "--run-dir",
        run_dir,
        "--raw-output-file",
        source_raw,
        "--model-call-metadata-file",
        metadata,
        "--decision",
        "accepted",
        "--decision-reason",
        "Output satisfies the required contract and remains within scope.",
        "--operator",
        "manual",
        "--next-worker",
        "qwen3-30b",
        "--next-worker-objective",
        "Produce a bounded downstream comparison report.",
    )
    assert result.returncode == 0

    attempt = json.loads((run_dir / "supervised_model_attempt.json").read_text(encoding="utf-8"))
    assert attempt["model_metadata"]["model_id"] == "Qwen_Qwen3-1.7B-Q4_K_M.gguf"
    assert attempt["model_metadata"]["provider"] == "local_model_call"
    assert attempt["provenance"]["source"] == "captured_model_output"
    assert attempt["provenance"]["model_call_metadata_path"].endswith("local_model_call.json")
    assert attempt["provenance"]["model_call_metadata_sha256"] == manual_attempt._sha256_file(metadata)
    assert attempt["provenance"]["raw_output_sha256"] == manual_attempt._sha256_text(raw_text)
    assert attempt["provenance"]["raw_output_length"] == len(raw_text)
    assert attempt["provenance"]["acquisition_request_provenance"]["resolved_model"] == "Qwen_Qwen3-1.7B-Q4_K_M.gguf"
    assert "manual_operator_provided_model_output" not in json.dumps(attempt)
    assert attempt["provenance"]["acquisition_request_provenance"]["prompt_sha256"] == metadata_payload["prompt_sha256"]
    assert attempt["provenance"]["acquisition_request_provenance"]["prompt_length"] == metadata_payload["prompt_length"]
    assert attempt["provenance"]["acquisition_request_provenance"]["prompt_path"] == "prompt_to_paste.md"
    assert attempt["provenance"]["acquisition_request_provenance"]["request_url"] == metadata_payload["request_provenance"][
        "request_url"
    ]

    manifest = json.loads((run_dir / "transaction_manifest.json").read_text(encoding="utf-8"))
    assert manifest["records"]["attempt_id"] == attempt["attempt_id"]
    assert manifest["first_worker_identity"] == "Qwen_Qwen3-1.7B-Q4_K_M.gguf"


def test_ingest_with_tampered_model_call_metadata_fails_closed(tmp_path: Path):
    run_dir = _prepare_run(tmp_path, timestamp="20260707T161718Z")
    prompt_text = (run_dir / "prompt_to_paste.md").read_text(encoding="utf-8")
    raw_text = _valid_raw_output_json()
    source_raw = tmp_path / "raw_model_output.txt"
    source_raw.write_text(raw_text, encoding="utf-8")
    metadata = _captured_model_call_metadata(prompt_text=prompt_text, raw_output_text=raw_text)
    metadata["raw_output_sha256"] = "0" * 64
    metadata_path = tmp_path / "tampered_model_call.json"
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = run_script(
        "ingest",
        "--run-dir",
        run_dir,
        "--raw-output-file",
        source_raw,
        "--model-call-metadata-file",
        metadata_path,
    )
    assert result.returncode != 0
    assert "does not match model call metadata raw_output_sha256" in result.stderr


def test_ingest_with_prompt_sha_mismatch_fails_closed(tmp_path: Path):
    run_dir = _prepare_run(tmp_path, timestamp="20260707T171820Z")
    raw_text = _valid_raw_output_json()
    source_raw = tmp_path / "raw_model_output.txt"
    source_raw.write_text(raw_text, encoding="utf-8")
    metadata = _captured_model_call_metadata(
        prompt_text=(run_dir / "prompt_to_paste.md").read_text(encoding="utf-8"),
        raw_output_text=raw_text,
    )
    metadata["prompt_sha256"] = "1" * 64
    metadata["request_provenance"]["prompt_sha256"] = "1" * 64
    metadata_path = tmp_path / "prompt_sha_mismatch.json"
    _write_captured_model_call_metadata(metadata_path, metadata)

    result = run_script(
        "ingest",
        "--run-dir",
        run_dir,
        "--raw-output-file",
        source_raw,
        "--model-call-metadata-file",
        metadata_path,
    )
    assert result.returncode != 0
    assert "prompt_sha256 does not match run prompt artifact" in result.stderr


def test_ingest_with_prompt_length_mismatch_fails_closed(tmp_path: Path):
    run_dir = _prepare_run(tmp_path, timestamp="20260707T171821Z")
    raw_text = _valid_raw_output_json()
    source_raw = tmp_path / "raw_model_output.txt"
    source_raw.write_text(raw_text, encoding="utf-8")
    metadata = _captured_model_call_metadata(
        prompt_text=(run_dir / "prompt_to_paste.md").read_text(encoding="utf-8"),
        raw_output_text=raw_text,
    )
    metadata["prompt_length"] = metadata["prompt_length"] + 1
    metadata["request_provenance"]["prompt_length"] = metadata["request_provenance"]["prompt_length"] + 1
    metadata_path = tmp_path / "prompt_length_mismatch.json"
    _write_captured_model_call_metadata(metadata_path, metadata)

    result = run_script(
        "ingest",
        "--run-dir",
        run_dir,
        "--raw-output-file",
        source_raw,
        "--model-call-metadata-file",
        metadata_path,
    )
    assert result.returncode != 0
    assert "prompt_length does not match run prompt artifact" in result.stderr


def test_ingest_with_response_sha_mismatch_fails_closed(tmp_path: Path):
    run_dir = _prepare_run(tmp_path, timestamp="20260707T171822Z")
    raw_text = _valid_raw_output_json()
    source_raw = tmp_path / "raw_model_output.txt"
    source_raw.write_text(raw_text, encoding="utf-8")
    metadata = _captured_model_call_metadata(
        prompt_text=(run_dir / "prompt_to_paste.md").read_text(encoding="utf-8"),
        raw_output_text=raw_text,
    )
    metadata["response_provenance"]["raw_output_sha256"] = "2" * 64
    metadata_path = tmp_path / "response_sha_mismatch.json"
    _write_captured_model_call_metadata(metadata_path, metadata)

    result = run_script(
        "ingest",
        "--run-dir",
        run_dir,
        "--raw-output-file",
        source_raw,
        "--model-call-metadata-file",
        metadata_path,
    )
    assert result.returncode != 0
    assert "response_provenance.raw_output_sha256 must match raw_output_sha256" in result.stderr


def test_ingest_with_response_length_mismatch_fails_closed(tmp_path: Path):
    run_dir = _prepare_run(tmp_path, timestamp="20260707T171823Z")
    raw_text = _valid_raw_output_json()
    source_raw = tmp_path / "raw_model_output.txt"
    source_raw.write_text(raw_text, encoding="utf-8")
    metadata = _captured_model_call_metadata(
        prompt_text=(run_dir / "prompt_to_paste.md").read_text(encoding="utf-8"),
        raw_output_text=raw_text,
    )
    metadata["response_provenance"]["raw_output_length"] = metadata["response_provenance"]["raw_output_length"] + 1
    metadata_path = tmp_path / "response_length_mismatch.json"
    _write_captured_model_call_metadata(metadata_path, metadata)

    result = run_script(
        "ingest",
        "--run-dir",
        run_dir,
        "--raw-output-file",
        source_raw,
        "--model-call-metadata-file",
        metadata_path,
    )
    assert result.returncode != 0
    assert "response_provenance.raw_output_length must match raw_output_length" in result.stderr


def test_ingest_with_failed_acquisition_status_fails_closed(tmp_path: Path):
    run_dir = _prepare_run(tmp_path, timestamp="20260707T171824Z")
    raw_text = _valid_raw_output_json()
    source_raw = tmp_path / "raw_model_output.txt"
    source_raw.write_text(raw_text, encoding="utf-8")
    metadata = _captured_model_call_metadata(
        prompt_text=(run_dir / "prompt_to_paste.md").read_text(encoding="utf-8"),
        raw_output_text=raw_text,
    )
    metadata["call_status"] = "failed"
    metadata_path = tmp_path / "failed_acquisition.json"
    _write_captured_model_call_metadata(metadata_path, metadata)

    result = run_script(
        "ingest",
        "--run-dir",
        run_dir,
        "--raw-output-file",
        source_raw,
        "--model-call-metadata-file",
        metadata_path,
    )
    assert result.returncode != 0
    assert "must represent a completed acquisition" in result.stderr


def test_call_local_materializes_prompt_copy_from_prepared_run(tmp_path: Path):
    run_dir = _prepare_run(tmp_path, timestamp="20260707T181825Z")
    result = _run_call_local_in_process(
        run_dir=run_dir,
        endpoint="http://127.0.0.1:8081/v1",
        model="Qwen_Qwen3-1.7B-Q4_K_M.gguf",
        response_body={"choices": [{"message": {"content": _valid_raw_output_json()}}]},
    )
    assert result.returncode == 0, result.stderr
    assert (run_dir / "prompt_to_paste.md").is_file()
    assert (run_dir / "raw_model_output.txt").is_file()
    assert (run_dir / "local_model_call.json").is_file()


def test_ingest_with_model_call_metadata_requires_acquisition_provenance(tmp_path: Path):
    run_dir = _prepare_run(tmp_path, timestamp="20260707T171819Z")
    raw_text = _valid_raw_output_json()
    source_raw = tmp_path / "raw_model_output.txt"
    source_raw.write_text(raw_text, encoding="utf-8")
    metadata = _captured_model_call_metadata(
        prompt_text=(run_dir / "model_prompt_packet.md").read_text(encoding="utf-8"),
        raw_output_text=raw_text,
    )
    del metadata["request_provenance"]
    metadata_path = tmp_path / "missing_request_provenance.json"
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = run_script(
        "ingest",
        "--run-dir",
        run_dir,
        "--raw-output-file",
        source_raw,
        "--model-call-metadata-file",
        metadata_path,
    )
    assert result.returncode != 0
    assert "must include request_provenance" in result.stderr


def test_prepare_prints_run_dir_and_ingest_prints_validation_status(tmp_path: Path):
    out_dir = tmp_path / "runs"
    ts = "20260707T151515Z"
    prepare_result = run_script(
        "prepare",
        "--messy-input",
        "Bounded input.",
        "--out-dir",
        out_dir,
        "--timestamp",
        ts,
    )
    assert prepare_result.returncode == 0
    assert "run_dir:" in prepare_result.stdout

    run_dir = out_dir / ts
    source_raw = tmp_path / "raw_model_output.txt"
    source_raw.write_text(_valid_raw_output_json(), encoding="utf-8")
    ingest_result = run_script(
        "ingest",
        "--run-dir",
        run_dir,
        "--raw-output-file",
        source_raw,
    )
    assert ingest_result.returncode == 0
    assert "validation_status:" in ingest_result.stdout


def test_ingest_invalid_cli_combination_requires_decision_reason(tmp_path: Path):
    run_dir = _prepare_run(tmp_path, timestamp="20260707T161616Z")
    source_raw = tmp_path / "raw_model_output.txt"
    source_raw.write_text(_valid_raw_output_json(), encoding="utf-8")

    result = run_script(
        "ingest",
        "--run-dir",
        run_dir,
        "--raw-output-file",
        source_raw,
        "--decision",
        "accepted",
    )
    assert result.returncode != 0
    assert "--decision-reason is required" in result.stderr
