from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/larql_evidence_packet.py"
REGISTRY = ROOT / "docs/reports/affordance_larql/larql_rule_registry.json"


def run_script(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_help_works():
    result = run_script("--help")
    assert result.returncode == 0
    assert "usage:" in result.stdout.lower()


def test_writes_packet_for_unsupported_file_target_rule(tmp_path):
    out = tmp_path / "packet"
    result = run_script("--registry", REGISTRY, "--rule-id", "unsupported_file_target_authority_v0", "--out", out)
    assert result.returncode == 0
    manifest = json.loads((out / "evidence_packet_manifest.json").read_text(encoding="utf-8"))
    assert manifest["report_type"] == "larql_evidence_packet.v0"
    assert manifest["rule_id"] == "unsupported_file_target_authority_v0"
    assert manifest["rule_family_id"] == "unsupported-file-target-authority"
    assert manifest["source_failure_id"] == "unsupported_file_target_authority.real"
    assert manifest["candidate_id"] == "unsupported_file_target_authority"
    assert manifest["status"] == "passed_after_transport_repair"
    assert manifest["failed_probe_preserved"] is True
    assert manifest["transport_repair_required"] is True
    assert manifest["json_contract"]["allowed_claim"] == "only listed files are authorized targets"
    assert any(item["path"].endswith("UNSUPPORTED_FILE_TARGET_AUTHORITY_JSON_MODEL_CONTEXT_PASS_CLOSEOUT_2026-06-29.md") for item in manifest["evidence_items"])
    assert any(item["path"].endswith("unsupported_file_target_authority_v0.json") for item in manifest["evidence_items"])
    assert (out / "evidence_packet_summary.md").exists()


def test_missing_work_evidence_is_recorded_not_fatal(tmp_path):
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    payload["rules"][0]["evidence_paths"].append(".work/larql_evidence_packets/does_not_exist.txt")
    bad = tmp_path / "registry.json"
    bad.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    out = tmp_path / "packet"
    result = run_script("--registry", bad, "--rule-id", "unsupported_certainty_scope_claim_v0", "--out", out)
    assert result.returncode == 0
    manifest = json.loads((out / "evidence_packet_manifest.json").read_text(encoding="utf-8"))
    missing = [item for item in manifest["evidence_items"] if not item["exists"]]
    assert missing
    assert any(item["kind"] == "missing" for item in missing)


def test_existing_docs_evidence_gets_sha256(tmp_path):
    out = tmp_path / "packet"
    result = run_script("--registry", REGISTRY, "--rule-id", "unsupported_certainty_scope_claim_v0", "--out", out)
    assert result.returncode == 0
    manifest = json.loads((out / "evidence_packet_manifest.json").read_text(encoding="utf-8"))
    closeout = next(item for item in manifest["evidence_items"] if item["path"].endswith("UNSUPPORTED_CERTAINTY_JSON_MODEL_CONTEXT_PASS_CLOSEOUT_2026-06-29.md"))
    assert closeout["exists"] is True
    assert closeout["kind"] == "file"
    assert isinstance(closeout.get("sha256"), str) and closeout["sha256"]


def test_rejects_unknown_rule_id(tmp_path):
    result = run_script("--registry", REGISTRY, "--rule-id", "missing_rule", "--out", tmp_path / "packet")
    assert result.returncode != 0


def test_rejects_duplicate_rule_id_in_registry(tmp_path):
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    payload["rules"].append(dict(payload["rules"][0]))
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result = run_script("--registry", bad, "--rule-id", "absence_of_evidence_file_authority_v0", "--out", tmp_path / "packet")
    assert result.returncode != 0


def test_rejects_missing_required_registry_field(tmp_path):
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    del payload["rules"][0]["status"]
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result = run_script("--registry", bad, "--rule-id", "absence_of_evidence_file_authority_v0", "--out", tmp_path / "packet")
    assert result.returncode != 0


def test_rejects_non_object_json_contract(tmp_path):
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    payload["rules"][0]["json_contract"] = []
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result = run_script("--registry", bad, "--rule-id", "absence_of_evidence_file_authority_v0", "--out", tmp_path / "packet")
    assert result.returncode != 0


def test_summary_markdown_includes_required_sections(tmp_path):
    out = tmp_path / "packet"
    result = run_script("--registry", REGISTRY, "--rule-id", "unsupported_file_target_authority_v0", "--out", out)
    assert result.returncode == 0
    summary = (out / "evidence_packet_summary.md").read_text(encoding="utf-8")
    assert "unsupported_file_target_authority_v0" in summary
    assert "passed_after_transport_repair" in summary
    assert "UNSUPPORTED_FILE_TARGET_AUTHORITY_JSON_MODEL_CONTEXT_PASS_CLOSEOUT_2026-06-29.md" in summary
    assert "Evidence items:" in summary
    assert "Missing items:" in summary


def test_collector_performs_no_model_call():
    result = run_script("--registry", REGISTRY, "--rule-id", "unsupported_file_target_authority_v0", "--out", Path("/tmp") / "larql_evidence_packet")
    assert result.returncode == 0
    assert "model" not in result.stderr.lower()
