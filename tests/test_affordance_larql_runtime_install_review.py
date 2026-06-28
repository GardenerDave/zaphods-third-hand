import json
import subprocess
import sys
from pathlib import Path

from local_harness.affordance_larql_runtime_install_packet import write_reports as write_packet
from local_harness.affordance_larql_runtime_install_review import write_reports
from tests.test_affordance_larql_runtime_install_packet import ready_bundle_path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/affordance_larql_runtime_install_review.py"


def run_review(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def ready_packet_path(tmp_path: Path) -> Path:
    bundle, validation_bundle = ready_bundle_path(tmp_path)
    packet_out = tmp_path / "runtime_packet"
    write_packet(bundle / "larql_rule.json", validation_bundle / "larql_rule_validation_report.json", packet_out)
    return packet_out / "larql_runtime_install_packet.json"


def test_help_works():
    result = run_review("--help")
    assert result.returncode == 0
    assert "usage:" in result.stdout


def test_missing_packet_fails(tmp_path):
    report = write_reports(tmp_path / "missing.json", "approve_runtime_install", "ok", tmp_path / "out")
    assert report["review_verdict"] == "invalid_input"


def test_malformed_json_fails(tmp_path):
    packet = tmp_path / "packet.json"
    packet.write_text("{not json\n", encoding="utf-8")
    report = write_reports(packet, "approve_runtime_install", "ok", tmp_path / "out")
    assert report["review_verdict"] == "invalid_input"


def test_wrong_report_type_fails(tmp_path):
    packet = ready_packet_path(tmp_path)
    payload = json.loads(packet.read_text(encoding="utf-8"))
    payload["report_type"] = "wrong"
    packet.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = write_reports(packet, "approve_runtime_install", "ok", tmp_path / "out")
    assert report["review_verdict"] == "invalid_input"


def test_wrong_verdict_fails(tmp_path):
    packet = ready_packet_path(tmp_path)
    payload = json.loads(packet.read_text(encoding="utf-8"))
    payload["packet_verdict"] = "wrong"
    packet.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = write_reports(packet, "approve_runtime_install", "ok", tmp_path / "out")
    assert report["review_verdict"] == "invalid_input"


def test_wrong_next_step_fails(tmp_path):
    packet = ready_packet_path(tmp_path)
    payload = json.loads(packet.read_text(encoding="utf-8"))
    payload["allowed_next_step"] = "wrong"
    packet.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = write_reports(packet, "approve_runtime_install", "ok", tmp_path / "out")
    assert report["review_verdict"] == "invalid_input"


def test_preauthorized_packet_fails(tmp_path):
    packet = ready_packet_path(tmp_path)
    payload = json.loads(packet.read_text(encoding="utf-8"))
    payload["runtime_installation_authorized"] = True
    packet.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = write_reports(packet, "approve_runtime_install", "ok", tmp_path / "out")
    assert report["review_verdict"] == "invalid_input"


def test_missing_ids_fails(tmp_path):
    packet = ready_packet_path(tmp_path)
    payload = json.loads(packet.read_text(encoding="utf-8"))
    del payload["candidate_id"]
    packet.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = write_reports(packet, "approve_runtime_install", "ok", tmp_path / "out")
    assert report["review_verdict"] == "invalid_input"


def test_missing_or_installed_rule_payload_fails(tmp_path):
    packet = ready_packet_path(tmp_path)
    payload = json.loads(packet.read_text(encoding="utf-8"))
    del payload["rule_payload"]
    packet.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = write_reports(packet, "approve_runtime_install", "ok", tmp_path / "out")
    assert report["review_verdict"] == "invalid_input"


def test_approve_path_sets_runtime_authorized_true_only(tmp_path):
    packet = ready_packet_path(tmp_path)
    out = tmp_path / "out"
    report = write_reports(packet, "approve_runtime_install", "Approve runtime install only.", out)
    assert report["review_verdict"] == "approved_for_runtime_installation_only"
    assert report["runtime_installation_authorized"] is True
    assert report["durable_memory_authorized"] is False
    assert report["candidate_promotion_authorized"] is False
    assert report["lora_training_authorized"] is False
    assert report["model_weight_mutation_authorized"] is False
    assert sorted(path.name for path in out.iterdir()) == [
        "larql_runtime_install_review.json",
        "larql_runtime_install_review.md",
    ]


def test_reject_path_keeps_all_flags_false(tmp_path):
    packet = ready_packet_path(tmp_path)
    report = write_reports(packet, "reject_runtime_install", "Reject.", tmp_path / "out")
    assert report["review_verdict"] == "rejected_runtime_installation"
    assert report["runtime_installation_authorized"] is False
    assert report["durable_memory_authorized"] is False
    assert report["candidate_promotion_authorized"] is False
    assert report["lora_training_authorized"] is False
    assert report["model_weight_mutation_authorized"] is False


def test_markdown_boundary_text_present(tmp_path):
    packet = ready_packet_path(tmp_path)
    out = tmp_path / "out"
    write_reports(packet, "reject_runtime_install", "Reject.", out)
    markdown = (out / "larql_runtime_install_review.md").read_text(encoding="utf-8")
    assert "This is review only." in markdown
    assert "No runtime rule is installed." in markdown
    assert "No durable memory is written." in markdown
    assert "No candidate promotion is granted." in markdown
    assert "No LoRA training is authorized." in markdown
    assert "Approval only authorizes a later install step." in markdown
