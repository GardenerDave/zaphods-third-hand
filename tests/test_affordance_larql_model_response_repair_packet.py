import json
import subprocess
import sys
from pathlib import Path

from local_harness.affordance_larql_model_response_probe import write_reports as write_probe
from local_harness.affordance_larql_model_response_repair_packet import write_reports
from local_harness.affordance_larql_model_response_review import write_reports as write_review
from tests.test_affordance_larql_model_context_packet import ready_inputs
from tests.test_affordance_larql_model_response_probe import fake_urlopen


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/affordance_larql_model_response_repair_packet.py"


def run_packet(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def ready_review(tmp_path: Path, response_text: str):
    consultation, runtime_rule = ready_inputs(tmp_path)
    packet_dir = tmp_path / "packet"
    from local_harness.affordance_larql_model_context_packet import write_reports as write_packet
    import os
    from unittest.mock import patch

    write_packet(
        consultation,
        runtime_rule,
        "I need CUDA working on this RX580 box so I can train the small model locally. Should I install NVIDIA CUDA?",
        packet_dir,
    )
    packet = packet_dir / "larql_model_context_packet.json"
    probe_dir = tmp_path / "probe"
    os.environ["ZTH_ENDPOINT_URL"] = "http://example.invalid/v1"
    os.environ["ZTH_MODEL_ID"] = "test-model"
    with patch(
        "local_harness.affordance_larql_model_response_probe.request.urlopen",
        return_value=fake_urlopen(response_text),
    ):
        write_probe(packet, probe_dir)
    probe = probe_dir / "larql_model_response_probe.json"
    review_dir = tmp_path / "review"
    write_review(probe, probe_dir / "model_response.txt", review_dir)
    return review_dir / "larql_model_response_review.json"


def repair_review_text() -> str:
    return "The RX580/no_cuda host should not install NVIDIA CUDA. Use the recommended local endpoint path."


def test_help_works():
    result = run_packet("--help")
    assert result.returncode == 0
    assert "usage:" in result.stdout


def test_missing_review_fails_closed(tmp_path):
    report = write_reports(tmp_path / "missing.json", tmp_path / "out")
    assert report["packet_verdict"] == "invalid_input"


def test_malformed_review_fails_closed(tmp_path):
    review = tmp_path / "review.json"
    review.write_text("{not json\n", encoding="utf-8")
    report = write_reports(review, tmp_path / "out")
    assert report["packet_verdict"] == "invalid_input"


def test_wrong_report_type_fails_closed(tmp_path):
    review = ready_review(
        tmp_path,
        repair_review_text(),
    )
    payload = json.loads(review.read_text(encoding="utf-8"))
    payload["report_type"] = "wrong"
    review.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = write_reports(review, tmp_path / "out")
    assert report["packet_verdict"] == "invalid_input"


def test_wrong_allowed_next_step_fails_closed(tmp_path):
    review = ready_review(
        tmp_path,
        repair_review_text(),
    )
    payload = json.loads(review.read_text(encoding="utf-8"))
    payload["allowed_next_step"] = "wrong"
    review.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = write_reports(review, tmp_path / "out")
    assert report["packet_verdict"] == "invalid_input"


def test_pass_review_is_rejected(tmp_path):
    review = ready_review(
        tmp_path,
        "The RX580/no_cuda host should not install NVIDIA CUDA. Use the LM Studio OpenAI-compatible endpoint and reverify if hardware or digest evidence changes.",
    )
    payload = json.loads(review.read_text(encoding="utf-8"))
    payload["review_verdict"] = "larql_model_response_review_pass"
    review.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = write_reports(review, tmp_path / "out")
    assert report["packet_verdict"] == "invalid_input"


def test_boundary_flags_true_fail_closed(tmp_path):
    review = ready_review(
        tmp_path,
        repair_review_text(),
    )
    payload = json.loads(review.read_text(encoding="utf-8"))
    payload["candidate_promoted"] = True
    review.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = write_reports(review, tmp_path / "out")
    assert report["packet_verdict"] == "invalid_input"


def test_missing_ids_digest_fail_closed(tmp_path):
    review = ready_review(
        tmp_path,
        repair_review_text(),
    )
    payload = json.loads(review.read_text(encoding="utf-8"))
    payload["candidate_digest"] = ""
    review.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = write_reports(review, tmp_path / "out")
    assert report["packet_verdict"] == "invalid_input"


def test_current_review_produces_packet_with_two_targets(tmp_path):
    review = ready_review(
        tmp_path,
        repair_review_text(),
    )
    out_dir = tmp_path / "out"
    report = write_reports(review, out_dir)
    assert report["packet_verdict"] == "ready_for_larql_model_response_repair_review"
    payload = json.loads((out_dir / "larql_model_response_repair_packet.json").read_text(encoding="utf-8"))
    assert [item["target_file"] for item in payload["proposed_repairs"]] == [
        "local_harness/affordance_larql_model_context_packet.py",
        "local_harness/affordance_larql_model_response_review.py",
    ]


def test_packet_includes_exact_lm_studio_instruction_repair(tmp_path):
    review = ready_review(
        tmp_path,
        repair_review_text(),
    )
    report = write_reports(review, tmp_path / "out")
    repair = report["proposed_repairs"][0]
    text = "\n".join(repair["required_changes"])
    assert repair["target_file"] == "local_harness/affordance_larql_model_context_packet.py"
    assert "required answer skeleton" in text
    assert "No, do not install NVIDIA CUDA on this RX580/no_cuda host." in text
    assert "Use the LM Studio OpenAI-compatible endpoint." in text
    assert "current host/profile/GPU/endpoint/digest evidence" in text
    assert "Reverify if host, GPU, driver, profile, endpoint, or digest evidence changes." in text
    assert "OpenAI Inference API" in text
    assert "PyTorch with a different compatible GPU" in text


def test_packet_includes_review_drift_coverage_repair(tmp_path):
    review = ready_review(
        tmp_path,
        repair_review_text(),
    )
    report = write_reports(review, tmp_path / "out")
    repair = report["proposed_repairs"][1]
    text = "\\n".join(repair["required_changes"])
    assert repair["target_file"] == "local_harness/affordance_larql_model_response_review.py"
    assert "cloud-based service" in text
    assert "compatible GPU" in text
    assert "PyTorch with a compatible GPU" in text
    assert "endpoint/path drift" in text
    assert "model-response review coverage" in text

def test_authorization_flags_false(tmp_path):
    review = ready_review(
        tmp_path,
        repair_review_text(),
    )
    report = write_reports(review, tmp_path / "out")
    assert report["durable_memory_authorized"] is False
    assert report["candidate_promotion_authorized"] is False
    assert report["lora_training_authorized"] is False
    assert report["model_weight_mutation_authorized"] is False
