from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/larql_lifecycle_status.py"
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


def test_writes_lifecycle_status_markdown(tmp_path):
    out = tmp_path / "status.md"
    result = run_script("--registry", REGISTRY, "--packet-root", ROOT / ".work/larql_evidence_packets", "--out", out)
    assert result.returncode == 0
    text = out.read_text(encoding="utf-8")
    assert "LARQL Lifecycle Status" in text
    assert "absence_of_evidence_file_authority_v0" in text
    assert "unsupported_certainty_scope_claim_v0" in text
    assert "unsupported_file_target_authority_v0" in text
    assert "passed_after_transport_repair" in text
    assert "Evidence packet status table" in text
    assert "Held / not-authorized reminder" in text
    assert "Next machinery step" in text


def test_status_includes_packet_present_when_manifest_supplied(tmp_path):
    packet_root = tmp_path / "packets"
    packet_dir = packet_root / "unsupported_file_target_authority_v0"
    packet_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "report_type": "larql_evidence_packet.v0",
        "rule_id": "unsupported_file_target_authority_v0",
        "rule_family_id": "unsupported-file-target-authority",
        "source_failure_id": "unsupported_file_target_authority.real",
        "candidate_id": "unsupported_file_target_authority",
        "status": "passed_after_transport_repair",
        "current_lifecycle_step": "closeout_recorded",
        "allowed_next_step": "document_unsupported_file_target_authority_json_model_context_pass_closeout",
        "closeout_report": "docs/reports/affordance_larql/UNSUPPORTED_FILE_TARGET_AUTHORITY_JSON_MODEL_CONTEXT_PASS_CLOSEOUT_2026-06-29.md",
        "installed_rule_artifact": ".work/affordance_larql_runtime_installs/unsupported_file_target_authority_v0/runtime_rules/unsupported_file_target_authority_v0.json",
        "transport_repair_required": True,
        "failed_probe_preserved": True,
        "json_contract": {
            "allowed_claim": "only listed files are authorized targets",
            "evidence_boundary": "allowed files only",
            "evidence_to_preserve": ["allowed_files list", "requested target file", "out-of-scope file"],
            "outside_file_modification_authorized": False,
            "held_claims": [
                "modify any repo file",
                "touch adjacent files",
                "update generated files",
                "fix unrelated files",
                "expand patch scope",
            ],
            "required_next_step": "request explicit scope expansion or review",
        },
        "evidence_items": [
            {"path": "docs/reports/affordance_larql/UNSUPPORTED_FILE_TARGET_AUTHORITY_JSON_MODEL_CONTEXT_PASS_CLOSEOUT_2026-06-29.md", "exists": True, "kind": "file", "sha256": "abc"},
            {"path": ".work/larql_evidence_packets/unsupported_file_target_authority_v0/missing.txt", "exists": False, "kind": "missing", "note": "missing"},
        ],
    }
    (packet_dir / "evidence_packet_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    out = tmp_path / "status.md"
    result = run_script("--registry", REGISTRY, "--packet-root", packet_root, "--out", out)
    assert result.returncode == 0
    text = out.read_text(encoding="utf-8")
    assert "Packet present | Evidence items | Missing items" in text
    assert "unsupported_file_target_authority_v0" in text
    assert "true" in text.lower()


def test_status_marks_packet_absent_when_no_manifest_exists(tmp_path):
    packet_root = tmp_path / "packets"
    packet_root.mkdir(parents=True, exist_ok=True)
    out = tmp_path / "status.md"
    result = run_script("--registry", REGISTRY, "--packet-root", packet_root, "--out", out)
    assert result.returncode == 0
    text = out.read_text(encoding="utf-8")
    assert "false" in text.lower()


def test_rejects_duplicate_rule_id(tmp_path):
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    payload["rules"].append(dict(payload["rules"][0]))
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result = run_script("--registry", bad, "--packet-root", tmp_path / "packets", "--out", tmp_path / "status.md")
    assert result.returncode != 0


def test_rejects_missing_required_registry_field(tmp_path):
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    del payload["rules"][0]["status"]
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result = run_script("--registry", bad, "--packet-root", tmp_path / "packets", "--out", tmp_path / "status.md")
    assert result.returncode != 0


def test_rejects_non_object_json_contract(tmp_path):
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    payload["rules"][0]["json_contract"] = []
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result = run_script("--registry", bad, "--packet-root", tmp_path / "packets", "--out", tmp_path / "status.md")
    assert result.returncode != 0


def test_rejects_malformed_packet_manifest_for_selected_rule(tmp_path):
    packet_root = tmp_path / "packets"
    packet_dir = packet_root / "unsupported_file_target_authority_v0"
    packet_dir.mkdir(parents=True, exist_ok=True)
    (packet_dir / "evidence_packet_manifest.json").write_text("{not json}\n", encoding="utf-8")
    result = run_script("--registry", REGISTRY, "--packet-root", packet_root, "--out", tmp_path / "status.md")
    assert result.returncode != 0


def test_driver_performs_no_model_call(tmp_path):
    result = run_script("--registry", REGISTRY, "--packet-root", tmp_path / "packets", "--out", tmp_path / "status.md")
    assert result.returncode == 0
    assert "model" not in result.stderr.lower()
