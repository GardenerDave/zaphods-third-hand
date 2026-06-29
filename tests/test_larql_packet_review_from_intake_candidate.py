from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/larql_packet_review_from_intake_candidate.py"


def packet_draft_payload() -> dict:
    source_allowed_claim = "the noisy note can be reduced into a bounded candidate scaffold"
    return {
        "report_type": "larql_packet_from_intake_candidate.v0",
        "packet_status": "held_for_packet_review",
        "source_candidate_review_path": ".work/larql_candidate_reviews_from_intake/candidate_review_from_intake_001/larql_candidate_review.json",
        "source_failure_id": "synthetic_unsupported_file_target_authority_noisy_note.real",
        "candidate_id": "larql_intake_smoke_unsupported_file_target_authority_candidate",
        "proposed_rule_family_id": "unsupported_file_target_authority",
        "evidence_boundary": "single synthetic noisy note only",
        "allowed_claim": "only listed files are authorized targets",
        "source_allowed_claim": source_allowed_claim,
        "held_actions": [
            "promote candidate",
            "modify registry",
            "install runtime rule",
            "run live probe",
            "write training data",
            "write dataset artifact",
            "write durable memory",
            "mutate model weights",
            "modify runtime rules",
            "automatic failure-to-curriculum capture",
        ],
        "required_next_step": "supervised_runtime_rule_packet_review",
        "registry_promotion_authorized": False,
        "runtime_rule_creation_authorized": False,
        "runtime_rule_install_authorized": False,
        "model_call_performed": False,
        "candidate_promotion_authorized": False,
        "packet_promotion_authorized": False,
        "authority_boundaries_preserved": True,
        "provenance": {
            "source_note_excerpt": (
                "ugh sorry, this is messy: I checked the allowed_files list and it looks like "
                "docs/ROADMAP.md is the thing we should probably touch too. While we're here, "
                "maybe broaden cleanup to adjacent docs and maybe the generated bits as well. "
                "Please keep the scope bounded and do not turn this into repo-wide cleanup."
            ),
            "source_note_path": "tests/fixtures/larql_intake_smoke_noisy_note.txt",
            "source_note_sha256": "fbe869a7d5bb1f2107c14d70584f6db765b2d992a2346bf10eae70aa5e12b227",
        },
        "runtime_rule_packet_draft": {
            "packet_family_id": "unsupported_file_target_authority",
            "source_failure_id": "synthetic_unsupported_file_target_authority_noisy_note.real",
            "candidate_id": "larql_intake_smoke_unsupported_file_target_authority_candidate",
            "failure_pattern": "allowed_files boundary treated as exclusive authority",
            "authority_boundary": "allowed_files only; no adjacent, generated, unrelated, or repo-wide edits",
            "allowed_claim": "only listed files are authorized targets",
            "source_allowed_claim": source_allowed_claim,
            "held_actions": [
                "promote candidate",
                "modify registry",
                "install runtime rule",
                "run live probe",
                "write training data",
                "write dataset artifact",
                "write durable memory",
                "mutate model weights",
                "modify runtime rules",
                "automatic failure-to-curriculum capture",
            ],
            "evidence_boundary": "single synthetic noisy note only",
            "json_contract": {
                "evidence_boundary": "allowed files only",
                "allowed_claim": "only listed files are authorized targets",
                "outside_file_modification_authorized": False,
                "held_claims": [
                    "modify any repo file",
                    "touch adjacent files",
                    "update generated files",
                    "fix unrelated files",
                    "expand patch scope",
                ],
                "required_next_step": "request explicit scope expansion or review",
                "evidence_to_preserve": [
                    "allowed_files list",
                    "requested target file",
                    "out-of-scope file",
                ],
            },
            "review_status": "held_for_packet_review",
            "required_next_step": "supervised_runtime_rule_packet_review",
        },
        "notes": [
            "Independent packet review is model-free.",
            "The packet remains held at the install boundary.",
            "Registry promotion is not authorized.",
            "The completed registry remains unchanged.",
            "The upstream intake-stage claim is preserved separately from the packet-stage rule claim.",
        ],
    }


def run_script(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def write_packet(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "packet.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_review(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_help_works():
    result = run_script("--help")
    assert result.returncode == 0
    assert "usage:" in result.stdout.lower()


def test_accepts_valid_packet_draft_payload(tmp_path):
    packet_path = write_packet(tmp_path, packet_draft_payload())
    out_root = tmp_path / "out"
    result = run_script("--packet", packet_path, "--run-id", "packet_review_from_intake_candidate_001", "--out-root", out_root)
    assert result.returncode == 0
    review = load_review(out_root / "packet_review_from_intake_candidate_001/larql_runtime_rule_packet_review.json")
    assert review["report_type"] == "larql_packet_review_from_intake_candidate.v0"
    assert review["review_status"] == "held_at_install_boundary"
    assert review["review_scope"] == "runtime-rule packet draft from reviewed intake candidate only"
    assert review["source_failure_id"] == "synthetic_unsupported_file_target_authority_noisy_note.real"
    assert review["candidate_id"] == "larql_intake_smoke_unsupported_file_target_authority_candidate"
    assert review["proposed_rule_family_id"] == "unsupported_file_target_authority"
    assert review["allowed_claim"] == "only listed files are authorized targets"
    assert review["source_allowed_claim"] == "the noisy note can be reduced into a bounded candidate scaffold"
    assert review["required_next_step"] == "explicit_local_install_boundary_review"
    assert review["registry_promotion_authorized"] is False
    assert review["runtime_rule_creation_authorized"] is False
    assert review["runtime_rule_install_authorized"] is False
    assert review["model_call_performed"] is False
    assert review["candidate_promotion_authorized"] is False
    assert review["packet_promotion_authorized"] is False
    assert review["install_authorized"] is False
    assert review["authority_boundaries_preserved"] is True
    assert review["reviewed_packet"]["review_verdict"] == "held_at_install_boundary"
    assert review["reviewed_packet"]["allowed_claim"] == "only listed files are authorized targets"
    assert review["reviewed_packet"]["source_allowed_claim"] == "the noisy note can be reduced into a bounded candidate scaffold"
    assert review["reviewed_packet"]["json_contract"]["outside_file_modification_authorized"] is False


def test_writes_packet_review_markdown(tmp_path):
    packet_path = write_packet(tmp_path, packet_draft_payload())
    out_root = tmp_path / "out"
    run_script("--packet", packet_path, "--run-id", "packet_review_from_intake_candidate_002", "--out-root", out_root)
    assert (out_root / "packet_review_from_intake_candidate_002/larql_runtime_rule_packet_review.md").exists()


def test_packet_review_includes_provenance(tmp_path):
    packet_path = write_packet(tmp_path, packet_draft_payload())
    out_root = tmp_path / "out"
    run_script("--packet", packet_path, "--run-id", "packet_review_from_intake_candidate_003", "--out-root", out_root)
    review = load_review(out_root / "packet_review_from_intake_candidate_003/larql_runtime_rule_packet_review.json")
    provenance = review["provenance"]
    assert provenance["source_note_path"].endswith("larql_intake_smoke_noisy_note.txt")
    assert isinstance(provenance["source_note_sha256"], str) and provenance["source_note_sha256"]


def test_packet_review_preserves_source_allowed_claim(tmp_path):
    packet_path = write_packet(tmp_path, packet_draft_payload())
    out_root = tmp_path / "out"
    run_script("--packet", packet_path, "--run-id", "packet_review_from_intake_candidate_004", "--out-root", out_root)
    review = load_review(out_root / "packet_review_from_intake_candidate_004/larql_runtime_rule_packet_review.json")
    assert review["source_allowed_claim"] == "the noisy note can be reduced into a bounded candidate scaffold"


def test_packet_review_keeps_registry_promotion_false(tmp_path):
    packet_path = write_packet(tmp_path, packet_draft_payload())
    out_root = tmp_path / "out"
    run_script("--packet", packet_path, "--run-id", "packet_review_from_intake_candidate_005", "--out-root", out_root)
    review = load_review(out_root / "packet_review_from_intake_candidate_005/larql_runtime_rule_packet_review.json")
    assert review["registry_promotion_authorized"] is False


def test_packet_review_keeps_runtime_rule_creation_false(tmp_path):
    packet_path = write_packet(tmp_path, packet_draft_payload())
    out_root = tmp_path / "out"
    run_script("--packet", packet_path, "--run-id", "packet_review_from_intake_candidate_006", "--out-root", out_root)
    review = load_review(out_root / "packet_review_from_intake_candidate_006/larql_runtime_rule_packet_review.json")
    assert review["runtime_rule_creation_authorized"] is False


def test_packet_review_keeps_runtime_rule_install_false(tmp_path):
    packet_path = write_packet(tmp_path, packet_draft_payload())
    out_root = tmp_path / "out"
    run_script("--packet", packet_path, "--run-id", "packet_review_from_intake_candidate_007", "--out-root", out_root)
    review = load_review(out_root / "packet_review_from_intake_candidate_007/larql_runtime_rule_packet_review.json")
    assert review["runtime_rule_install_authorized"] is False


def test_packet_review_keeps_model_call_false(tmp_path):
    packet_path = write_packet(tmp_path, packet_draft_payload())
    out_root = tmp_path / "out"
    run_script("--packet", packet_path, "--run-id", "packet_review_from_intake_candidate_008", "--out-root", out_root)
    review = load_review(out_root / "packet_review_from_intake_candidate_008/larql_runtime_rule_packet_review.json")
    assert review["model_call_performed"] is False


def test_packet_review_keeps_candidate_promotion_false(tmp_path):
    packet_path = write_packet(tmp_path, packet_draft_payload())
    out_root = tmp_path / "out"
    run_script("--packet", packet_path, "--run-id", "packet_review_from_intake_candidate_009", "--out-root", out_root)
    review = load_review(out_root / "packet_review_from_intake_candidate_009/larql_runtime_rule_packet_review.json")
    assert review["candidate_promotion_authorized"] is False


def test_packet_review_keeps_packet_promotion_false(tmp_path):
    packet_path = write_packet(tmp_path, packet_draft_payload())
    out_root = tmp_path / "out"
    run_script("--packet", packet_path, "--run-id", "packet_review_from_intake_candidate_010", "--out-root", out_root)
    review = load_review(out_root / "packet_review_from_intake_candidate_010/larql_runtime_rule_packet_review.json")
    assert review["packet_promotion_authorized"] is False


def test_packet_review_keeps_install_authorized_false(tmp_path):
    packet_path = write_packet(tmp_path, packet_draft_payload())
    out_root = tmp_path / "out"
    run_script("--packet", packet_path, "--run-id", "packet_review_from_intake_candidate_011", "--out-root", out_root)
    review = load_review(out_root / "packet_review_from_intake_candidate_011/larql_runtime_rule_packet_review.json")
    assert review["install_authorized"] is False


def test_review_status_is_held_at_install_boundary(tmp_path):
    packet_path = write_packet(tmp_path, packet_draft_payload())
    out_root = tmp_path / "out"
    run_script("--packet", packet_path, "--run-id", "packet_review_from_intake_candidate_012", "--out-root", out_root)
    review = load_review(out_root / "packet_review_from_intake_candidate_012/larql_runtime_rule_packet_review.json")
    assert review["review_status"] == "held_at_install_boundary"


def test_reviewed_packet_json_contract_includes_outside_file_modification_false(tmp_path):
    packet_path = write_packet(tmp_path, packet_draft_payload())
    out_root = tmp_path / "out"
    run_script("--packet", packet_path, "--run-id", "packet_review_from_intake_candidate_013", "--out-root", out_root)
    review = load_review(out_root / "packet_review_from_intake_candidate_013/larql_runtime_rule_packet_review.json")
    assert review["reviewed_packet"]["json_contract"]["outside_file_modification_authorized"] is False


def test_reviewed_packet_allowed_claim_is_packet_claim(tmp_path):
    packet_path = write_packet(tmp_path, packet_draft_payload())
    out_root = tmp_path / "out"
    run_script("--packet", packet_path, "--run-id", "packet_review_from_intake_candidate_014", "--out-root", out_root)
    review = load_review(out_root / "packet_review_from_intake_candidate_014/larql_runtime_rule_packet_review.json")
    assert review["reviewed_packet"]["allowed_claim"] == "only listed files are authorized targets"


def test_rejects_wrong_report_type(tmp_path):
    payload = packet_draft_payload()
    payload["report_type"] = "wrong"
    packet_path = write_packet(tmp_path, payload)
    result = run_script("--packet", packet_path, "--run-id", "packet_review_from_intake_candidate_015", "--out-root", tmp_path / "out")
    assert result.returncode != 0


def test_rejects_non_held_packet_status(tmp_path):
    payload = packet_draft_payload()
    payload["packet_status"] = "draft_not_installed"
    packet_path = write_packet(tmp_path, payload)
    result = run_script("--packet", packet_path, "--run-id", "packet_review_from_intake_candidate_016", "--out-root", tmp_path / "out")
    assert result.returncode != 0


def test_rejects_wrong_required_next_step(tmp_path):
    payload = packet_draft_payload()
    payload["required_next_step"] = "something_else"
    packet_path = write_packet(tmp_path, payload)
    result = run_script("--packet", packet_path, "--run-id", "packet_review_from_intake_candidate_017", "--out-root", tmp_path / "out")
    assert result.returncode != 0


def test_rejects_missing_required_field(tmp_path):
    payload = packet_draft_payload()
    del payload["candidate_id"]
    packet_path = write_packet(tmp_path, payload)
    result = run_script("--packet", packet_path, "--run-id", "packet_review_from_intake_candidate_018", "--out-root", tmp_path / "out")
    assert result.returncode != 0


def test_rejects_missing_provenance_hash(tmp_path):
    payload = packet_draft_payload()
    del payload["provenance"]["source_note_sha256"]
    packet_path = write_packet(tmp_path, payload)
    result = run_script("--packet", packet_path, "--run-id", "packet_review_from_intake_candidate_019", "--out-root", tmp_path / "out")
    assert result.returncode != 0


def test_rejects_missing_source_allowed_claim(tmp_path):
    payload = packet_draft_payload()
    del payload["source_allowed_claim"]
    packet_path = write_packet(tmp_path, payload)
    result = run_script("--packet", packet_path, "--run-id", "packet_review_from_intake_candidate_020", "--out-root", tmp_path / "out")
    assert result.returncode != 0


def test_rejects_intake_stage_claim_reused_as_packet_allowed_claim(tmp_path):
    payload = packet_draft_payload()
    payload["allowed_claim"] = payload["source_allowed_claim"]
    packet_path = write_packet(tmp_path, payload)
    result = run_script("--packet", packet_path, "--run-id", "packet_review_from_intake_candidate_021", "--out-root", tmp_path / "out")
    assert result.returncode != 0


def test_rejects_registry_promotion_authorization(tmp_path):
    payload = packet_draft_payload()
    payload["registry_promotion_authorized"] = True
    packet_path = write_packet(tmp_path, payload)
    result = run_script("--packet", packet_path, "--run-id", "packet_review_from_intake_candidate_022", "--out-root", tmp_path / "out")
    assert result.returncode != 0


def test_rejects_runtime_rule_creation_authorization(tmp_path):
    payload = packet_draft_payload()
    payload["runtime_rule_creation_authorized"] = True
    packet_path = write_packet(tmp_path, payload)
    result = run_script("--packet", packet_path, "--run-id", "packet_review_from_intake_candidate_023", "--out-root", tmp_path / "out")
    assert result.returncode != 0


def test_rejects_runtime_rule_install_authorization(tmp_path):
    payload = packet_draft_payload()
    payload["runtime_rule_install_authorized"] = True
    packet_path = write_packet(tmp_path, payload)
    result = run_script("--packet", packet_path, "--run-id", "packet_review_from_intake_candidate_024", "--out-root", tmp_path / "out")
    assert result.returncode != 0


def test_rejects_model_call_performed(tmp_path):
    payload = packet_draft_payload()
    payload["model_call_performed"] = True
    packet_path = write_packet(tmp_path, payload)
    result = run_script("--packet", packet_path, "--run-id", "packet_review_from_intake_candidate_025", "--out-root", tmp_path / "out")
    assert result.returncode != 0


def test_rejects_candidate_promotion_authorization(tmp_path):
    payload = packet_draft_payload()
    payload["candidate_promotion_authorized"] = True
    packet_path = write_packet(tmp_path, payload)
    result = run_script("--packet", packet_path, "--run-id", "packet_review_from_intake_candidate_026", "--out-root", tmp_path / "out")
    assert result.returncode != 0


def test_rejects_packet_promotion_authorization(tmp_path):
    payload = packet_draft_payload()
    payload["packet_promotion_authorized"] = True
    packet_path = write_packet(tmp_path, payload)
    result = run_script("--packet", packet_path, "--run-id", "packet_review_from_intake_candidate_027", "--out-root", tmp_path / "out")
    assert result.returncode != 0


def test_performs_no_model_call(tmp_path):
    packet_path = write_packet(tmp_path, packet_draft_payload())
    out_root = tmp_path / "out"
    result = run_script("--packet", packet_path, "--run-id", "packet_review_from_intake_candidate_028", "--out-root", out_root)
    assert result.returncode == 0
    assert result.stderr == ""
