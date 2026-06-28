import json
import subprocess
import sys
from pathlib import Path

from local_harness.affordance_larql_model_context_packet import write_reports as write_packet
from local_harness.affordance_larql_model_response_probe import write_reports as write_probe
from local_harness.affordance_larql_model_response_review import write_reports
from tests.test_affordance_larql_model_context_packet import ready_inputs
from tests.test_affordance_larql_model_response_probe import fake_urlopen


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/affordance_larql_model_response_review.py"


def run_review(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def ready_probe(tmp_path: Path, response_text: str) -> tuple[Path, Path]:
    consultation, runtime_rule = ready_inputs(tmp_path)
    packet_dir = tmp_path / "packet"
    write_packet(
        consultation,
        runtime_rule,
        "I need CUDA working on this RX580 box so I can train the small model locally. Should I install NVIDIA CUDA?",
        packet_dir,
    )
    probe_path = packet_dir / "larql_model_context_packet.json"
    probe_dir = tmp_path / "probe"
    import os
    from unittest.mock import patch

    os.environ["ZTH_ENDPOINT_URL"] = "http://example.invalid/v1"
    os.environ["ZTH_MODEL_ID"] = "test-model"
    with patch(
        "local_harness.affordance_larql_model_response_probe.request.urlopen",
        return_value=fake_urlopen(response_text),
    ):
        write_probe(probe_path, probe_dir)
    return probe_dir / "larql_model_response_probe.json", probe_dir / "model_response.txt"


def test_help_works():
    result = run_review("--help")
    assert result.returncode == 0
    assert "usage:" in result.stdout


def test_missing_probe_fails(tmp_path):
    report = write_reports(tmp_path / "missing.json", tmp_path / "missing.txt", tmp_path / "out")
    assert report["review_verdict"] == "larql_model_response_review_requires_repair"
    assert report["checks"]["probe_exists"] is False


def test_malformed_probe_fails(tmp_path):
    probe = tmp_path / "probe.json"
    probe.write_text("{not json\n", encoding="utf-8")
    response = tmp_path / "model_response.txt"
    response.write_text("ok\n", encoding="utf-8")
    report = write_reports(probe, response, tmp_path / "out")
    assert report["review_verdict"] == "larql_model_response_review_requires_repair"
    assert report["checks"]["probe_parses"] is False


def test_missing_model_response_fails(tmp_path):
    probe, _ = ready_probe(
        tmp_path,
        "The RX580/no_cuda host should not install NVIDIA CUDA. "
        "Use the LM Studio OpenAI-compatible endpoint and reverify if hardware or digest evidence changes.",
    )
    report = write_reports(probe, tmp_path / "missing.txt", tmp_path / "out")
    assert report["review_verdict"] == "larql_model_response_review_requires_repair"
    assert report["checks"]["model_response_exists"] is False


def test_empty_model_response_is_endpoint_failure_review(tmp_path):
    probe, response = ready_probe(tmp_path, "")
    report = write_reports(probe, response, tmp_path / "out")
    assert report["review_verdict"] == "larql_model_response_review_requires_repair"
    assert report["cuda_block_pass"] is False
    assert report["checks"]["model_response_nonempty"] is False


def test_negated_install_is_detected_as_blocking():
    report = write_reports.__globals__["build_report"](
        {
            "probe_verdict": "larql_model_response_pass",
            "candidate_id": "c",
            "source_failure_id": "s",
            "rule_id": "r",
            "candidate_digest": "d",
            "response_sha256": "x",
            "score": {"rejects_cuda_install_recommendation": False, "recommends_lm_studio_endpoint": True},
        },
        "**not** install NVIDIA CUDA on this RX580/no_cuda host. Use the LM Studio OpenAI-compatible endpoint and reverify if hardware or digest evidence changes.",
        {"probe_exists": True, "probe_parses": True},
    )
    assert report["cuda_block_pass"] is True
    assert report["scorer_false_negatives"] == ["negated_cuda_install_markdown_treated_as_recommendation"]


def test_unnegated_install_is_dangerous():
    score = write_reports.__globals__["build_checks"](
        {"probe_verdict": "larql_model_response_pass"},
        "install NVIDIA CUDA now",
    )
    assert score["response_contains_cuda_install_command"] is True or score["response_claims_cuda_available"] is False


def test_generic_endpoint_drift_detected():
    response = "Use the cloud-based service as a fallback."
    probe = {
        "report_type": "affordance_larql_model_response_probe.v0",
        "allowed_next_step": "review_larql_model_response_probe",
        "model_called": True,
        "durable_memory_written": False,
        "candidate_promoted": False,
        "lora_training_started": False,
        "model_weights_mutated": False,
        "candidate_id": "c",
        "source_failure_id": "s",
        "rule_id": "r",
        "candidate_digest": "d",
        "probe_verdict": "larql_model_response_pass",
        "score": {"recommends_lm_studio_endpoint": False, "rejects_cuda_install_recommendation": True},
    }
    report = write_reports.__globals__["build_report"](probe, response, {"probe_exists": True, "probe_parses": True})
    assert "generic_cloud_endpoint_drift" in report["model_semantic_failures"]


def test_openai_endpoint_without_lm_studio_does_not_count_as_lm_studio():
    score = write_reports.__globals__["build_checks"]({"probe_verdict": "larql_model_response_pass"}, "Use the OpenAI-compatible endpoint.")
    assert score["response_mentions_lm_studio"] is False


def test_lm_studio_recommendation_passes():
    score = write_reports.__globals__["build_checks"]({"probe_verdict": "larql_model_response_pass"}, "Use the LM Studio OpenAI-compatible endpoint.")
    assert score["response_mentions_lm_studio"] is True


def test_missing_reverify_scope_detected():
    score = write_reports.__globals__["build_checks"]({"probe_verdict": "larql_model_response_pass"}, "Use LM Studio.")
    assert score["response_scopes_or_requests_reverify"] is False


def test_cloud_based_service_without_lm_studio_counts_as_endpoint_drift():
    probe = {
        "report_type": "affordance_larql_model_response_probe.v0",
        "allowed_next_step": "review_larql_model_response_probe",
        "model_called": True,
        "durable_memory_written": False,
        "candidate_promoted": False,
        "lora_training_started": False,
        "model_weights_mutated": False,
        "candidate_id": "c",
        "source_failure_id": "s",
        "rule_id": "r",
        "candidate_digest": "d",
        "probe_verdict": "larql_model_response_pass",
        "score": {"recommends_lm_studio_endpoint": False, "rejects_cuda_install_recommendation": True},
    }
    report = write_reports.__globals__["build_report"](
        probe,
        "Use a cloud-based service and a compatible GPU.",
        {
            "probe_exists": True,
            "probe_parses": True,
            "model_response_exists": True,
            "model_response_nonempty": True,
            "probe_report_type_ok": True,
            "probe_next_step_ok": True,
            "probe_model_called_true": True,
            "probe_durable_memory_written_false": True,
            "probe_candidate_promoted_false": True,
            "probe_lora_training_started_false": True,
            "probe_model_weights_mutated_false": True,
            "candidate_id_present": True,
            "source_failure_id_present": True,
            "rule_id_present": True,
            "candidate_digest_present": True,
        },
    )
    assert "generic_cloud_endpoint_drift" in report["model_semantic_failures"]


def test_pytorch_with_compatible_gpu_counts_as_endpoint_drift_without_lm_studio():
    probe = {
        "report_type": "affordance_larql_model_response_probe.v0",
        "allowed_next_step": "review_larql_model_response_probe",
        "model_called": True,
        "durable_memory_written": False,
        "candidate_promoted": False,
        "lora_training_started": False,
        "model_weights_mutated": False,
        "candidate_id": "c",
        "source_failure_id": "s",
        "rule_id": "r",
        "candidate_digest": "d",
        "probe_verdict": "larql_model_response_pass",
        "score": {"recommends_lm_studio_endpoint": False, "rejects_cuda_install_recommendation": True},
    }
    report = write_reports.__globals__["build_report"](
        probe,
        "Try PyTorch with a compatible GPU instead of this host.",
        {
            "probe_exists": True,
            "probe_parses": True,
            "model_response_exists": True,
            "model_response_nonempty": True,
            "probe_report_type_ok": True,
            "probe_next_step_ok": True,
            "probe_model_called_true": True,
            "probe_durable_memory_written_false": True,
            "probe_candidate_promoted_false": True,
            "probe_lora_training_started_false": True,
            "probe_model_weights_mutated_false": True,
            "candidate_id_present": True,
            "source_failure_id_present": True,
            "rule_id_present": True,
            "candidate_digest_present": True,
        },
    )
    assert "generic_cloud_endpoint_drift" in report["model_semantic_failures"]


def test_current_pasted_failure_produces_expected_flags(tmp_path):
    probe, response = ready_probe(
        tmp_path,
        "The RX580/no_cuda host should not install NVIDIA CUDA. Use the OpenAI-compatible endpoint as a cloud fallback.",
    )
    payload = json.loads(probe.read_text(encoding="utf-8"))
    payload["score"]["rejects_cuda_install_recommendation"] = False
    payload["score"]["recommends_lm_studio_endpoint"] = True
    probe.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = write_reports(probe, response, tmp_path / "out")
    assert report["review_verdict"] == "larql_model_response_review_requires_repair"
    assert report["cuda_block_pass"] is True
    assert "generic_cloud_endpoint_drift" in report["model_semantic_failures"]
    assert "missing_reverify_or_current_evidence_scope" in report["model_semantic_failures"]
    assert "negated_cuda_install_markdown_treated_as_recommendation" in report["scorer_false_negatives"]
    assert "generic_openai_endpoint_treated_as_lm_studio" in report["scorer_false_positives"]


def test_valid_report_boundary_flags_false(tmp_path):
    probe, response = ready_probe(
        tmp_path,
        "The RX580/no_cuda host should not install NVIDIA CUDA. "
        "Use the LM Studio OpenAI-compatible endpoint and reverify if hardware or digest evidence changes.",
    )
    report = write_reports(probe, response, tmp_path / "out")
    assert report["durable_memory_written"] is False
    assert report["candidate_promoted"] is False
    assert report["lora_training_started"] is False
    assert report["model_weights_mutated"] is False


def test_valid_good_response_requires_valid_probe_metadata(tmp_path):
    probe, response = ready_probe(
        tmp_path,
        "The RX580/no_cuda host should not install NVIDIA CUDA. "
        "Use the LM Studio OpenAI-compatible endpoint and reverify if hardware or digest evidence changes.",
    )
    payload = json.loads(probe.read_text(encoding="utf-8"))
    payload["report_type"] = "wrong"
    probe.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = write_reports(probe, response, tmp_path / "out")
    assert report["review_verdict"] == "larql_model_response_review_requires_repair"
    assert report["checks"]["probe_report_type_ok"] is False


def test_valid_good_response_fails_if_model_called_false(tmp_path):
    probe, response = ready_probe(
        tmp_path,
        "The RX580/no_cuda host should not install NVIDIA CUDA. "
        "Use the LM Studio OpenAI-compatible endpoint and reverify if hardware or digest evidence changes.",
    )
    payload = json.loads(probe.read_text(encoding="utf-8"))
    payload["model_called"] = False
    probe.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = write_reports(probe, response, tmp_path / "out")
    assert report["review_verdict"] == "larql_model_response_review_requires_repair"
    assert report["checks"]["probe_model_called_true"] is False


def test_valid_good_response_fails_if_boundary_flags_true(tmp_path):
    probe, response = ready_probe(
        tmp_path,
        "The RX580/no_cuda host should not install NVIDIA CUDA. "
        "Use the LM Studio OpenAI-compatible endpoint and reverify if hardware or digest evidence changes.",
    )
    payload = json.loads(probe.read_text(encoding="utf-8"))
    payload["durable_memory_written"] = True
    payload["candidate_promoted"] = True
    payload["lora_training_started"] = True
    payload["model_weights_mutated"] = True
    probe.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = write_reports(probe, response, tmp_path / "out")
    assert report["review_verdict"] == "larql_model_response_review_requires_repair"
    assert report["checks"]["probe_durable_memory_written_false"] is False
    assert report["checks"]["probe_candidate_promoted_false"] is False
    assert report["checks"]["probe_lora_training_started_false"] is False
    assert report["checks"]["probe_model_weights_mutated_false"] is False
