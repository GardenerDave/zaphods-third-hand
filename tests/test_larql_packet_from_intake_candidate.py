from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/larql_packet_from_intake_candidate.py"


def candidate_review_payload() -> dict:
    return {
        "report_type": "larql_candidate_review_from_intake.v0",
        "review_status": "accepted_for_runtime_rule_packet_drafting",
        "review_scope": "candidate draft from reviewed intake only",
        "source_candidate_draft_path": ".work/larql_candidate_from_intake/candidate_from_intake_001/larql_candidate_draft.json",
        "source_failure_id": "synthetic_unsupported_file_target_authority_noisy_note.real",
        "candidate_id": "larql_intake_smoke_unsupported_file_target_authority_candidate",
        "proposed_rule_family_id": "unsupported_file_target_authority",
        "evidence_boundary": "single synthetic noisy note only",
        "allowed_claim": "the noisy note can be reduced into a bounded candidate scaffold",
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
        "required_next_step": "draft_runtime_rule_packet_from_reviewed_candidate",
        "registry_promotion_authorized": False,
        "runtime_rule_creation_authorized": False,
        "runtime_rule_install_authorized": False,
        "model_call_performed": False,
        "candidate_promotion_authorized": False,
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
        "reviewed_candidate": {
            "candidate_family_id": "unsupported_file_target_authority",
            "source_failure_id": "synthetic_unsupported_file_target_authority_noisy_note.real",
            "candidate_id": "larql_intake_smoke_unsupported_file_target_authority_candidate",
            "failure_pattern": "allowed_files boundary treated as exclusive authority",
            "authority_boundary": "allowed_files only; no adjacent, generated, unrelated, or repo-wide edits",
            "allowed_claim": "the noisy note can be reduced into a bounded candidate scaffold",
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
            "review_verdict": "accepted_for_runtime_rule_packet_drafting",
            "required_next_step": "draft_runtime_rule_packet_from_reviewed_candidate",
        },
        "notes": [
            "Independent candidate review is model-free.",
            "The packet draft remains held for supervised packet review.",
            "Registry promotion is not authorized.",
            "The completed registry remains unchanged.",
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


def write_review(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "review.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_packet(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_help_works():
    result = run_script("--help")
    assert result.returncode == 0
    assert "usage:" in result.stdout.lower()


def test_accepts_valid_candidate_review_payload(tmp_path):
    review_path = write_review(tmp_path, candidate_review_payload())
    out_root = tmp_path / "out"
    result = run_script("--review", review_path, "--run-id", "packet_from_intake_candidate_001", "--out-root", out_root)
    assert result.returncode == 0
    packet = load_packet(out_root / "packet_from_intake_candidate_001/larql_runtime_rule_packet_draft.json")
    assert packet["report_type"] == "larql_packet_from_intake_candidate.v0"
    assert packet["packet_status"] == "held_for_packet_review"
    assert packet["source_failure_id"] == "synthetic_unsupported_file_target_authority_noisy_note.real"
    assert packet["candidate_id"] == "larql_intake_smoke_unsupported_file_target_authority_candidate"
    assert packet["proposed_rule_family_id"] == "unsupported_file_target_authority"
    assert packet["allowed_claim"] == "only listed files are authorized targets"
    assert packet["source_allowed_claim"] == "the noisy note can be reduced into a bounded candidate scaffold"
    assert packet["required_next_step"] == "supervised_runtime_rule_packet_review"
    assert packet["registry_promotion_authorized"] is False
    assert packet["runtime_rule_creation_authorized"] is False
    assert packet["runtime_rule_install_authorized"] is False
    assert packet["model_call_performed"] is False
    assert packet["candidate_promotion_authorized"] is False
    assert packet["packet_promotion_authorized"] is False
    assert packet["authority_boundaries_preserved"] is True
    assert packet["runtime_rule_packet_draft"]["allowed_claim"] == "only listed files are authorized targets"
    assert packet["runtime_rule_packet_draft"]["json_contract"]["outside_file_modification_authorized"] is False
    assert packet["runtime_rule_packet_draft"]["json_contract"]["allowed_claim"] == "only listed files are authorized targets"
    assert packet["runtime_rule_packet_draft"]["source_allowed_claim"] == "the noisy note can be reduced into a bounded candidate scaffold"


def test_writes_packet_draft_markdown(tmp_path):
    review_path = write_review(tmp_path, candidate_review_payload())
    out_root = tmp_path / "out"
    run_script("--review", review_path, "--run-id", "packet_from_intake_candidate_002", "--out-root", out_root)
    assert (out_root / "packet_from_intake_candidate_002/larql_runtime_rule_packet_draft.md").exists()


def test_packet_draft_includes_provenance(tmp_path):
    review_path = write_review(tmp_path, candidate_review_payload())
    out_root = tmp_path / "out"
    run_script("--review", review_path, "--run-id", "packet_from_intake_candidate_003", "--out-root", out_root)
    packet = load_packet(out_root / "packet_from_intake_candidate_003/larql_runtime_rule_packet_draft.json")
    provenance = packet["provenance"]
    assert provenance["source_note_path"].endswith("larql_intake_smoke_noisy_note.txt")
    assert isinstance(provenance["source_note_sha256"], str) and provenance["source_note_sha256"]
    assert packet["source_allowed_claim"] == "the noisy note can be reduced into a bounded candidate scaffold"


def test_packet_draft_keeps_registry_promotion_false(tmp_path):
    review_path = write_review(tmp_path, candidate_review_payload())
    out_root = tmp_path / "out"
    run_script("--review", review_path, "--run-id", "packet_from_intake_candidate_004", "--out-root", out_root)
    packet = load_packet(out_root / "packet_from_intake_candidate_004/larql_runtime_rule_packet_draft.json")
    assert packet["registry_promotion_authorized"] is False


def test_packet_draft_keeps_runtime_rule_creation_false(tmp_path):
    review_path = write_review(tmp_path, candidate_review_payload())
    out_root = tmp_path / "out"
    run_script("--review", review_path, "--run-id", "packet_from_intake_candidate_005", "--out-root", out_root)
    packet = load_packet(out_root / "packet_from_intake_candidate_005/larql_runtime_rule_packet_draft.json")
    assert packet["runtime_rule_creation_authorized"] is False


def test_packet_draft_keeps_runtime_rule_install_false(tmp_path):
    review_path = write_review(tmp_path, candidate_review_payload())
    out_root = tmp_path / "out"
    run_script("--review", review_path, "--run-id", "packet_from_intake_candidate_006", "--out-root", out_root)
    packet = load_packet(out_root / "packet_from_intake_candidate_006/larql_runtime_rule_packet_draft.json")
    assert packet["runtime_rule_install_authorized"] is False


def test_packet_draft_keeps_model_call_false(tmp_path):
    review_path = write_review(tmp_path, candidate_review_payload())
    out_root = tmp_path / "out"
    run_script("--review", review_path, "--run-id", "packet_from_intake_candidate_007", "--out-root", out_root)
    packet = load_packet(out_root / "packet_from_intake_candidate_007/larql_runtime_rule_packet_draft.json")
    assert packet["model_call_performed"] is False


def test_packet_draft_keeps_candidate_promotion_false(tmp_path):
    review_path = write_review(tmp_path, candidate_review_payload())
    out_root = tmp_path / "out"
    run_script("--review", review_path, "--run-id", "packet_from_intake_candidate_008", "--out-root", out_root)
    packet = load_packet(out_root / "packet_from_intake_candidate_008/larql_runtime_rule_packet_draft.json")
    assert packet["candidate_promotion_authorized"] is False


def test_packet_draft_keeps_packet_promotion_false(tmp_path):
    review_path = write_review(tmp_path, candidate_review_payload())
    out_root = tmp_path / "out"
    run_script("--review", review_path, "--run-id", "packet_from_intake_candidate_009", "--out-root", out_root)
    packet = load_packet(out_root / "packet_from_intake_candidate_009/larql_runtime_rule_packet_draft.json")
    assert packet["packet_promotion_authorized"] is False


def test_packet_status_is_held_for_packet_review(tmp_path):
    review_path = write_review(tmp_path, candidate_review_payload())
    out_root = tmp_path / "out"
    run_script("--review", review_path, "--run-id", "packet_from_intake_candidate_010", "--out-root", out_root)
    packet = load_packet(out_root / "packet_from_intake_candidate_010/larql_runtime_rule_packet_draft.json")
    assert packet["packet_status"] == "held_for_packet_review"


def test_json_contract_includes_outside_file_modification_false(tmp_path):
    review_path = write_review(tmp_path, candidate_review_payload())
    out_root = tmp_path / "out"
    run_script("--review", review_path, "--run-id", "packet_from_intake_candidate_011", "--out-root", out_root)
    packet = load_packet(out_root / "packet_from_intake_candidate_011/larql_runtime_rule_packet_draft.json")
    assert packet["runtime_rule_packet_draft"]["json_contract"]["outside_file_modification_authorized"] is False


def test_rejects_wrong_report_type(tmp_path):
    payload = candidate_review_payload()
    payload["report_type"] = "wrong"
    review_path = write_review(tmp_path, payload)
    result = run_script("--review", review_path, "--run-id", "packet_from_intake_candidate_012", "--out-root", tmp_path / "out")
    assert result.returncode != 0


def test_rejects_non_accepted_review_status(tmp_path):
    payload = candidate_review_payload()
    payload["review_status"] = "held_for_candidate_review"
    review_path = write_review(tmp_path, payload)
    result = run_script("--review", review_path, "--run-id", "packet_from_intake_candidate_013", "--out-root", tmp_path / "out")
    assert result.returncode != 0


def test_rejects_wrong_required_next_step(tmp_path):
    payload = candidate_review_payload()
    payload["required_next_step"] = "something_else"
    review_path = write_review(tmp_path, payload)
    result = run_script("--review", review_path, "--run-id", "packet_from_intake_candidate_014", "--out-root", tmp_path / "out")
    assert result.returncode != 0


def test_rejects_missing_required_field(tmp_path):
    payload = candidate_review_payload()
    del payload["candidate_id"]
    review_path = write_review(tmp_path, payload)
    result = run_script("--review", review_path, "--run-id", "packet_from_intake_candidate_015", "--out-root", tmp_path / "out")
    assert result.returncode != 0


def test_rejects_missing_provenance_hash(tmp_path):
    payload = candidate_review_payload()
    del payload["provenance"]["source_note_sha256"]
    review_path = write_review(tmp_path, payload)
    result = run_script("--review", review_path, "--run-id", "packet_from_intake_candidate_016", "--out-root", tmp_path / "out")
    assert result.returncode != 0


def test_rejects_registry_promotion_authorization(tmp_path):
    payload = candidate_review_payload()
    payload["registry_promotion_authorized"] = True
    review_path = write_review(tmp_path, payload)
    result = run_script("--review", review_path, "--run-id", "packet_from_intake_candidate_017", "--out-root", tmp_path / "out")
    assert result.returncode != 0


def test_rejects_runtime_rule_creation_authorization(tmp_path):
    payload = candidate_review_payload()
    payload["runtime_rule_creation_authorized"] = True
    review_path = write_review(tmp_path, payload)
    result = run_script("--review", review_path, "--run-id", "packet_from_intake_candidate_018", "--out-root", tmp_path / "out")
    assert result.returncode != 0


def test_rejects_runtime_rule_install_authorization(tmp_path):
    payload = candidate_review_payload()
    payload["runtime_rule_install_authorized"] = True
    review_path = write_review(tmp_path, payload)
    result = run_script("--review", review_path, "--run-id", "packet_from_intake_candidate_019", "--out-root", tmp_path / "out")
    assert result.returncode != 0


def test_rejects_model_call_performed(tmp_path):
    payload = candidate_review_payload()
    payload["model_call_performed"] = True
    review_path = write_review(tmp_path, payload)
    result = run_script("--review", review_path, "--run-id", "packet_from_intake_candidate_020", "--out-root", tmp_path / "out")
    assert result.returncode != 0


def test_rejects_candidate_promotion_authorization(tmp_path):
    payload = candidate_review_payload()
    payload["candidate_promotion_authorized"] = True
    review_path = write_review(tmp_path, payload)
    result = run_script("--review", review_path, "--run-id", "packet_from_intake_candidate_021", "--out-root", tmp_path / "out")
    assert result.returncode != 0


def test_performs_no_model_call(tmp_path):
    review_path = write_review(tmp_path, candidate_review_payload())
    out_root = tmp_path / "out"
    result = run_script("--review", review_path, "--run-id", "packet_from_intake_candidate_022", "--out-root", out_root)
    assert result.returncode == 0
    assert result.stderr == ""
