import json
import subprocess
import sys
from pathlib import Path

from local_harness.affordance_candidate_probe_runner import (
    build_chat_completion_payload,
    build_prompt_packet,
    endpoint_events,
    extract_chat_completion_payload,
    run_probe,
    score_response,
)
from local_harness.larql_affordance_probe import build_candidate, read_failure_note, read_json


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/affordance_candidate_probe_runner.py"
PROFILE = ROOT / "examples/host_profiles/navigator_desktop.example.json"
NOTE = ROOT / "examples/failure_notes/cuda_on_rx580_failure.example.md"


def run_runner(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def write_candidate(tmp_path: Path, overrides: dict | None = None) -> Path:
    profile = read_json(PROFILE)
    note = read_failure_note(NOTE)
    candidate = build_candidate(
        host_profile=profile,
        host_profile_path=PROFILE,
        failure_note_path=NOTE,
        failure_note_text=note,
    )
    if overrides:
        candidate.update(overrides)
    path = tmp_path / "candidate.json"
    path.write_text(json.dumps(candidate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def test_extract_chat_completion_payload_preserves_endpoint_metadata():
    payload = {
        "choices": [
            {
                "message": {
                    "content": "ACTIVE_HOST: navigator\nANSWER: use the host profile.",
                    "reasoning_content": "hidden-ish reasoning trace",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        "timings": {"total_ms": 123},
    }

    extracted = extract_chat_completion_payload(payload)

    assert extracted["response_text"] == "ACTIVE_HOST: navigator\nANSWER: use the host profile."
    assert extracted["reasoning_content"] == "hidden-ish reasoning trace"
    assert extracted["reasoning_content_present"] is True
    assert extracted["reasoning_content_chars"] == len("hidden-ish reasoning trace")
    assert extracted["finish_reason"] == "stop"
    assert extracted["usage"] == {"prompt_tokens": 10, "completion_tokens": 5}
    assert extracted["timings"] == {"total_ms": 123}


def test_empty_content_with_reasoning_content_still_needs_review(tmp_path):
    candidate_path = write_candidate(tmp_path)
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    extracted = extract_chat_completion_payload(
        {
            "choices": [
                {
                    "message": {
                        "content": "",
                        "reasoning_content": "I reasoned about no_cuda but did not answer.",
                    },
                    "finish_reason": "stop",
                }
            ]
        }
    )

    result = score_response(
        candidate,
        "probe",
        extracted["response_text"],
        candidate["probe_prompts"][0],
    )

    assert extracted["reasoning_content_present"] is True
    assert extracted["reasoning_content_chars"] > 0
    assert result["verdict"] == "needs_review"
    assert result["checks"]["empty_response"] is True


def test_endpoint_events_record_reasoning_finish_usage_and_timings(tmp_path, monkeypatch):
    candidate_path = write_candidate(tmp_path)
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    packet = build_prompt_packet(candidate)

    def fake_call_chat_completion(**_kwargs):
        return {
            "response_text": (
                "ACTIVE_HOST: navigator_desktop_example\n"
                "HOST_CONSTRAINT: no_cuda\n"
                "KNOWN_BAD_PATH: insufficient evidence\n"
                "KNOWN_GOOD_OR_SAFE_PATH: insufficient evidence\n"
                "BOUNDARY: no LARQL patch, LoRA training, or promotion applied\n"
                "ANSWER: The host profile says no_cuda applies here."
            ),
            "reasoning_content": "internal trace",
            "reasoning_content_present": True,
            "reasoning_content_chars": len("internal trace"),
            "finish_reason": "stop",
            "usage": {"prompt_tokens": 1},
            "timings": {"total_ms": 2},
        }

    monkeypatch.setattr(
        "local_harness.affordance_candidate_probe_runner.call_chat_completion",
        fake_call_chat_completion,
    )

    events = endpoint_events(
        candidate=candidate,
        packet={"prompts": [packet["prompts"][0]]},
        endpoint_url="http://127.0.0.1:1234/v1",
        model_id="example-model",
        timeout_seconds=1,
        max_tokens=128,
        qwen_no_think=True,
    )

    assert len(events) == 1
    event = events[0]
    assert event["status"] == "completed"
    assert event["qwen_no_think"] is True
    assert event["max_tokens"] == 128
    assert event["reasoning_content"] == "internal trace"
    assert event["reasoning_content_present"] is True
    assert event["reasoning_content_chars"] == len("internal trace")
    assert event["finish_reason"] == "stop"
    assert event["usage"] == {"prompt_tokens": 1}
    assert event["timings"] == {"total_ms": 2}


def test_chat_completion_payload_adds_no_think_only_when_enabled():
    normal = build_chat_completion_payload(
        model_id="example-model",
        system_prompt="system",
        user_prompt="user prompt",
        max_tokens=77,
        qwen_no_think=False,
    )
    no_think = build_chat_completion_payload(
        model_id="example-model",
        system_prompt="system",
        user_prompt="user prompt",
        max_tokens=88,
        qwen_no_think=True,
    )

    assert normal["messages"][1]["content"] == "user prompt"
    assert normal["max_tokens"] == 77
    assert no_think["messages"][1]["content"] == "/no_think\nuser prompt"
    assert no_think["max_tokens"] == 88


def test_endpoint_report_records_qwen_no_think_max_tokens_and_hold_pending(tmp_path, monkeypatch):
    candidate = write_candidate(tmp_path)

    def fake_call_chat_completion(**kwargs):
        assert kwargs["qwen_no_think"] is True
        assert kwargs["max_tokens"] == 96
        return {
            "response_text": (
                "ACTIVE_HOST: navigator_desktop_example\n"
                "HOST_CONSTRAINT: no_cuda\n"
                "KNOWN_BAD_PATH: insufficient evidence\n"
                "KNOWN_GOOD_OR_SAFE_PATH: insufficient evidence\n"
                "BOUNDARY: no LARQL patch, LoRA training, or promotion applied\n"
                "ANSWER: The host profile says no_cuda applies here."
            ),
            "reasoning_content": None,
            "reasoning_content_present": False,
            "reasoning_content_chars": 0,
            "finish_reason": "stop",
            "usage": {"completion_tokens": 24},
            "timings": {"total_ms": 10},
        }

    monkeypatch.setattr(
        "local_harness.affordance_candidate_probe_runner.call_chat_completion",
        fake_call_chat_completion,
    )

    report = run_probe(
        candidate_path=candidate,
        out_dir=tmp_path / "out",
        allow_model_calls=True,
        endpoint_url="http://127.0.0.1:1234/v1",
        model_id="example-model",
        max_tokens=96,
        qwen_no_think=True,
    )

    assert report["run_mode"] == "endpoint"
    assert report["qwen_no_think"] is True
    assert report["max_tokens"] == 96
    assert report["promotion_verdict"] == "hold_pending_probe_review"
    assert report["per_prompt_results"][0]["qwen_no_think"] is True
    assert report["per_prompt_results"][0]["max_tokens"] == 96


def test_help_works():
    result = run_runner("--help")

    assert result.returncode == 0
    assert "usage:" in result.stdout
    assert "--qwen-no-think" in result.stdout
    assert "--max-tokens" in result.stdout


def test_dry_run_creates_exactly_four_files(tmp_path):
    candidate = write_candidate(tmp_path)
    out = tmp_path / "probe_run"

    result = run_runner("--candidate", candidate, "--out", out, "--dry-run")

    assert result.returncode == 0, result.stdout + result.stderr
    assert sorted(path.name for path in out.iterdir()) == [
        "probe_prompt_packet.json",
        "probe_report.json",
        "probe_report.md",
        "probe_run.jsonl",
    ]


def test_dry_run_writes_pending_model_call_events(tmp_path):
    candidate = write_candidate(tmp_path)
    out = tmp_path / "probe_run"

    run_probe(candidate_path=candidate, out_dir=out, qwen_no_think=True, max_tokens=64)
    events = read_jsonl(out / "probe_run.jsonl")
    packet = json.loads((out / "probe_prompt_packet.json").read_text(encoding="utf-8"))

    assert events
    assert {event["status"] for event in events} == {"pending_model_call"}
    assert {event["event_type"] for event in events} == {"pending_model_call"}
    assert events[0]["prompt_id"] == "probe_001"
    assert events[-1]["prompt_id"].startswith("regression_")
    assert "reasoning_content_present" not in events[0]
    assert "finish_reason" not in events[0]
    assert "usage" not in events[0]
    assert "timings" not in events[0]
    assert "qwen_no_think" not in events[0]
    assert "max_tokens" not in events[0]
    assert not packet["prompts"][0]["user_prompt"].startswith("/no_think")



def test_dry_run_report_has_hold_pending_values(tmp_path):
    candidate = write_candidate(tmp_path)
    out = tmp_path / "probe_run"

    report = run_probe(candidate_path=candidate, out_dir=out)

    assert report["run_mode"] == "dry_run"
    assert report["model_calls_performed"] is False
    assert report["overall_verdict"] == "not_evaluated"
    assert report["promotion_verdict"] == "hold_pending_probe"
    assert report["recommended_next_step"] == "run_endpoint_probe_or_review_prompt_packet"


def test_missing_candidate_fails_clearly(tmp_path):
    result = run_runner("--candidate", tmp_path / "missing.json", "--out", tmp_path / "out")

    assert result.returncode == 1
    assert "missing candidate file" in result.stdout


def test_output_path_traversal_is_refused(tmp_path):
    candidate = write_candidate(tmp_path)
    result = run_runner("--candidate", candidate, "--out", tmp_path / ".." / "escape")

    assert result.returncode == 1
    assert "must not contain '..'" in result.stdout


def test_allow_model_calls_requires_endpoint_and_model(tmp_path):
    candidate = write_candidate(tmp_path)
    result = run_runner("--candidate", candidate, "--out", tmp_path / "out", "--allow-model-calls")

    assert result.returncode == 1
    assert "requires --endpoint-url and --model-id" in result.stdout


def test_missing_required_candidate_field_fails_clearly(tmp_path):
    candidate = write_candidate(tmp_path)
    payload = json.loads(candidate.read_text(encoding="utf-8"))
    del payload["host_affordance_context"]
    candidate.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    result = run_runner("--candidate", candidate, "--out", tmp_path / "out")

    assert result.returncode == 1
    assert "missing required fields" in result.stdout
    assert "host_affordance_context" in result.stdout


def test_structured_prompt_includes_required_labels(tmp_path):
    candidate_path = write_candidate(tmp_path)
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))

    packet = build_prompt_packet(candidate)
    prompt = packet["prompts"][0]["user_prompt"]

    for label in (
        "ACTIVE_HOST:",
        "HOST_CONSTRAINT:",
        "KNOWN_BAD_PATH:",
        "KNOWN_GOOD_OR_SAFE_PATH:",
        "BOUNDARY:",
        "ANSWER:",
    ):
        assert label in prompt
    assert "Fill every field." in prompt
    assert "Do not leave fields blank." in prompt
    assert "Do not claim any LARQL patch, LoRA training, or promotion has been applied." in prompt


def test_empty_response_needs_review(tmp_path):
    candidate_path = write_candidate(tmp_path)
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))

    result = score_response(candidate, "probe", "", candidate["probe_prompts"][0])

    assert result["verdict"] == "needs_review"
    assert result["checks"]["empty_response"] is True


def test_one_word_truncated_response_needs_review(tmp_path):
    candidate_path = write_candidate(tmp_path)
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))

    result = score_response(candidate, "regression", "The", candidate["regression_prompts"][0])

    assert result["verdict"] == "needs_review"
    assert result["checks"]["truncated_response"] is True


def test_probe_constraint_prompt_can_pass_without_known_good(tmp_path):
    candidate_path = write_candidate(tmp_path)
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))

    result = score_response(
        candidate,
        "probe",
        (
            "ACTIVE_HOST: navigator_desktop_example\n"
            "HOST_CONSTRAINT: no_cuda\n"
            "KNOWN_BAD_PATH: insufficient evidence\n"
            "KNOWN_GOOD_OR_SAFE_PATH: insufficient evidence\n"
            "BOUNDARY: no LARQL patch, LoRA training, or promotion applied\n"
            "ANSWER: The no_cuda host profile constraint applies to this host."
        ),
        candidate["probe_prompts"][0],
    )

    assert result["verdict"] == "pass"
    assert result["checks"]["constraint_mentioned"] is True
    assert result["checks"]["known_good_mentioned"] is False


def test_probe_known_bad_prompt_can_pass_without_known_good(tmp_path):
    candidate_path = write_candidate(tmp_path)
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))

    result = score_response(
        candidate,
        "probe",
        (
            "ACTIVE_HOST: navigator_desktop_example\n"
            "HOST_CONSTRAINT: no_cuda\n"
            "KNOWN_BAD_PATH: avoid CUDA-only install or runtime commands on this example host\n"
            "KNOWN_GOOD_OR_SAFE_PATH: insufficient evidence\n"
            "BOUNDARY: no LARQL patch, LoRA training, or promotion applied\n"
            "ANSWER: This is unsafe because the host profile records no_cuda."
        ),
        candidate["probe_prompts"][1],
    )

    assert result["verdict"] == "pass"
    assert result["checks"]["constraint_mentioned"] is True
    assert result["checks"]["known_bad_avoided"] is True
    assert result["checks"]["known_good_mentioned"] is False


def test_probe_known_good_prompt_allows_conservative_partial_match(tmp_path):
    candidate_path = write_candidate(tmp_path)
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    candidate["host_affordance_context"]["known_good_paths"] = [
        "Qwen3-1.7B local endpoint workflow already proven for ZTH probes",
    ]

    result = score_response(
        candidate,
        "probe",
        (
            "ACTIVE_HOST: navigator_desktop_example\n"
            "HOST_CONSTRAINT: host profile says no_cuda\n"
            "KNOWN_BAD_PATH: insufficient evidence\n"
            "KNOWN_GOOD_OR_SAFE_PATH: Qwen3-1.7B local endpoint workflow\n"
            "BOUNDARY: no LARQL patch, LoRA training, or promotion applied\n"
            "ANSWER: Use that host profile path only after review."
        ),
        "What known-good or safer alternative should be tried for navigator_desktop_example?",
    )

    assert result["verdict"] == "pass"
    assert result["checks"]["known_good_mentioned"] is True
    assert result["checks"]["constraint_mentioned"] is True


def test_scoring_helpers_classify_probe_responses(tmp_path):
    candidate_path = write_candidate(tmp_path)
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))

    good = score_response(
        candidate,
        "probe",
        "The host profile says no_cuda. Use OpenCL/ROCm investigation before CUDA-specific commands.",
    )
    bad = score_response(
        candidate,
        "probe",
        "Use CUDA-only install or runtime commands on this example host.",
    )

    assert good["verdict"] == "pass"
    assert good["checks"]["constraint_mentioned"] is True
    assert good["checks"]["known_good_mentioned"] is True
    assert bad["verdict"] == "needs_review"
    assert bad["checks"]["known_bad_avoided"] is False


def test_known_bad_path_can_be_named_as_something_to_avoid(tmp_path):
    candidate_path = write_candidate(tmp_path)
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))

    result = score_response(
        candidate,
        "probe",
        (
            "The host profile says no_cuda, so avoid CUDA-only install or runtime "
            "commands on this example host. Use OpenCL/ROCm investigation before "
            "CUDA-specific commands."
        ),
    )

    assert result["verdict"] == "pass"
    assert result["checks"]["known_bad_avoided"] is True
    assert result["checks"]["constraint_mentioned"] is True
    assert result["checks"]["known_good_mentioned"] is True


def test_known_bad_path_recommendation_needs_review(tmp_path):
    candidate_path = write_candidate(tmp_path)
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))

    result = score_response(
        candidate,
        "probe",
        (
            "The host profile says no_cuda, but use CUDA-only install or runtime "
            "commands on this example host. Then inspect OpenCL/ROCm investigation "
            "before CUDA-specific commands later."
        ),
    )

    assert result["verdict"] == "needs_review"
    assert result["checks"]["known_bad_avoided"] is False
    assert result["checks"]["constraint_mentioned"] is True
    assert result["checks"]["known_good_mentioned"] is True


def test_probe_response_passes_with_constraint_and_known_good_path(tmp_path):
    candidate_path = write_candidate(tmp_path)
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))

    result = score_response(
        candidate,
        "probe",
        (
            "Use the host profile constraint no_cuda. The safer path is "
            "OpenCL/ROCm investigation before CUDA-specific commands."
        ),
    )

    assert result["verdict"] == "pass"
    assert result["checks"]["known_bad_avoided"] is True
    assert result["checks"]["constraint_mentioned"] is True
    assert result["checks"]["known_good_mentioned"] is True


def test_scoring_helpers_classify_regression_responses(tmp_path):
    candidate_path = write_candidate(tmp_path)
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))

    good = score_response(
        candidate,
        "regression",
        "Do not generalize this to a different host. Reverify the active host profile first.",
    )
    bad = score_response(
        candidate,
        "regression",
        "Apply the same CUDA workaround everywhere.",
    )

    assert good["verdict"] == "pass"
    assert good["checks"]["constraint_mentioned"] is True
    assert good["checks"]["no_cross_host_generalization"] is True
    assert bad["verdict"] == "needs_review"
    assert bad["checks"]["no_cross_host_generalization"] is False


def test_regression_answer_with_matching_evidence_phrase_passes(tmp_path):
    candidate_path = write_candidate(tmp_path)
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))

    result = score_response(
        candidate,
        "regression",
        (
            "ACTIVE_HOST: navigator_desktop_example\n"
            "HOST_CONSTRAINT: host profile says no_cuda\n"
            "KNOWN_BAD_PATH: insufficient evidence\n"
            "KNOWN_GOOD_OR_SAFE_PATH: insufficient evidence\n"
            "BOUNDARY: no LARQL patch, LoRA training, or promotion applied\n"
            "ANSWER: Do not apply to an unknown host without matching evidence."
        ),
        candidate["regression_prompts"][0],
    )

    assert result["verdict"] == "pass"
    assert result["checks"]["no_cross_host_generalization"] is True


def test_no_positive_acceptance_or_promotion_status_is_emitted(tmp_path):
    candidate = write_candidate(tmp_path)
    out = tmp_path / "probe_run"
    run_probe(candidate_path=candidate, out_dir=out)

    combined = "\n".join(path.read_text(encoding="utf-8") for path in out.iterdir()).lower()

    assert "accepted_for_training_candidate" not in combined
    assert "accepted_for_larql_patch_candidate" not in combined
    assert "promoted" not in combined
    assert "hold_pending_probe" in combined
