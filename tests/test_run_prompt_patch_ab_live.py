from __future__ import annotations

import hashlib
import json
from pathlib import Path
import pytest

from local_harness.run_prompt_patch_ab_live import (
    PromptPatchABLiveError,
    main,
    run_prompt_patch_ab_live,
)
from local_harness.run_prompt_patch_ab_harness import run_prompt_patch_ab_harness


def _write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")


class _FakeHTTPResponse:
    def __init__(self, content: str) -> None:
        self._content = content
        self.status = 200

    def read(self) -> bytes:
        return json.dumps(
            {
                "choices": [
                    {
                        "message": {
                            "content": self._content,
                        }
                    }
                ]
            }
        ).encode("utf-8")

    def __enter__(self) -> "_FakeHTTPResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def _make_json_response(content: str) -> _FakeHTTPResponse:
    return _FakeHTTPResponse(content)


def _prompt_paths(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    baseline = tmp_path / "baseline_prompt.txt"
    patched = tmp_path / "patched_prompt.txt"
    expected = tmp_path / "expected_contract.json"
    out_dir = tmp_path / "out"
    return baseline, patched, expected, out_dir


def _expected_contract() -> dict:
    return {
        "required_allowed_targets": ["docs/"],
        "required_held_targets": ["training/"],
        "required_json_fields": ["allowed_targets", "held_targets", "reason"],
        "forbidden_completion_claim": True,
        "requires_scope_expansion_flag": False,
    }


def _baseline_and_patched_outputs() -> tuple[str, str]:
    baseline = {
        "allowed_targets": ["docs/", "training/"],
        "held_targets": [],
        "scope_expansion_required": False,
        "reason": "still working",
    }
    patched = {
        "allowed_targets": ["docs/"],
        "held_targets": ["training/"],
        "scope_expansion_required": False,
        "reason": "bounded",
    }
    return json.dumps(baseline), json.dumps(patched)


def test_builds_identical_runtime_settings_payloads(monkeypatch, tmp_path: Path) -> None:
    baseline_prompt, patched_prompt, expected_contract, out_dir = _prompt_paths(tmp_path)
    _write_text(baseline_prompt, "baseline prompt\n")
    _write_text(patched_prompt, "patched prompt\n")
    _write_json(expected_contract, _expected_contract())

    seen_payloads: list[dict] = []

    def fake_urlopen(request, timeout):
        seen_payloads.append(json.loads(request.data.decode("utf-8")))
        content = _baseline_and_patched_outputs()[len(seen_payloads) - 1]
        return _make_json_response(content)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    run_prompt_patch_ab_live(
        case_id="case_001",
        failure_mode="scope_boundary",
        prompt_patch_id="scope_boundary_v1",
        task_summary="Keep allowed and held targets separated.",
        expected_contract_path=expected_contract,
        baseline_prompt_path=baseline_prompt,
        patched_prompt_path=patched_prompt,
        base_url="http://example.invalid/v1",
        model="test-model",
        out_dir=out_dir,
    )

    assert len(seen_payloads) == 2
    assert seen_payloads[0]["temperature"] == seen_payloads[1]["temperature"]
    assert seen_payloads[0]["max_tokens"] == seen_payloads[1]["max_tokens"]
    assert seen_payloads[0]["model"] == seen_payloads[1]["model"]


def test_writes_prompt_patch_ab_cases_json_and_scores_as_improved(monkeypatch, tmp_path: Path) -> None:
    baseline_prompt, patched_prompt, expected_contract, out_dir = _prompt_paths(tmp_path)
    _write_text(baseline_prompt, "baseline prompt\n")
    _write_text(patched_prompt, "patched prompt\n")
    _write_json(expected_contract, _expected_contract())

    responses = iter(_baseline_and_patched_outputs())

    def fake_urlopen(request, timeout):
        return _make_json_response(next(responses))

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    live_record = run_prompt_patch_ab_live(
        case_id="case_001",
        failure_mode="scope_boundary",
        prompt_patch_id="scope_boundary_v1",
        task_summary="Keep allowed and held targets separated.",
        expected_contract_path=expected_contract,
        baseline_prompt_path=baseline_prompt,
        patched_prompt_path=patched_prompt,
        base_url="http://example.invalid/v1",
        model="test-model",
        out_dir=out_dir,
    )

    cases_path = out_dir / "prompt_patch_ab_cases.json"
    assert cases_path.is_file()
    result = run_prompt_patch_ab_harness(cases_path)
    assert result["cases_total"] == 1
    assert result["improved_total"] == 1
    assert result["regressed_total"] == 0
    assert live_record["generated_cases_path"] == str(cases_path)


def test_expected_contract_malformed_exits_before_any_live_call(monkeypatch, tmp_path: Path) -> None:
    baseline_prompt, patched_prompt, expected_contract, out_dir = _prompt_paths(tmp_path)
    _write_text(baseline_prompt, "baseline prompt\n")
    _write_text(patched_prompt, "patched prompt\n")
    expected_contract.write_text("{not json}\n", encoding="utf-8")

    called = False

    def fake_urlopen(request, timeout):
        nonlocal called
        called = True
        raise AssertionError("endpoint should not be called")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    with pytest.raises(PromptPatchABLiveError, match="invalid JSON in expected contract"):
        run_prompt_patch_ab_live(
            case_id="case_001",
            failure_mode="scope_boundary",
            prompt_patch_id="scope_boundary_v1",
            task_summary="Keep allowed and held targets separated.",
            expected_contract_path=expected_contract,
            baseline_prompt_path=baseline_prompt,
            patched_prompt_path=patched_prompt,
            base_url="http://example.invalid/v1",
            model="test-model",
            out_dir=out_dir,
        )

    assert called is False


def test_invalid_assistant_json_exits_nonzero_and_preserves_raw_evidence(monkeypatch, tmp_path: Path) -> None:
    baseline_prompt, patched_prompt, expected_contract, out_dir = _prompt_paths(tmp_path)
    _write_text(baseline_prompt, "baseline prompt\n")
    _write_text(patched_prompt, "patched prompt\n")
    _write_json(expected_contract, _expected_contract())

    responses = iter(
        [
            _FakeHTTPResponse("not json"),
            _FakeHTTPResponse(
                json.dumps(
                    {
                        "allowed_targets": ["docs/"],
                        "held_targets": ["training/"],
                        "scope_expansion_required": False,
                        "reason": "bounded",
                    }
                )
            ),
        ]
    )

    def fake_urlopen(request, timeout):
        return next(responses)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    record = run_prompt_patch_ab_live(
        case_id="case_001",
        failure_mode="scope_boundary",
        prompt_patch_id="scope_boundary_v1",
        task_summary="Keep allowed and held targets separated.",
        expected_contract_path=expected_contract,
        baseline_prompt_path=baseline_prompt,
        patched_prompt_path=patched_prompt,
        base_url="http://example.invalid/v1",
        model="test-model",
        out_dir=out_dir,
    )

    assert record["diagnostics"]
    assert (out_dir / "baseline_response.raw.json").is_file()
    assert (out_dir / "patched_response.raw.json").is_file()
    assert not (out_dir / "prompt_patch_ab_cases.json").exists()


def test_live_record_includes_review_required_boundary_and_hides_base_url(monkeypatch, tmp_path: Path) -> None:
    baseline_prompt, patched_prompt, expected_contract, out_dir = _prompt_paths(tmp_path)
    _write_text(baseline_prompt, "baseline prompt\n")
    _write_text(patched_prompt, "patched prompt\n")
    _write_json(expected_contract, _expected_contract())

    responses = iter(_baseline_and_patched_outputs())

    def fake_urlopen(request, timeout):
        return _make_json_response(next(responses))

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    record = run_prompt_patch_ab_live(
        case_id="case_001",
        failure_mode="scope_boundary",
        prompt_patch_id="scope_boundary_v1",
        task_summary="Keep allowed and held targets separated.",
        expected_contract_path=expected_contract,
        baseline_prompt_path=baseline_prompt,
        patched_prompt_path=patched_prompt,
        base_url="http://secret.internal.example/v1",
        model="test-model",
        out_dir=out_dir,
    )

    assert record["review_required"] is True
    assert "explicit_operator_invoked" in record["authority_boundary"]
    assert "no_auto_promotion" in record["authority_boundary"]
    assert record["base_url_present"] is True
    assert "secret.internal.example" not in json.dumps(record)
    payload = json.loads((out_dir / "prompt_patch_ab_live_record.json").read_text(encoding="utf-8"))
    assert payload["review_required"] is True
    assert payload["base_url_present"] is True
    assert "secret.internal.example" not in json.dumps(payload)


def test_main_returns_nonzero_for_invalid_assistant_json_and_preserves_raw_evidence(
    monkeypatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    baseline_prompt, patched_prompt, expected_contract, out_dir = _prompt_paths(tmp_path)
    _write_text(baseline_prompt, "baseline prompt\n")
    _write_text(patched_prompt, "patched prompt\n")
    _write_json(expected_contract, _expected_contract())

    responses = iter(
        [
            _FakeHTTPResponse("not json"),
            _FakeHTTPResponse(
                json.dumps(
                    {
                        "allowed_targets": ["docs/"],
                        "held_targets": ["training/"],
                        "scope_expansion_required": False,
                        "reason": "bounded",
                    }
                )
            ),
        ]
    )

    def fake_urlopen(request, timeout):
        return next(responses)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    exit_code = main(
        [
            "--case-id",
            "case_001",
            "--failure-mode",
            "scope_boundary",
            "--prompt-patch-id",
            "scope_boundary_v1",
            "--task-summary",
            "Keep allowed and held targets separated.",
            "--expected-contract",
            str(expected_contract),
            "--baseline-prompt",
            str(baseline_prompt),
            "--patched-prompt",
            str(patched_prompt),
            "--base-url",
            "http://secret.internal.example/v1",
            "--model",
            "test-model",
            "--out-dir",
            str(out_dir),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "secret.internal.example" not in captured.out
    assert "secret.internal.example" not in captured.err
    assert (out_dir / "baseline_response.raw.json").is_file()
    assert (out_dir / "patched_response.raw.json").is_file()
    assert (out_dir / "prompt_patch_ab_live_record.json").is_file()
    assert not (out_dir / "prompt_patch_ab_cases.json").exists()


def test_main_returns_nonzero_for_malformed_expected_contract_before_calls(
    monkeypatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    baseline_prompt, patched_prompt, expected_contract, out_dir = _prompt_paths(tmp_path)
    _write_text(baseline_prompt, "baseline prompt\n")
    _write_text(patched_prompt, "patched prompt\n")
    expected_contract.write_text("{not json}\n", encoding="utf-8")

    called = False

    def fake_urlopen(request, timeout):
        nonlocal called
        called = True
        raise AssertionError("endpoint should not be called")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    exit_code = main(
        [
            "--case-id",
            "case_001",
            "--failure-mode",
            "scope_boundary",
            "--prompt-patch-id",
            "scope_boundary_v1",
            "--task-summary",
            "Keep allowed and held targets separated.",
            "--expected-contract",
            str(expected_contract),
            "--baseline-prompt",
            str(baseline_prompt),
            "--patched-prompt",
            str(patched_prompt),
            "--base-url",
            "http://example.invalid/v1",
            "--model",
            "test-model",
            "--out-dir",
            str(out_dir),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert called is False
    assert "invalid JSON in expected contract" in captured.err
