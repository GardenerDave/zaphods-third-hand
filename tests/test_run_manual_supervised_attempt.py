from __future__ import annotations

import hashlib
import json
import io
import subprocess
import sys
import threading
import socket
import unittest
import tempfile
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from contextlib import redirect_stdout, redirect_stderr
from unittest.mock import patch
import urllib.error

import local_harness.run_manual_supervised_attempt as manual_attempt
from local_harness.run_manual_supervised_attempt import run_prepare

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


def _extract_output_contract(rendered_prompt: str) -> dict:
    marker = "## Output Contract\n```json\n"
    start = rendered_prompt.index(marker) + len(marker)
    end = rendered_prompt.index("\n```", start)
    return json.loads(rendered_prompt[start:end])


def _captured_model_call_metadata(
    *,
    prompt_text: str,
    raw_output_text: str,
    model: str = "Qwen_Qwen3-1.7B-Q4_K_M.gguf",
    endpoint: str = "http://192.168.1.16:8081/v1",
    response_schema_path: Path | None = None,
    response_schema_source_path: Path | None = None,
) -> dict[str, object]:
    structured_output: dict[str, object] = {
        "enabled": response_schema_path is not None,
        "mechanism": "openai_json_schema" if response_schema_path is not None else None,
    }
    if response_schema_path is not None:
        structured_output["schema_path"] = response_schema_path.name
        structured_output["schema_sha256"] = manual_attempt._sha256_file(response_schema_path)
        structured_output["schema_length"] = len(response_schema_path.read_text(encoding="utf-8"))
    if response_schema_source_path is not None:
        structured_output["schema_source_path"] = str(response_schema_source_path)
    if response_schema_path is not None:
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "zth_structured_output",
                "strict": True,
                "schema": json.loads(response_schema_path.read_text(encoding="utf-8")),
            },
        }
        structured_output["response_format"] = json.loads(json.dumps(response_format))
    request_payload: dict[str, object] = {
        "model": model,
        "messages": [{"role": "user", "content": prompt_text}],
        "temperature": 0,
        "max_tokens": 1024,
    }
    if response_schema_path is not None:
        request_payload["response_format"] = json.loads(json.dumps(structured_output["response_format"]))
    request_body_text = json.dumps(request_payload)
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
        "request_body_sha256": manual_attempt._sha256_text(request_body_text),
        "request_body_length": len(request_body_text.encode("utf-8")),
        "structured_output": structured_output,
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
            "request_body_sha256": manual_attempt._sha256_text(request_body_text),
            "request_body_length": len(request_body_text.encode("utf-8")),
            "structured_output_enabled": response_schema_path is not None,
            "structured_output_mechanism": "openai_json_schema" if response_schema_path is not None else None,
            "response_format": json.loads(json.dumps(structured_output.get("response_format"))) if response_schema_path is not None else None,
        },
        "response_provenance": {
            "raw_output_path": "raw_model_output.txt",
            "raw_output_sha256": manual_attempt._sha256_text(raw_output_text),
            "raw_output_length": len(raw_output_text),
            "model": model,
            "structured_output": structured_output,
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


class RunManualSupervisedAttemptPromptPatchProjectionTests(unittest.TestCase):
    def test_evidence_prompt_includes_prompt_patch_delta_when_selected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            evidence_a = root / "evidence_a.md"
            evidence_b = root / "evidence_b.md"
            evidence_a.write_text("alpha\n", encoding="utf-8")
            evidence_b.write_text("beta\n", encoding="utf-8")

            baseline = run_prepare(
                messy_input="Does transport qualification prove model capability?",
                out_dir=root / "baseline",
                timestamp="20260831T140000Z",
                overwrite=True,
                exclude_prompt_patches=["unsupported_certainty_v1"],
                evidence_files=[evidence_a, evidence_b],
                evidence_task_title="Task A",
                evidence_task_summary="Transport qualification versus model capability.",
            )
            patched = run_prepare(
                messy_input="Does transport qualification prove model capability?",
                out_dir=root / "patched",
                timestamp="20260831T140000Z",
                overwrite=True,
                include_prompt_patches=["unsupported_certainty_v1"],
                evidence_files=[evidence_a, evidence_b],
                evidence_task_title="Task A",
                evidence_task_summary="Transport qualification versus model capability.",
            )

            baseline_prompt = Path(baseline["prompt_to_paste_path"]).read_text(encoding="utf-8")
            patched_prompt = Path(patched["prompt_to_paste_path"]).read_text(encoding="utf-8")

        self.assertNotEqual(
            hashlib.sha256(baseline_prompt.encode("utf-8")).hexdigest(),
            hashlib.sha256(patched_prompt.encode("utf-8")).hexdigest(),
        )
        self.assertNotIn("unsupported_certainty_v1", baseline_prompt)
        self.assertIn("unsupported_certainty_v1", patched_prompt)

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
    response_schema_file: Path | None = None,
    urlopen_side_effect=None,
) -> subprocess.CompletedProcess[str]:
    seen_request: dict[str, object] | None = None
    seen_request_raw: str | None = None

    def fake_urlopen(request, timeout=None):
        nonlocal seen_request
        nonlocal seen_request_raw
        _ = timeout
        if getattr(request, "data", None):
            seen_request_raw = request.data.decode("utf-8")
            seen_request = json.loads(seen_request_raw)
        else:
            seen_request_raw = None
            seen_request = None
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
                        *(
                            ["--response-schema-file", str(response_schema_file)]
                            if response_schema_file is not None
                            else []
                        ),
                        *(["--overwrite"] if overwrite else []),
                    ]
                )
        except SystemExit as exc:
            exit_code = int(exc.code or 0)
    stdout_text = stdout.getvalue()
    if seen_request_raw is not None:
        stdout_text += f"request_payload_bytes: {seen_request_raw}\n"
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


def test_prepare_with_evidence_files_projects_bounded_observation_packet(tmp_path: Path):
    run_dir = tmp_path / "runs"
    source_a = tmp_path / "source_a.txt"
    source_b = tmp_path / "source_b.txt"
    source_a.write_text("alpha\nbeta\ngamma\n", encoding="utf-8")
    source_b.write_text("delta\nepsilon\nzeta\n", encoding="utf-8")

    result = run_script(
        "prepare",
        "--messy-input",
        "Inspect repository evidence.",
        "--out-dir",
        run_dir,
        "--timestamp",
        "20260707T040405Z",
        "--evidence-file",
        source_a,
        "--evidence-file",
        source_b,
        "--evidence-task-title",
        "Read-only repo observation",
        "--evidence-task-summary",
        "Inspect supplied evidence only; do not browse the filesystem.",
        "--evidence-max-chars",
        "5",
    )
    assert result.returncode == 0
    run_path = run_dir / "20260707T040405Z"
    projection = json.loads((run_path / "evidence_projection.json").read_text(encoding="utf-8"))
    assert projection["task_title"] == "Read-only repo observation"
    assert projection["task_summary"] == "Inspect supplied evidence only; do not browse the filesystem."
    assert len(projection["evidence_sources"]) == 2
    assert projection["evidence_sources"][0]["path"] == str(source_a)
    assert projection["evidence_sources"][0]["sha256"] == manual_attempt._sha256_file(source_a)
    assert projection["evidence_sources"][0]["truncated"] is True
    assert projection["evidence_sources"][0]["excerpt"].endswith("[trimmed]")
    assert projection["output_contract"] == {
        "format": "json",
        "required_fields": ["findings", "reason"],
        "requires_reason": True,
    }
    prompt = (run_path / "prompt_to_paste.md").read_text(encoding="utf-8")
    assert "# ZTH Repository Observation Packet" in prompt
    assert "Read-only repo observation" in prompt
    assert "Inspect supplied evidence only; do not browse the filesystem." in prompt
    assert "findings" in prompt
    summary = json.loads((run_path / "prompt_projection_summary.json").read_text(encoding="utf-8"))
    assert summary["evidence_projection_path"] == "evidence_projection.json"
    assert summary["evidence_source_count"] == 2
    assert "evidence_output_contract_sha256" in summary
    assert summary["evidence_budget"]["status"] == "passed"
    assert summary["evidence_budget"]["any_source_truncated"] is True
    assert "Prompt Patch Provenance" in prompt
    assert "provenance metadata, not citable evidence sources" in prompt
    assert "Cite only paths from the Evidence Packet" in prompt


def test_prepare_with_evidence_files_fails_early_when_total_budget_overflows(tmp_path: Path):
    run_dir = tmp_path / "runs"
    source = tmp_path / "oversize.txt"
    source.write_text("x" * 2000, encoding="utf-8")

    result = run_script(
        "prepare",
        "--messy-input",
        "Inspect repository evidence.",
        "--out-dir",
        run_dir,
        "--timestamp",
        "20260707T040407Z",
        "--evidence-file",
        source,
        "--evidence-task-title",
        "Read-only repo observation",
        "--evidence-task-summary",
        "Inspect supplied evidence only; do not browse the filesystem.",
        "--evidence-max-chars",
        "2000",
        "--evidence-total-budget-tokens",
        "10",
        "--evidence-response-reserve-tokens",
        "5",
        "--evidence-overhead-tokens",
        "2",
    )
    assert result.returncode != 0
    assert "exceed available budget" in result.stderr
    run_path = run_dir / "20260707T040407Z"
    projection = json.loads((run_path / "evidence_projection.json").read_text(encoding="utf-8"))
    assert projection["budget"]["status"] == "failed"
    assert projection["budget"]["estimated_prompt_tokens"] > projection["budget"]["available_prompt_tokens"]


def test_prepare_to_ingest_round_trip_resolves_repo_relative_artifacts(tmp_path: Path):
    out_dir = Path(".work") / f"test_round_trip_{tmp_path.name}"
    timestamp = "20260831T180000Z"
    source = tmp_path / "evidence.txt"
    source.write_text("alpha\nbeta\n", encoding="utf-8")
    try:
        prepare_result = manual_attempt.run_prepare(
            messy_input="Inspect supplied evidence only.",
            out_dir=out_dir,
            timestamp=timestamp,
            overwrite=True,
            evidence_files=[source],
            evidence_task_title="Evidence inspection",
            evidence_task_summary="Use only the supplied evidence packet.",
            evidence_max_chars=100,
        )
        run_dir = prepare_result["run_dir"]
        raw_output = run_dir / "raw_model_output.txt"
        raw_output.write_text(
            json.dumps(
                {
                    "findings": [
                        {
                            "claim": "The supplied evidence source is projected correctly and can be grounded without path duplication.",
                            "evidence": [
                                {
                                    "path": str(source),
                                    "detail": "The evidence file was supplied directly to prepare and should remain the grounding source.",
                                }
                            ],
                        }
                    ],
                    "format": "json",
                    "required_fields_present": True,
                    "reason": "The output remains bounded and supervised.",
                }
            ),
            encoding="utf-8",
        )

        ingest_result = manual_attempt.run_ingest(
            run_dir=run_dir,
            raw_output_file=raw_output,
        )

        assert ingest_result["validation_status"] == "passed"
        evidence_projection = json.loads((run_dir / "evidence_projection.json").read_text(encoding="utf-8"))
        assert evidence_projection["evidence_sources"][0]["path"] == str(source)
    finally:
        if out_dir.exists():
            import shutil

            shutil.rmtree(out_dir)


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


def test_prepare_and_ingest_keep_prompt_patch_provenance_out_of_grounding(tmp_path: Path):
    run_dir = tmp_path / "runs"
    source = tmp_path / "evidence.txt"
    source.write_text("line one\nline two\n", encoding="utf-8")
    result = run_script(
        "prepare",
        "--messy-input",
        "Inspect supplied evidence only.",
        "--out-dir",
        run_dir,
        "--timestamp",
        "20260707T040410Z",
        "--evidence-file",
        source,
        "--evidence-task-title",
        "Evidence inspection",
        "--evidence-task-summary",
        "Use only the supplied evidence packet.",
    )
    assert result.returncode == 0
    run_path = run_dir / "20260707T040410Z"
    prompt = (run_path / "prompt_to_paste.md").read_text(encoding="utf-8")
    assert "Prompt Patch Provenance" in prompt
    assert "not citable evidence sources" in prompt
    assert "rendered_patch_deltas" in (run_path / "evidence_projection.json").read_text(encoding="utf-8")


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


def test_prepare_and_call_local_with_evidence_projection_uses_observation_contract(tmp_path: Path):
    run_dir = tmp_path / "runs"
    source = tmp_path / "evidence.txt"
    source.write_text("line one\nline two\n", encoding="utf-8")
    result = run_script(
        "prepare",
        "--messy-input",
        "Inspect supplied evidence only.",
        "--out-dir",
        run_dir,
        "--timestamp",
        "20260707T040406Z",
        "--evidence-file",
        source,
        "--evidence-task-title",
        "Evidence inspection",
        "--evidence-task-summary",
        "Use only the supplied evidence packet.",
    )
    assert result.returncode == 0
    run_path = run_dir / "20260707T040406Z"
    contract = json.loads((run_path / "output_contract.json").read_text(encoding="utf-8"))
    assert contract == {"format": "json", "required_fields": ["findings", "reason"], "requires_reason": True}
    assert "# ZTH Repository Observation Packet" in (run_path / "prompt_to_paste.md").read_text(encoding="utf-8")


def test_call_local_auto_attaches_evidence_response_schema(tmp_path: Path):
    run_dir = tmp_path / "runs"
    source = tmp_path / "evidence.txt"
    source.write_text("alpha\nbeta\n", encoding="utf-8")
    result = run_script(
        "prepare",
        "--messy-input",
        "Inspect supplied evidence only.",
        "--out-dir",
        run_dir,
        "--timestamp",
        "20260707T040408Z",
        "--evidence-file",
        source,
        "--evidence-task-title",
        "Evidence inspection",
        "--evidence-task-summary",
        "Use only the supplied evidence packet.",
        "--evidence-max-chars",
        "100",
    )
    assert result.returncode == 0
    run_path = run_dir / "20260707T040408Z"
    response_body = {"choices": [{"message": {"content": "{\"findings\": [], \"reason\": \"ok\"}"}}]}
    mock_response = io.BytesIO(json.dumps(response_body).encode("utf-8"))
    mock_response.status = 200  # type: ignore[attr-defined]
    mock_response.getcode = lambda: 200  # type: ignore[assignment]
    mock_response.__enter__ = lambda self=mock_response: self  # type: ignore[assignment]
    mock_response.__exit__ = lambda exc_type, exc, tb: False  # type: ignore[assignment]
    with patch("urllib.request.urlopen", return_value=mock_response):
        call_result = manual_attempt.run_call_local(
            run_dir=run_path,
            endpoint="http://127.0.0.1:9999/v1",
            model="Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf",
            max_tokens=64,
            timeout_seconds=5,
            temperature=0,
            overwrite=False,
        )
    assert call_result["endpoint"] == "http://127.0.0.1:9999/v1"
    request = json.loads((run_path / "local_model_call.json").read_text(encoding="utf-8"))
    assert request["request_provenance"]["structured_output_enabled"] is True
    assert request["request_provenance"]["structured_output_mechanism"] == "openai_json_schema"


def test_epistemic_response_schema_runs_through_canonical_validation(tmp_path: Path):
    run_dir = tmp_path / "runs"
    source = tmp_path / "evidence.txt"
    source.write_text("alpha\nbeta\n", encoding="utf-8")
    schema = ROOT / "local_harness" / "schemas" / "repo_observation_output_epistemic_schema.json"

    result = run_script(
        "prepare",
        "--messy-input",
        "Assess what the supplied evidence demonstrates about transport qualification and model capability.",
        "--out-dir",
        run_dir,
        "--timestamp",
        "20260707T040409Z",
        "--evidence-file",
        source,
        "--evidence-task-title",
        "Evidence inspection",
        "--evidence-task-summary",
        "Use only the supplied evidence packet.",
        "--response-schema-file",
        schema,
    )
    assert result.returncode == 0
    run_path = run_dir / "20260707T040409Z"
    projected_contract = json.loads((run_path / "output_contract.json").read_text(encoding="utf-8"))
    response_schema = json.loads((run_path / "response_schema.json").read_text(encoding="utf-8"))
    assert projected_contract == {
        "format": "json",
        "required_fields": ["conclusion", "findings", "reason"],
        "requires_reason": True,
    }
    assert response_schema == json.loads(schema.read_text(encoding="utf-8"))

    attempt_record = {
        "attempt_id": "manual_attempt_test",
        "orchestration_id": "orch_manual_test",
        "triage_id": "triage_manual_test",
        "prompt_packet_id": "prompt_packet_manual_test",
        "source_prompt_packet_path": str(run_path / "model_prompt_packet.md"),
        "raw_model_output": json.dumps(
            {
                "conclusion": {
                    "established": ["transport qualification occurred"],
                    "not_established": ["semantic model capability"],
                },
                "findings": [
                    {
                        "claim": "transport qualification occurred",
                        "evidence": [{"path": str(source), "detail": "alpha"}],
                    }
                ],
                "reason": "bounded evidence",
            }
        ),
        "model_metadata": {"model_id": "test", "provider": "test"},
        "operator_metadata": {"operator": "test", "review_required": True},
        "provenance": {
            "source": "captured_model_output",
            "input_artifact": "model_prompt_packet",
            "raw_output_preserved": True,
            "run_manifest_path": str(run_path / "run_manifest.json"),
            "raw_output_source_path": str(run_path / "raw_model_output.txt"),
        },
        "validation_status": "not_validated",
        "acceptance_status": "not_reviewed",
        "authority_boundaries": [
            "No command execution authority is granted.",
            "No direct file modification authority is granted.",
            "No automatic patch promotion authority is granted.",
            "No automatic training authority is granted.",
            "No default failure-to-curriculum capture authority is granted.",
            "Human review is required before downstream use.",
        ],
    }
    validation = manual_attempt.validate_supervised_attempt_output_against_contract(
        attempt_record=attempt_record,
        output_contract=projected_contract,
        validation_id="validation_test",
        validated_at="2026-08-31T00:00:00Z",
        projected_source_paths=[str(source)],
    )
    assert any(
        check["check_id"] == "epistemic_observation_schema" and check["status"] == "passed"
        for check in validation["checks"]
    )

    invalid_attempt = dict(attempt_record)
    invalid_attempt["raw_model_output"] = json.dumps(
        {
            "conclusion": {"established": [], "not_established": []},
            "findings": [
                {
                    "claim": "transport qualification occurred",
                    "evidence": [{"path": str(source), "detail": "alpha"}],
                }
            ],
            "reason": "bounded evidence",
        }
    )
    invalid_validation = manual_attempt.validate_supervised_attempt_output_against_contract(
        attempt_record=invalid_attempt,
        output_contract=projected_contract,
        validation_id="validation_test_invalid",
        validated_at="2026-08-31T00:00:00Z",
        projected_source_paths=[str(source)],
    )
    assert any(
        check["check_id"] == "epistemic_observation_schema" and check["status"] == "failed"
        for check in invalid_validation["checks"]
    )
    assert any("established" in diag for diag in invalid_validation["diagnostics"])


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
    assert "response_format" not in body
    request_raw = result.stdout.split("request_payload_bytes: ", 1)[1].splitlines()[0]

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
    assert metadata["request_body_sha256"] == manual_attempt._sha256_bytes(request_raw.encode("utf-8"))
    assert metadata["request_body_length"] == len(request_raw.encode("utf-8"))
    assert metadata["request_provenance"]["request_body_sha256"] == metadata["request_body_sha256"]
    assert metadata["request_provenance"]["request_body_length"] == metadata["request_body_length"]
    assert metadata["structured_output"]["enabled"] is False
    assert metadata["request_provenance"]["structured_output_enabled"] is False
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
    assert "response_format" not in json.dumps(body)
    assert not (run_dir / "review_decision.json").exists()
    assert not (run_dir / "downstream_use_gate.json").exists()
    assert not (run_dir / "handoff_packet.json").exists()


def test_call_local_with_response_schema_encodes_response_format_and_records_provenance(tmp_path: Path):
    run_dir, _ = _session_run(tmp_path, timestamp="20260707T212122Z")
    schema = run_dir / "response_schema.json"
    schema.write_text(
        json.dumps(
            {
                "type": "object",
                "properties": {
                    "reason": {"type": "string"},
                },
                "required": ["reason"],
                "additionalProperties": False,
            }
        ),
        encoding="utf-8",
    )
    result = _run_call_local_in_process(
        run_dir=run_dir,
        endpoint="http://127.0.0.1:65500/v1",
        model="qwen3-1.7b-gpu-40k",
        response_schema_file=schema,
        response_body={"choices": [{"message": {"content": "{\"reason\":\"local\"}"}}]},
    )

    assert result.returncode == 0
    body = json.loads(result.stdout.split("request_payload: ", 1)[1]) if "request_payload: " in result.stdout else None
    assert isinstance(body, dict)
    assert body["response_format"]["type"] == "json_schema"
    assert body["response_format"]["json_schema"]["name"] == "zth_structured_output"
    assert body["response_format"]["json_schema"]["strict"] is True
    assert body["response_format"]["json_schema"]["schema"]["required"] == ["reason"]
    request_raw = result.stdout.split("request_payload_bytes: ", 1)[1].splitlines()[0]

    metadata = json.loads((run_dir / "local_model_call.json").read_text(encoding="utf-8"))
    assert metadata["structured_output"]["enabled"] is True
    assert metadata["structured_output"]["mechanism"] == "openai_json_schema"
    assert metadata["structured_output"]["schema_path"] == "response_schema.json"
    assert metadata["structured_output"]["schema_sha256"] == manual_attempt._sha256_file(run_dir / "response_schema.json")
    assert metadata["structured_output"]["schema_length"] == len((run_dir / "response_schema.json").read_bytes())
    assert metadata["structured_output"]["response_format"] == body["response_format"]
    assert metadata["request_provenance"]["structured_output_enabled"] is True
    assert metadata["request_provenance"]["structured_output_mechanism"] == "openai_json_schema"
    assert metadata["request_provenance"]["response_format"]["json_schema"]["name"] == "zth_structured_output"
    assert metadata["request_provenance"]["response_format"] == body["response_format"]
    assert metadata["request_body_sha256"] == manual_attempt._sha256_bytes(request_raw.encode("utf-8"))
    assert metadata["request_body_length"] == len(request_raw.encode("utf-8"))
    assert metadata["response_provenance"]["structured_output"]["enabled"] is True
    assert (run_dir / "response_schema.json").read_text(encoding="utf-8") == schema.read_text(encoding="utf-8")


def test_prepare_with_explicit_response_schema_projects_schema_provenance(tmp_path: Path):
    run_dir = tmp_path / "runs"
    evidence = tmp_path / "evidence.txt"
    evidence.write_text("alpha\nbeta\n", encoding="utf-8")
    schema = tmp_path / "epistemic_schema.json"
    schema.write_text(
        json.dumps(
            {
                "type": "object",
                "additionalProperties": False,
                "required": ["conclusion", "findings", "reason"],
                "properties": {
                    "conclusion": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["established", "not_established"],
                        "properties": {
                            "established": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                            "not_established": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                        },
                    },
                    "findings": {"type": "array"},
                    "reason": {"type": "string"},
                },
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    result = run_script(
        "prepare",
        "--messy-input",
        "Inspect supplied evidence only.",
        "--out-dir",
        run_dir,
        "--timestamp",
        "20260707T040409Z",
        "--evidence-file",
        evidence,
        "--evidence-task-title",
        "Evidence inspection",
        "--evidence-task-summary",
        "Use only the supplied evidence packet.",
        "--evidence-max-chars",
        "100",
        "--response-schema-file",
        schema,
    )
    assert result.returncode == 0
    run_path = run_dir / "20260707T040409Z"
    projected_schema = json.loads((run_path / "response_schema.json").read_text(encoding="utf-8"))
    summary = json.loads((run_path / "prompt_projection_summary.json").read_text(encoding="utf-8"))
    evidence_packet = json.loads((run_path / "evidence_projection.json").read_text(encoding="utf-8"))
    assert projected_schema["required"] == ["conclusion", "findings", "reason"]
    assert summary["selected_response_schema_sha256"] == manual_attempt._sha256_file(schema)
    assert evidence_packet["response_schema"] == projected_schema


def test_call_local_preserves_endpoint_finish_reason_and_usage_when_present(tmp_path: Path):
    run_dir, _ = _session_run(tmp_path, timestamp="20260707T212122A")
    response_body = {
        "choices": [
            {
                "finish_reason": "length",
                "message": {"content": '{"reason":"local"}'},
            }
        ],
        "usage": {
            "prompt_tokens": 41,
            "completion_tokens": 17,
            "total_tokens": 58,
        },
    }
    result = _run_call_local_in_process(
        run_dir=run_dir,
        endpoint="http://127.0.0.1:65500/v1",
        model="qwen3-1.7b-gpu-40k",
        response_body=response_body,
    )

    assert result.returncode == 0
    metadata = json.loads((run_dir / "local_model_call.json").read_text(encoding="utf-8"))
    endpoint_response = metadata["response_provenance"]["endpoint_response"]
    assert endpoint_response["finish_reason"] == "length"
    assert endpoint_response["usage"] == {
        "prompt_tokens": 41,
        "completion_tokens": 17,
        "total_tokens": 58,
    }
    assert endpoint_response["response_status"] == 200
    assert "response_body_sha256" in endpoint_response
    assert metadata["raw_output_sha256"] == manual_attempt._sha256_text('{"reason":"local"}')
    assert not (run_dir / "local_model_call.failed.json").exists()


def test_call_local_preserves_absent_usage_fields_without_fabrication(tmp_path: Path):
    run_dir, _ = _session_run(tmp_path, timestamp="20260707T212122B")
    result = _run_call_local_in_process(
        run_dir=run_dir,
        endpoint="http://127.0.0.1:65500/v1",
        model="qwen3-1.7b-gpu-40k",
        response_body={"choices": [{"message": {"content": '{"reason":"local"}'}}]},
    )

    assert result.returncode == 0
    metadata = json.loads((run_dir / "local_model_call.json").read_text(encoding="utf-8"))
    endpoint_response = metadata["response_provenance"]["endpoint_response"]
    assert "finish_reason" not in endpoint_response
    assert "usage" not in endpoint_response
    assert endpoint_response["response_status"] == 200
    assert "response_body_sha256" in endpoint_response
    assert metadata["raw_output_sha256"] == manual_attempt._sha256_text('{"reason":"local"}')


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


def test_call_local_rejects_missing_response_schema_file(tmp_path: Path):
    run_dir, _ = _session_run(tmp_path, timestamp="20260707T222223Z")
    result = run_script(
        "call-local",
        "--run-dir",
        run_dir,
        "--endpoint",
        "http://127.0.0.1:65500/v1",
        "--model",
        "qwen3-1.7b-gpu-40k",
        "--response-schema-file",
        run_dir / "missing_response_schema.json",
    )
    assert result.returncode != 0
    assert "does not exist" in result.stderr


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


def test_ingest_with_explicit_accepted_review_writes_decision_only(tmp_path: Path):
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
    assert not (run_dir / "downstream_use_gate.json").exists()
    assert not (run_dir / "handoff_packet.json").exists()


def test_ingest_with_explicit_accepted_observation_review_writes_decision_only(tmp_path: Path):
    run_dir = _prepare_run(tmp_path, timestamp="20260707T101011Z")
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
    assert not (run_dir / "downstream_use_gate.json").exists()
    assert not (run_dir / "handoff_packet.json").exists()
    assert "gate_path" not in result.stdout
    assert "handoff_path" not in result.stdout


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
    assert (run_dir / "review_decision.json").is_file()
    assert not (run_dir / "downstream_use_gate.json").exists()
    assert not (run_dir / "handoff_packet.json").exists()


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
    assert (run_dir / "review_decision.json").is_file()
    assert not (run_dir / "downstream_use_gate.json").exists()
    assert not (run_dir / "handoff_packet.json").exists()


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


def test_ingest_with_model_call_metadata_rejects_held_target_mutation(tmp_path: Path):
    run_dir = _prepare_run(tmp_path, timestamp="20260707T151615Z")
    prompt_text = (run_dir / "prompt_to_paste.md").read_text(encoding="utf-8")
    source_raw = tmp_path / "raw_model_output.txt"
    raw_text = json.dumps(
        {
            "allowed_targets": ["docs/reports/"],
            "held_targets": [
                "docs/reports/production automation",
                "docs/reports/automatic curriculum capture",
                "docs/reports/automatic promotion",
                "docs/reports/implementation_packet",
            ],
            "scope_expansion_required": False,
            "claims": [],
            "evidence_basis": [],
            "unverified_claims": [],
            "format": "json",
            "required_fields_present": True,
            "reason": "The output remains bounded and supervised.",
        }
    )
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
    )
    assert result.returncode == 0
    validation = json.loads((run_dir / "output_validation.json").read_text(encoding="utf-8"))
    assert validation["validation_status"] == "failed"
    assert any(
        check["check_id"] == "held_target_preservation" and check["status"] == "failed"
        for check in validation["checks"]
    )


def test_ingest_with_structured_model_call_metadata_records_structured_output_provenance(tmp_path: Path):
    run_dir = _prepare_run(tmp_path, timestamp="20260707T151617Z")
    prompt_text = (run_dir / "prompt_to_paste.md").read_text(encoding="utf-8")
    source_raw = tmp_path / "raw_model_output.txt"
    raw_text = _valid_raw_output_json()
    source_raw.write_text(raw_text, encoding="utf-8")
    schema = run_dir / "response_schema.json"
    schema.write_text(
        json.dumps(
            {
                "type": "object",
                "properties": {"reason": {"type": "string"}},
                "required": ["reason"],
                "additionalProperties": False,
            }
        ),
        encoding="utf-8",
    )
    metadata = tmp_path / "local_model_call.json"
    metadata_payload = _captured_model_call_metadata(
        prompt_text=prompt_text,
        raw_output_text=raw_text,
        response_schema_path=schema,
        response_schema_source_path=schema,
    )
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
    assert attempt["provenance"]["source"] == "captured_model_output"
    assert attempt["provenance"]["structured_output"]["enabled"] is True
    assert attempt["provenance"]["structured_output"]["mechanism"] == "openai_json_schema"
    assert attempt["provenance"]["structured_output"]["schema_path"] == "response_schema.json"
    assert attempt["provenance"]["structured_output"]["schema_sha256"] == manual_attempt._sha256_file(schema)
    assert attempt["provenance"]["structured_output"]["schema_length"] == len(schema.read_bytes())
    assert "manual_operator_provided_model_output" not in json.dumps(attempt)


def test_prepare_projects_canonical_prompt_with_explicit_patch_includes(tmp_path: Path):
    result = run_script(
        "prepare",
        "--messy-input",
        "The LoRA and prompt injection work got messy. Build a bounded design packet.",
        "--out-dir",
        tmp_path / "runs",
        "--timestamp",
        "20260707T161616Z",
        "--include-prompt-patch",
        "allowed_held_mapping_v1",
        "--include-prompt-patch",
        "required_fields_boolean_v1",
        "--include-prompt-patch",
        "required_fields_boolean_v1",
    )
    assert result.returncode == 0
    run_dir = tmp_path / "runs" / "20260707T161616Z"
    prompt_packet = (run_dir / "model_prompt_packet.md").read_text(encoding="utf-8")
    prompt_copy = (run_dir / "prompt_to_paste.md").read_text(encoding="utf-8")
    summary = json.loads((run_dir / "prompt_projection_summary.json").read_text(encoding="utf-8"))
    canonical_output_contract = json.loads((run_dir / "canonical_output_contract.json").read_text(encoding="utf-8"))
    projected_output_contract = json.loads((run_dir / "output_contract.json").read_text(encoding="utf-8"))
    canonical_prompt_contract = _extract_output_contract(prompt_packet)
    prompt_contract = _extract_output_contract(prompt_copy)
    assert prompt_copy != prompt_packet
    assert "Patch: output_contract_v1" in prompt_packet
    assert "Patch: output_contract_v1" in prompt_copy
    assert "Patch: allowed_held_mapping_v1" in prompt_copy
    assert "Patch: required_fields_boolean_v1" in prompt_copy
    assert "Patch: unique_json_keys_v1" not in prompt_copy
    assert "Patch: single_pass_json_object_v1" not in prompt_copy
    assert prompt_copy.count("Patch: allowed_held_mapping_v1") == 1
    assert prompt_copy.count("Patch: required_fields_boolean_v1") == 1
    assert "scope_boundary_v1" in prompt_copy
    assert "unsupported_certainty_v1" in prompt_copy
    assert "output_contract_v1" in prompt_copy
    assert summary["canonical_selected_prompt_patches"] == [
        "scope_boundary_v1",
        "unsupported_certainty_v1",
        "output_contract_v1",
    ]
    assert summary["explicitly_included_prompt_patches"] == [
        "allowed_held_mapping_v1",
        "required_fields_boolean_v1",
    ]
    assert summary["explicitly_excluded_prompt_patches"] == []
    assert summary["final_selected_prompt_patches"] == [
        "scope_boundary_v1",
        "unsupported_certainty_v1",
        "output_contract_v1",
        "allowed_held_mapping_v1",
        "required_fields_boolean_v1",
    ]
    assert canonical_prompt_contract == canonical_output_contract
    assert prompt_contract == projected_output_contract
    assert summary["canonical_output_contract_sha256"] == manual_attempt._sha256_text(
        json.dumps(canonical_output_contract, indent=2, sort_keys=True) + "\n"
    )
    assert summary["projected_output_contract_sha256"] == manual_attempt._sha256_text(
        json.dumps(projected_output_contract, indent=2, sort_keys=True) + "\n"
    )
    assert summary["canonical_output_contract_path"] == "canonical_output_contract.json"
    assert summary["projected_output_contract_path"] == "output_contract.json"


def test_prepare_projection_include_and_exclude_is_deterministic(tmp_path: Path):
    result = run_script(
        "prepare",
        "--messy-input",
        "The LoRA and prompt injection work got messy. Build a bounded design packet.",
        "--out-dir",
        tmp_path / "runs",
        "--timestamp",
        "20260707T171717Z",
        "--include-prompt-patch",
        "unique_json_keys_v1",
        "--include-prompt-patch",
        "single_pass_json_object_v1",
        "--exclude-prompt-patch",
        "single_pass_json_object_v1",
    )
    assert result.returncode == 0
    run_dir = tmp_path / "runs" / "20260707T171717Z"
    prompt_copy = (run_dir / "prompt_to_paste.md").read_text(encoding="utf-8")
    summary = json.loads((run_dir / "prompt_projection_summary.json").read_text(encoding="utf-8"))
    assert "Patch: unique_json_keys_v1" in prompt_copy
    assert "Patch: single_pass_json_object_v1" not in prompt_copy
    assert summary["explicitly_included_prompt_patches"] == [
        "unique_json_keys_v1",
        "single_pass_json_object_v1",
    ]
    assert summary["explicitly_excluded_prompt_patches"] == ["single_pass_json_object_v1"]
    assert summary["final_selected_prompt_patches"] == [
        "scope_boundary_v1",
        "unsupported_certainty_v1",
        "output_contract_v1",
        "unique_json_keys_v1",
    ]


def test_ingest_with_structured_model_call_metadata_rejects_tampered_schema_provenance(tmp_path: Path):
    run_dir = _prepare_run(tmp_path, timestamp="20260707T151618Z")
    prompt_text = (run_dir / "prompt_to_paste.md").read_text(encoding="utf-8")
    source_raw = tmp_path / "raw_model_output.txt"
    raw_text = _valid_raw_output_json()
    source_raw.write_text(raw_text, encoding="utf-8")
    schema = run_dir / "response_schema.json"
    schema.write_text(
        json.dumps(
            {
                "type": "object",
                "properties": {"reason": {"type": "string"}},
                "required": ["reason"],
                "additionalProperties": False,
            }
        ),
        encoding="utf-8",
    )
    metadata = tmp_path / "local_model_call.json"
    metadata_payload = _captured_model_call_metadata(
        prompt_text=prompt_text,
        raw_output_text=raw_text,
        response_schema_path=schema,
        response_schema_source_path=schema,
    )
    metadata_payload["structured_output"]["schema_sha256"] = "0" * 64
    metadata_payload["request_provenance"]["response_format"]["json_schema"]["schema"]["required"] = ["reason"]
    _write_captured_model_call_metadata(metadata, metadata_payload)

    result = run_script(
        "ingest",
        "--run-dir",
        run_dir,
        "--raw-output-file",
        source_raw,
        "--model-call-metadata-file",
        metadata,
    )
    assert result.returncode != 0
    assert "structured_output.schema_sha256 does not match schema artifact" in result.stderr


def test_ingest_with_structured_model_call_metadata_rejects_response_format_mismatch(tmp_path: Path):
    run_dir = _prepare_run(tmp_path, timestamp="20260707T151618Z")
    prompt_text = (run_dir / "prompt_to_paste.md").read_text(encoding="utf-8")
    source_raw = tmp_path / "raw_model_output.txt"
    raw_text = _valid_raw_output_json()
    source_raw.write_text(raw_text, encoding="utf-8")
    schema = run_dir / "response_schema.json"
    schema.write_text(
        json.dumps(
            {
                "type": "object",
                "properties": {"reason": {"type": "string"}},
                "required": ["reason"],
                "additionalProperties": False,
            }
        ),
        encoding="utf-8",
    )
    metadata = tmp_path / "local_model_call.json"
    metadata_payload = _captured_model_call_metadata(
        prompt_text=prompt_text,
        raw_output_text=raw_text,
        response_schema_path=schema,
        response_schema_source_path=schema,
    )
    wrong_schema = json.loads(
        json.dumps(metadata_payload["request_provenance"]["response_format"]["json_schema"]["schema"])
    )
    wrong_schema["additionalProperties"] = True
    metadata_payload["structured_output"]["response_format"]["json_schema"]["schema"] = wrong_schema
    metadata_payload["request_provenance"]["response_format"]["json_schema"]["schema"] = wrong_schema
    _write_captured_model_call_metadata(metadata, metadata_payload)

    result = run_script(
        "ingest",
        "--run-dir",
        run_dir,
        "--raw-output-file",
        source_raw,
        "--model-call-metadata-file",
        metadata,
    )
    assert result.returncode != 0
    assert "structured_output.response_format.json_schema.schema must match response_schema.json" in result.stderr


def test_ingest_with_structured_model_call_metadata_rejects_request_body_mismatch(tmp_path: Path):
    run_dir = _prepare_run(tmp_path, timestamp="20260707T151618AZ")
    prompt_text = (run_dir / "prompt_to_paste.md").read_text(encoding="utf-8")
    source_raw = tmp_path / "raw_model_output.txt"
    raw_text = _valid_raw_output_json()
    source_raw.write_text(raw_text, encoding="utf-8")
    schema = run_dir / "response_schema.json"
    schema.write_text(
        json.dumps(
            {
                "type": "object",
                "properties": {"reason": {"type": "string"}},
                "required": ["reason"],
                "additionalProperties": False,
            }
        ),
        encoding="utf-8",
    )
    metadata = tmp_path / "local_model_call.json"
    metadata_payload = _captured_model_call_metadata(
        prompt_text=prompt_text,
        raw_output_text=raw_text,
        response_schema_path=schema,
        response_schema_source_path=schema,
    )
    metadata_payload["request_body_sha256"] = "0" * 64
    _write_captured_model_call_metadata(metadata, metadata_payload)

    result = run_script(
        "ingest",
        "--run-dir",
        run_dir,
        "--raw-output-file",
        source_raw,
        "--model-call-metadata-file",
        metadata,
    )
    assert result.returncode != 0
    assert "request_body_sha256 must match request_provenance.request_body_sha256" in result.stderr


def test_ingest_with_structured_model_call_metadata_rejects_request_body_length_mismatch(tmp_path: Path):
    run_dir = _prepare_run(tmp_path, timestamp="20260707T151618BZ")
    prompt_text = (run_dir / "prompt_to_paste.md").read_text(encoding="utf-8")
    source_raw = tmp_path / "raw_model_output.txt"
    raw_text = _valid_raw_output_json()
    source_raw.write_text(raw_text, encoding="utf-8")
    schema = run_dir / "response_schema.json"
    schema.write_text(
        json.dumps(
            {
                "type": "object",
                "properties": {"reason": {"type": "string"}},
                "required": ["reason"],
                "additionalProperties": False,
            }
        ),
        encoding="utf-8",
    )
    metadata = tmp_path / "local_model_call.json"
    metadata_payload = _captured_model_call_metadata(
        prompt_text=prompt_text,
        raw_output_text=raw_text,
        response_schema_path=schema,
        response_schema_source_path=schema,
    )
    metadata_payload["request_body_length"] = metadata_payload["request_body_length"] + 1
    _write_captured_model_call_metadata(metadata, metadata_payload)

    result = run_script(
        "ingest",
        "--run-dir",
        run_dir,
        "--raw-output-file",
        source_raw,
        "--model-call-metadata-file",
        metadata,
    )
    assert result.returncode != 0
    assert "request_body_length must match request_provenance.request_body_length" in result.stderr


def test_ingest_with_structured_model_call_metadata_rejects_unsupported_mechanism(tmp_path: Path):
    run_dir = _prepare_run(tmp_path, timestamp="20260707T151620Z")
    prompt_text = (run_dir / "prompt_to_paste.md").read_text(encoding="utf-8")
    source_raw = tmp_path / "raw_model_output.txt"
    raw_text = _valid_raw_output_json()
    source_raw.write_text(raw_text, encoding="utf-8")
    schema = run_dir / "response_schema.json"
    schema.write_text(
        json.dumps(
            {
                "type": "object",
                "properties": {"reason": {"type": "string"}},
                "required": ["reason"],
                "additionalProperties": False,
            }
        ),
        encoding="utf-8",
    )
    metadata = tmp_path / "local_model_call.json"
    metadata_payload = _captured_model_call_metadata(
        prompt_text=prompt_text,
        raw_output_text=raw_text,
        response_schema_path=schema,
        response_schema_source_path=schema,
    )
    metadata_payload["structured_output"]["mechanism"] = "unsupported_mechanism"
    _write_captured_model_call_metadata(metadata, metadata_payload)

    result = run_script(
        "ingest",
        "--run-dir",
        run_dir,
        "--raw-output-file",
        source_raw,
        "--model-call-metadata-file",
        metadata,
    )
    assert result.returncode != 0
    assert "structured_output.mechanism must be openai_json_schema" in result.stderr


def test_ingest_with_structured_model_call_metadata_rejects_failed_acquisition(tmp_path: Path):
    run_dir = _prepare_run(tmp_path, timestamp="20260707T151619Z")
    prompt_text = (run_dir / "prompt_to_paste.md").read_text(encoding="utf-8")
    source_raw = tmp_path / "raw_model_output.txt"
    raw_text = _valid_raw_output_json()
    source_raw.write_text(raw_text, encoding="utf-8")
    schema = run_dir / "response_schema.json"
    schema.write_text(
        json.dumps(
            {
                "type": "object",
                "properties": {"reason": {"type": "string"}},
                "required": ["reason"],
                "additionalProperties": False,
            }
        ),
        encoding="utf-8",
    )
    metadata = tmp_path / "local_model_call.json"
    metadata_payload = _captured_model_call_metadata(
        prompt_text=prompt_text,
        raw_output_text=raw_text,
        response_schema_path=schema,
        response_schema_source_path=schema,
    )
    metadata_payload["call_status"] = "failed"
    _write_captured_model_call_metadata(metadata, metadata_payload)

    result = run_script(
        "ingest",
        "--run-dir",
        run_dir,
        "--raw-output-file",
        source_raw,
        "--model-call-metadata-file",
        metadata,
    )
    assert result.returncode != 0
    assert "must represent a completed acquisition" in result.stderr


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
