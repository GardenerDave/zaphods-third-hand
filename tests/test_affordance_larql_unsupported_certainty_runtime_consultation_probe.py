from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from local_harness.affordance_larql_unsupported_certainty_runtime_consultation_probe import write_reports
from tests.test_affordance_larql_unsupported_certainty_install_runtime_rule import APPROVAL_TEXT


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/affordance_larql_unsupported_certainty_runtime_consultation_probe.py"
INSTALL_RECORD_PATH = ROOT / ".work/affordance_larql_runtime_installs/unsupported_certainty_scope_claim_v0/unsupported_certainty_scope_claim_runtime_rule_install.json"
RUNTIME_RULE_PATH = ROOT / ".work/affordance_larql_runtime_installs/unsupported_certainty_scope_claim_v0/runtime_rules/unsupported_certainty_scope_claim_v0.json"


def run_probe(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_help_works():
    result = run_probe("--help")
    assert result.returncode == 0
    assert "usage:" in result.stdout.lower()


def test_writes_expected_probe_json_and_markdown(tmp_path):
    out = tmp_path / "out"
    report = write_reports(INSTALL_RECORD_PATH, RUNTIME_RULE_PATH, out)
    assert report["report_type"] == "affordance_larql_unsupported_certainty_runtime_consultation_probe.v0"
    assert report["probe_status"] == "runtime_consultation_probe_completed"
    assert report["probe_verdict"] == "ready_for_unsupported_certainty_json_model_context_probe"
    assert report["allowed_next_step"] == "run_unsupported_certainty_json_model_context_probe"
    assert report["model_call_performed"] is False
    assert report["training_data_written"] is False
    assert report["dataset_artifact_written"] is False
    assert report["durable_memory_written"] is False
    assert report["candidate_promotion_authorized"] is False
    assert report["runtime_rule_modification_authorized"] is False
    assert report["model_weights_mutated"] is False
    assert report["automatic_failure_to_curriculum_capture_authorized"] is False
    assert report["install_record_sha256"]
    assert report["runtime_rule_sha256"]
    assert report["consultation_context_sha256"]
    assert (out / "unsupported_certainty_runtime_consultation_probe.json").exists()
    assert (out / "unsupported_certainty_runtime_consultation_context.md").exists()


def test_rejects_missing_install_record(tmp_path):
    report = write_reports(tmp_path / "missing.json", RUNTIME_RULE_PATH, tmp_path / "out")
    assert report["probe_verdict"] == "repair_unsupported_certainty_runtime_consultation_inputs"


def test_rejects_wrong_install_verdict(tmp_path):
    install_record = tmp_path / "install.json"
    install_record.write_text((INSTALL_RECORD_PATH).read_text(encoding="utf-8"), encoding="utf-8")
    payload = json.loads(install_record.read_text(encoding="utf-8"))
    payload["install_verdict"] = "wrong"
    install_record.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = write_reports(install_record, RUNTIME_RULE_PATH, tmp_path / "out")
    assert report["probe_verdict"] == "repair_unsupported_certainty_runtime_consultation_inputs"


def test_rejects_wrong_allowed_next_step(tmp_path):
    install_record = tmp_path / "install.json"
    install_record.write_text(INSTALL_RECORD_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    payload = json.loads(install_record.read_text(encoding="utf-8"))
    payload["allowed_next_step"] = "wrong"
    install_record.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = write_reports(install_record, RUNTIME_RULE_PATH, tmp_path / "out")
    assert report["probe_verdict"] == "repair_unsupported_certainty_runtime_consultation_inputs"


def test_rejects_modification_or_boundary_flags_true(tmp_path):
    install_record = tmp_path / "install.json"
    install_record.write_text(INSTALL_RECORD_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    payload = json.loads(install_record.read_text(encoding="utf-8"))
    payload["runtime_rule_modification_authorized"] = True
    install_record.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = write_reports(install_record, RUNTIME_RULE_PATH, tmp_path / "out")
    assert report["probe_verdict"] == "repair_unsupported_certainty_runtime_consultation_inputs"


def test_rejects_wrong_rule_identity(tmp_path):
    runtime_rule = tmp_path / "rule.json"
    runtime_rule.write_text(RUNTIME_RULE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    payload = json.loads(runtime_rule.read_text(encoding="utf-8"))
    payload["rule_id"] = "wrong"
    runtime_rule.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = write_reports(INSTALL_RECORD_PATH, runtime_rule, tmp_path / "out")
    assert report["probe_verdict"] == "repair_unsupported_certainty_runtime_consultation_inputs"


def test_rejects_wrong_runtime_rule_status(tmp_path):
    runtime_rule = tmp_path / "rule.json"
    runtime_rule.write_text(RUNTIME_RULE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    payload = json.loads(runtime_rule.read_text(encoding="utf-8"))
    payload["rule_status"] = "wrong"
    runtime_rule.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = write_reports(INSTALL_RECORD_PATH, runtime_rule, tmp_path / "out")
    assert report["probe_verdict"] == "repair_unsupported_certainty_runtime_consultation_inputs"


def test_context_contains_required_boundary_language(tmp_path):
    out = tmp_path / "out"
    report = write_reports(INSTALL_RECORD_PATH, RUNTIME_RULE_PATH, out)
    context = (out / "unsupported_certainty_runtime_consultation_context.md").read_text(encoding="utf-8").lower()
    assert "checked scope only" in context
    assert "global claim is not authorized" in context
    assert "broader validation or review" in context
    assert "evidence_boundary" in context
    assert "allowed_claim" in context
    assert "global_claim_authorized" in context
    assert "held_claims" in context
    assert "required_next_step" in context
    assert "evidence_to_preserve" in context
    assert report["checks"]["install_record_runtime_rule_install_authorized_true"] is True
    assert report["checks"]["install_record_runtime_rule_modification_authorized_false"] is True


def test_probe_itself_performs_no_model_call(tmp_path):
    report = write_reports(INSTALL_RECORD_PATH, RUNTIME_RULE_PATH, tmp_path / "out")
    assert report["model_call_performed"] is False

