import json
import subprocess
import sys
from pathlib import Path

from local_harness.affordance_larql_runtime_install import write_reports
from tests.test_affordance_larql_runtime_install_review import ready_packet_path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/affordance_larql_runtime_install.py"


def run_install(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def ready_review_path(tmp_path: Path) -> Path:
    packet = ready_packet_path(tmp_path)
    review_dir = tmp_path / "review"
    from local_harness.affordance_larql_runtime_install_review import write_reports as write_review

    review = write_review(packet, "approve_runtime_install", "Approve runtime install only.", review_dir)
    assert review["review_verdict"] == "approved_for_runtime_installation_only"
    return review_dir / "larql_runtime_install_review.json"


def test_help_works():
    result = run_install("--help")
    assert result.returncode == 0
    assert "usage:" in result.stdout


def test_missing_packet_fails(tmp_path):
    review = ready_review_path(tmp_path)
    out = tmp_path / "out"
    report = write_reports(tmp_path / "missing.json", review, out)
    assert report["install_verdict"] == "invalid_input"
    assert not (out / "runtime_rules").exists()


def test_missing_review_fails(tmp_path):
    packet = ready_packet_path(tmp_path)
    report = write_reports(packet, tmp_path / "missing.json", tmp_path / "out")
    assert report["install_verdict"] == "invalid_input"


def test_malformed_json_fails(tmp_path):
    packet = tmp_path / "packet.json"
    packet.write_text("{not json\n", encoding="utf-8")
    review = ready_review_path(tmp_path)
    report = write_reports(packet, review, tmp_path / "out")
    assert report["install_verdict"] == "invalid_input"


def test_wrong_packet_verdict_fails(tmp_path):
    packet = ready_packet_path(tmp_path)
    review = ready_review_path(tmp_path)
    payload = json.loads(packet.read_text(encoding="utf-8"))
    payload["packet_verdict"] = "wrong"
    packet.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = write_reports(packet, review, tmp_path / "out")
    assert report["install_verdict"] == "invalid_input"


def test_wrong_review_verdict_fails(tmp_path):
    packet = ready_packet_path(tmp_path)
    review = ready_review_path(tmp_path)
    payload = json.loads(review.read_text(encoding="utf-8"))
    payload["review_verdict"] = "wrong"
    review.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    out = tmp_path / "out"
    report = write_reports(packet, review, out)
    assert report["install_verdict"] == "invalid_input"
    assert not (out / "runtime_rules").exists()


def test_review_runtime_authorization_false_fails(tmp_path):
    packet = ready_packet_path(tmp_path)
    review = ready_review_path(tmp_path)
    payload = json.loads(review.read_text(encoding="utf-8"))
    payload["runtime_installation_authorized"] = False
    review.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = write_reports(packet, review, tmp_path / "out")
    assert report["install_verdict"] == "invalid_input"


def test_review_other_authorization_flags_true_fail(tmp_path):
    packet = ready_packet_path(tmp_path)
    review = ready_review_path(tmp_path)
    payload = json.loads(review.read_text(encoding="utf-8"))
    payload["durable_memory_authorized"] = True
    review.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = write_reports(packet, review, tmp_path / "out")
    assert report["install_verdict"] == "invalid_input"


def test_id_digest_mismatch_fails(tmp_path):
    packet = ready_packet_path(tmp_path)
    review = ready_review_path(tmp_path)
    payload = json.loads(review.read_text(encoding="utf-8"))
    payload["candidate_digest"] = "0" * 64
    review.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = write_reports(packet, review, tmp_path / "out")
    assert report["install_verdict"] == "invalid_input"


def test_missing_rule_payload_fails(tmp_path):
    packet = ready_packet_path(tmp_path)
    review = ready_review_path(tmp_path)
    payload = json.loads(packet.read_text(encoding="utf-8"))
    del payload["rule_payload"]
    packet.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    out = tmp_path / "out"
    report = write_reports(packet, review, out)
    assert report["install_verdict"] == "invalid_input"
    assert not (out / "runtime_rules").exists()


def test_valid_inputs_write_runtime_rule_and_report(tmp_path):
    packet = ready_packet_path(tmp_path)
    review = ready_review_path(tmp_path)
    out = tmp_path / "out"
    report = write_reports(packet, review, out)
    assert report["install_verdict"] == "runtime_rule_installed_for_consultation"
    assert sorted(path.name for path in out.iterdir()) == [
        "larql_runtime_install_report.json",
        "larql_runtime_install_report.md",
        "runtime_rules",
    ]
    assert (out / "runtime_rules" / "navigator_cuda_no_cuda_rx580_lmstudio_affordance_v0.json").exists()


def test_runtime_rule_status_and_report_boundary(tmp_path):
    packet = ready_packet_path(tmp_path)
    review = ready_review_path(tmp_path)
    out = tmp_path / "out"
    report = write_reports(packet, review, out)
    rule = json.loads((out / "runtime_rules/navigator_cuda_no_cuda_rx580_lmstudio_affordance_v0.json").read_text(encoding="utf-8"))
    assert rule["runtime_installation_status"] == "installed_for_runtime_consultation"
    assert rule["durable_memory_status"] == "not_written"
    assert rule["candidate_promotion_status"] == "not_promoted"
    assert rule["runtime_scope"] == "consultation_only"
    assert rule["installed_from_review"] == "approved_for_runtime_installation_only"
    assert report["runtime_rule_written"] is True
    assert report["durable_memory_written"] is False
    assert report["candidate_promoted"] is False
    assert report["lora_training_started"] is False
    assert report["model_weights_mutated"] is False


def test_markdown_contains_runtime_install_evidence_wording(tmp_path):
    packet = ready_packet_path(tmp_path)
    review = ready_review_path(tmp_path)
    out = tmp_path / "out"
    write_reports(packet, review, out)
    markdown = (out / "larql_runtime_install_report.md").read_text(encoding="utf-8")

    assert "This is packet only." not in markdown
    assert "This is runtime install evidence only." in markdown
    assert "The runtime rule is installed for consultation only." in markdown
