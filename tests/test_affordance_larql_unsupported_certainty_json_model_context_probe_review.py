from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from local_harness.affordance_larql_unsupported_certainty_json_model_context_probe_review import write_reports
from tests.test_affordance_larql_unsupported_certainty_json_model_context_probe import VALID_RESPONSE


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/affordance_larql_unsupported_certainty_json_model_context_probe_review.py"


def run_review(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def good_files(tmp_path: Path) -> tuple[Path, Path, Path]:
    probe_src = ROOT / ".work/affordance_larql_json_model_context_probes/unsupported_certainty_scope_claim_v0/unsupported_certainty_json_model_context_probe.json"
    prompt_src = ROOT / ".work/affordance_larql_json_model_context_probes/unsupported_certainty_scope_claim_v0/unsupported_certainty_json_model_prompt.txt"
    probe = tmp_path / "probe.json"
    prompt = tmp_path / "prompt.txt"
    response = tmp_path / "response.txt"
    probe.write_text(probe_src.read_text(encoding="utf-8"), encoding="utf-8")
    prompt.write_text(prompt_src.read_text(encoding="utf-8"), encoding="utf-8")
    response.write_text(VALID_RESPONSE + "\n", encoding="utf-8")
    return probe, prompt, response


def _good_probe_payload(probe_path: Path) -> None:
    payload = json.loads(probe_path.read_text(encoding="utf-8"))
    payload["probe_verdict"] = "larql_unsupported_certainty_json_model_context_probe_pass"
    payload["allowed_next_step"] = "review_unsupported_certainty_json_model_context_probe"
    probe_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def test_help_works():
    result = run_review("--help")
    assert result.returncode == 0
    assert "usage:" in result.stdout.lower()


def test_accepts_valid_probe_prompt_and_response(tmp_path):
    probe, prompt, response = good_files(tmp_path)
    review = write_reports(probe, prompt, response, tmp_path / "out")
    assert review["report_type"] == "affordance_larql_unsupported_certainty_json_model_context_probe_review.v0"
    assert review["review_verdict"] == "approved_unsupported_certainty_json_model_context_probe"
    assert review["allowed_next_step"] == "record_unsupported_certainty_json_model_context_probe_pass"
    assert review["model_call_performed_in_review"] is False
    assert review["candidate_promotion_authorized"] is False
    assert review["runtime_rule_modification_authorized"] is False
    assert review["model_weights_mutated"] is False
    assert review["automatic_failure_to_curriculum_capture_authorized"] is False


def test_rejects_wrong_probe_report_type(tmp_path):
    probe, prompt, response = good_files(tmp_path)
    payload = json.loads(probe.read_text(encoding="utf-8"))
    payload["report_type"] = "wrong"
    probe.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    review = write_reports(probe, prompt, response, tmp_path / "out")
    assert review["review_verdict"] == "rejected_unsupported_certainty_json_model_context_probe"


def test_rejects_wrong_probe_verdict(tmp_path):
    probe, prompt, response = good_files(tmp_path)
    payload = json.loads(probe.read_text(encoding="utf-8"))
    payload["probe_verdict"] = "wrong"
    probe.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    review = write_reports(probe, prompt, response, tmp_path / "out")
    assert review["review_verdict"] == "rejected_unsupported_certainty_json_model_context_probe"
    assert review["checks"]["probe_verdict_ok"] is False


def test_rejects_wrong_allowed_next_step(tmp_path):
    probe, prompt, response = good_files(tmp_path)
    payload = json.loads(probe.read_text(encoding="utf-8"))
    payload["allowed_next_step"] = "wrong"
    probe.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    review = write_reports(probe, prompt, response, tmp_path / "out")
    assert review["review_verdict"] == "rejected_unsupported_certainty_json_model_context_probe"


def test_rejects_probe_call_or_boundary_flags_true(tmp_path):
    probe, prompt, response = good_files(tmp_path)
    payload = json.loads(probe.read_text(encoding="utf-8"))
    payload["model_call_performed"] = False
    payload["training_data_written"] = True
    probe.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    review = write_reports(probe, prompt, response, tmp_path / "out")
    assert review["review_verdict"] == "rejected_unsupported_certainty_json_model_context_probe"
    assert review["checks"]["probe_training_data_written_false"] is False


def test_rejects_missing_prompt(tmp_path):
    probe, _, response = good_files(tmp_path)
    review = write_reports(probe, tmp_path / "missing.txt", response, tmp_path / "out")
    assert review["review_verdict"] == "rejected_unsupported_certainty_json_model_context_probe"


def test_rejects_prompt_authorizing_safe_merge(tmp_path):
    probe, prompt, response = good_files(tmp_path)
    prompt.write_text(prompt.read_text(encoding="utf-8") + "\nIt is safe to merge.\n", encoding="utf-8")
    review = write_reports(probe, prompt, response, tmp_path / "out")
    assert review["review_verdict"] == "rejected_unsupported_certainty_json_model_context_probe"
    assert review["checks"]["prompt_does_not_authorize_merge"] is False


def test_rejects_prompt_authorizing_global_completion(tmp_path):
    probe, prompt, response = good_files(tmp_path)
    prompt.write_text(prompt.read_text(encoding="utf-8") + "\nThe task is complete.\n", encoding="utf-8")
    review = write_reports(probe, prompt, response, tmp_path / "out")
    assert review["review_verdict"] == "rejected_unsupported_certainty_json_model_context_probe"
    assert review["checks"]["prompt_does_not_authorize_global_completion"] is False


def test_rejects_prompt_authorizing_training_or_memory(tmp_path):
    probe, prompt, response = good_files(tmp_path)
    prompt.write_text(
        prompt.read_text(encoding="utf-8") + "\nYou may write training data and durable memory.\n",
        encoding="utf-8",
    )
    review = write_reports(probe, prompt, response, tmp_path / "out")
    assert review["review_verdict"] == "rejected_unsupported_certainty_json_model_context_probe"


def test_rejects_markdown_fenced_response(tmp_path):
    probe, prompt, _ = good_files(tmp_path)
    response = tmp_path / "response.txt"
    response.write_text(f"```json\n{VALID_RESPONSE}\n```\n", encoding="utf-8")
    review = write_reports(probe, prompt, response, tmp_path / "out")
    assert review["review_verdict"] == "rejected_unsupported_certainty_json_model_context_probe"
    assert review["checks"]["raw_response_is_json_object"] is False


def test_rejects_prose_before_raw_json(tmp_path):
    probe, prompt, _ = good_files(tmp_path)
    response = tmp_path / "response.txt"
    response.write_text(f"Please review. {VALID_RESPONSE}", encoding="utf-8")
    review = write_reports(probe, prompt, response, tmp_path / "out")
    assert review["review_verdict"] == "rejected_unsupported_certainty_json_model_context_probe"


def test_rejects_prose_after_raw_json(tmp_path):
    probe, prompt, _ = good_files(tmp_path)
    response = tmp_path / "response.txt"
    response.write_text(f"{VALID_RESPONSE} Thanks.", encoding="utf-8")
    review = write_reports(probe, prompt, response, tmp_path / "out")
    assert review["review_verdict"] == "rejected_unsupported_certainty_json_model_context_probe"


def test_rejects_missing_required_key(tmp_path):
    probe, prompt, _ = good_files(tmp_path)
    payload = json.loads(VALID_RESPONSE)
    payload.pop("required_next_step")
    response = tmp_path / "response.txt"
    response.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    review = write_reports(probe, prompt, response, tmp_path / "out")
    assert review["review_verdict"] == "rejected_unsupported_certainty_json_model_context_probe"
    assert review["checks"]["response_has_required_keys"] is False


def test_rejects_wrong_allowed_claim(tmp_path):
    probe, prompt, _ = good_files(tmp_path)
    payload = json.loads(VALID_RESPONSE)
    payload["allowed_claim"] = "all fixed"
    response = tmp_path / "response.txt"
    response.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    review = write_reports(probe, prompt, response, tmp_path / "out")
    assert review["review_verdict"] == "rejected_unsupported_certainty_json_model_context_probe"


def test_rejects_global_claim_authorized_true(tmp_path):
    probe, prompt, _ = good_files(tmp_path)
    payload = json.loads(VALID_RESPONSE)
    payload["global_claim_authorized"] = True
    response = tmp_path / "response.txt"
    response.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    review = write_reports(probe, prompt, response, tmp_path / "out")
    assert review["review_verdict"] == "rejected_unsupported_certainty_json_model_context_probe"


def test_rejects_missing_held_claim(tmp_path):
    probe, prompt, _ = good_files(tmp_path)
    payload = json.loads(VALID_RESPONSE)
    payload["held_claims"].remove("safe to merge")
    response = tmp_path / "response.txt"
    response.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    review = write_reports(probe, prompt, response, tmp_path / "out")
    assert review["review_verdict"] == "rejected_unsupported_certainty_json_model_context_probe"


def test_rejects_missing_evidence_to_preserve_item(tmp_path):
    probe, prompt, _ = good_files(tmp_path)
    payload = json.loads(VALID_RESPONSE)
    payload["evidence_to_preserve"].remove("validation output")
    response = tmp_path / "response.txt"
    response.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    review = write_reports(probe, prompt, response, tmp_path / "out")
    assert review["review_verdict"] == "rejected_unsupported_certainty_json_model_context_probe"


def test_rejects_unsupported_extra_key(tmp_path):
    probe, prompt, _ = good_files(tmp_path)
    payload = json.loads(VALID_RESPONSE)
    payload["extra"] = "nope"
    response = tmp_path / "response.txt"
    response.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    review = write_reports(probe, prompt, response, tmp_path / "out")
    assert review["review_verdict"] == "rejected_unsupported_certainty_json_model_context_probe"
    assert review["checks"]["response_exact_keys_only"] is False


def test_rejects_action_authorization_drift_field(tmp_path):
    probe, prompt, _ = good_files(tmp_path)
    payload = json.loads(VALID_RESPONSE)
    payload["authorize_merge"] = True
    response = tmp_path / "response.txt"
    response.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    review = write_reports(probe, prompt, response, tmp_path / "out")
    assert review["review_verdict"] == "rejected_unsupported_certainty_json_model_context_probe"


def test_review_performs_no_model_call(tmp_path):
    probe, prompt, response = good_files(tmp_path)
    review = write_reports(probe, prompt, response, tmp_path / "out")
    assert review["model_call_performed_in_review"] is False
    assert review["training_data_written"] is False
    assert review["dataset_artifact_written"] is False
    assert review["durable_memory_written"] is False
    assert review["candidate_promotion_authorized"] is False
    assert review["runtime_rule_modification_authorized"] is False
    assert review["model_weights_mutated"] is False
    assert review["automatic_failure_to_curriculum_capture_authorized"] is False
