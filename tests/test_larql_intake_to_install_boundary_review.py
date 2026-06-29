from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/larql_intake_to_install_boundary_review.py"


def intake_candidate_payload() -> dict:
    return {
        "allowed_claim": "the noisy note can be reduced into a bounded candidate scaffold",
        "authority_boundaries_preserved": True,
        "candidate_id": "larql_intake_smoke_unsupported_file_target_authority_candidate",
        "candidate_promotion_authorized": False,
        "evidence_boundary": "single synthetic noisy note only",
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
        "model_call_performed": False,
        "notes": [
            "Independent candidate drafting is model-free.",
            "The drafted candidate remains held for supervised review.",
            "Registry promotion is not authorized.",
            "The completed registry remains unchanged.",
        ],
        "proposed_rule_family_id": "unsupported_file_target_authority",
        "provenance": {
            "source_note_excerpt": "messy note about allowed_files and docs/ROADMAP.md",
            "source_note_path": "tests/fixtures/larql_intake_smoke_noisy_note.txt",
            "source_note_sha256": "fbe869a7d5bb1f2107c14d70584f6db765b2d992a2346bf10eae70aa5e12b227",
        },
        "registry_promotion_authorized": False,
        "report_type": "larql_intake_smoke.v0",
        "required_next_step": "draft_larql_candidate_from_reviewed_intake",
        "runtime_rule_creation_authorized": False,
        "runtime_rule_install_authorized": False,
        "source_failure_id": "synthetic_unsupported_file_target_authority_noisy_note.real",
        "status": "held_for_supervised_review",
    }


def intake_review_payload() -> dict:
    return {
        "allowed_claim": "the noisy note can be reduced into a bounded candidate scaffold",
        "authority_boundaries_preserved": True,
        "candidate_id": "larql_intake_smoke_unsupported_file_target_authority_candidate",
        "candidate_promotion_authorized": False,
        "evidence_boundary": "single synthetic noisy note only",
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
        "model_call_performed": False,
        "notes": [
            "Independent candidate review is model-free.",
            "The draft remains held for runtime-rule packet drafting.",
            "Registry promotion is not authorized.",
            "The completed registry remains unchanged.",
        ],
        "proposed_rule_family_id": "unsupported_file_target_authority",
        "provenance": {
            "source_note_excerpt": "messy note about allowed_files and docs/ROADMAP.md",
            "source_note_path": "tests/fixtures/larql_intake_smoke_noisy_note.txt",
            "source_note_sha256": "fbe869a7d5bb1f2107c14d70584f6db765b2d992a2346bf10eae70aa5e12b227",
        },
        "registry_promotion_authorized": False,
        "report_type": "larql_intake_review.v0",
        "required_next_step": "draft_larql_candidate_from_reviewed_intake",
        "review_scope": "intake candidate scaffold only",
        "review_status": "accepted_for_candidate_drafting",
        "runtime_rule_creation_authorized": False,
        "model_call_performed": False,
        "source_failure_id": "synthetic_unsupported_file_target_authority_noisy_note.real",
        "source_intake_candidate_path": ".work/larql_intake_smoke/intake_smoke_001/larql_intake_smoke_candidate.json",
    }


def candidate_draft_payload() -> dict:
    return {
        "allowed_claim": "the noisy note can be reduced into a bounded candidate scaffold",
        "authority_boundaries_preserved": True,
        "candidate_id": "larql_intake_smoke_unsupported_file_target_authority_candidate",
        "candidate_promotion_authorized": False,
        "candidate_status": "held_for_candidate_review",
        "drafted_candidate": {
            "allowed_claim": "the noisy note can be reduced into a bounded candidate scaffold",
            "authority_boundary": "allowed_files only; no adjacent, generated, unrelated, or repo-wide edits",
            "candidate_family_id": "unsupported_file_target_authority",
            "candidate_id": "larql_intake_smoke_unsupported_file_target_authority_candidate",
            "evidence_boundary": "single synthetic noisy note only",
            "failure_pattern": "allowed_files boundary treated as exclusive authority",
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
            "required_next_step": "supervised_candidate_review",
            "review_status": "held_for_candidate_review",
            "source_failure_id": "synthetic_unsupported_file_target_authority_noisy_note.real",
        },
        "evidence_boundary": "single synthetic noisy note only",
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
        "model_call_performed": False,
        "notes": [
            "Independent candidate drafting is model-free.",
            "The drafted candidate remains held for supervised review.",
            "Registry promotion is not authorized.",
            "The completed registry remains unchanged.",
        ],
        "proposed_rule_family_id": "unsupported_file_target_authority",
        "provenance": {
            "source_note_excerpt": "messy note about allowed_files and docs/ROADMAP.md",
            "source_note_path": "tests/fixtures/larql_intake_smoke_noisy_note.txt",
            "source_note_sha256": "fbe869a7d5bb1f2107c14d70584f6db765b2d992a2346bf10eae70aa5e12b227",
        },
        "registry_promotion_authorized": False,
        "report_type": "larql_candidate_from_intake.v0",
        "required_next_step": "supervised_candidate_review",
        "runtime_rule_creation_authorized": False,
        "runtime_rule_install_authorized": False,
        "source_failure_id": "synthetic_unsupported_file_target_authority_noisy_note.real",
        "source_review_artifact_path": ".work/larql_intake_reviews/intake_review_001/larql_intake_review.json",
    }


def candidate_review_payload() -> dict:
    payload = candidate_draft_payload()
    payload["reviewed_candidate"] = {
        "allowed_claim": "the noisy note can be reduced into a bounded candidate scaffold",
        "authority_boundary": "allowed_files only; no adjacent, generated, unrelated, or repo-wide edits",
        "candidate_family_id": "unsupported_file_target_authority",
        "candidate_id": "larql_intake_smoke_unsupported_file_target_authority_candidate",
        "evidence_boundary": "single synthetic noisy note only",
        "failure_pattern": "allowed_files boundary treated as exclusive authority",
        "held_actions": payload["held_actions"],
        "required_next_step": "draft_runtime_rule_packet_from_reviewed_candidate",
        "review_verdict": "accepted_for_runtime_rule_packet_drafting",
        "source_failure_id": "synthetic_unsupported_file_target_authority_noisy_note.real",
    }
    payload["report_type"] = "larql_candidate_review_from_intake.v0"
    payload["review_scope"] = "candidate draft from reviewed intake only"
    payload["review_status"] = "accepted_for_runtime_rule_packet_drafting"
    payload["required_next_step"] = "draft_runtime_rule_packet_from_reviewed_candidate"
    payload["source_candidate_draft_path"] = ".work/larql_candidate_from_intake/candidate_from_intake_001/larql_candidate_draft.json"
    return payload


def packet_draft_payload() -> dict:
    return {
        "allowed_claim": "only listed files are authorized targets",
        "authority_boundaries_preserved": True,
        "candidate_id": "larql_intake_smoke_unsupported_file_target_authority_candidate",
        "candidate_promotion_authorized": False,
        "evidence_boundary": "single synthetic noisy note only",
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
        "model_call_performed": False,
        "notes": [
            "Independent packet drafting is model-free.",
            "The packet draft remains held for supervised packet review.",
            "Registry promotion is not authorized.",
            "The completed registry remains unchanged.",
            "This packet does not create or install a runtime rule.",
        ],
        "packet_promotion_authorized": False,
        "packet_status": "held_for_packet_review",
        "proposed_rule_family_id": "unsupported_file_target_authority",
        "provenance": {
            "source_note_excerpt": "messy note about allowed_files and docs/ROADMAP.md",
            "source_note_path": "tests/fixtures/larql_intake_smoke_noisy_note.txt",
            "source_note_sha256": "fbe869a7d5bb1f2107c14d70584f6db765b2d992a2346bf10eae70aa5e12b227",
        },
        "registry_promotion_authorized": False,
        "report_type": "larql_packet_from_intake_candidate.v0",
        "required_next_step": "supervised_runtime_rule_packet_review",
        "runtime_rule_creation_authorized": False,
        "runtime_rule_install_authorized": False,
        "runtime_rule_packet_draft": {
            "allowed_claim": "only listed files are authorized targets",
            "authority_boundary": "allowed_files only; no adjacent, generated, unrelated, or repo-wide edits",
            "candidate_id": "larql_intake_smoke_unsupported_file_target_authority_candidate",
            "evidence_boundary": "single synthetic noisy note only",
            "failure_pattern": "allowed_files boundary treated as exclusive authority",
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
            "json_contract": {
                "allowed_claim": "only listed files are authorized targets",
                "evidence_boundary": "allowed files only",
                "evidence_to_preserve": [
                    "allowed_files list",
                    "requested target file",
                    "out-of-scope file",
                ],
                "held_claims": [
                    "modify any repo file",
                    "touch adjacent files",
                    "update generated files",
                    "fix unrelated files",
                    "expand patch scope",
                ],
                "outside_file_modification_authorized": False,
                "required_next_step": "request explicit scope expansion or review",
            },
            "packet_family_id": "unsupported_file_target_authority",
            "required_next_step": "supervised_runtime_rule_packet_review",
            "review_status": "held_for_packet_review",
            "source_allowed_claim": "the noisy note can be reduced into a bounded candidate scaffold",
            "source_failure_id": "synthetic_unsupported_file_target_authority_noisy_note.real",
        },
        "source_allowed_claim": "the noisy note can be reduced into a bounded candidate scaffold",
        "source_candidate_review_path": ".work/larql_candidate_reviews_from_intake/candidate_review_from_intake_001/larql_candidate_review.json",
        "source_failure_id": "synthetic_unsupported_file_target_authority_noisy_note.real",
    }


def packet_review_payload() -> dict:
    packet = packet_draft_payload()
    packet["reviewed_packet"] = {
        "allowed_claim": "only listed files are authorized targets",
        "authority_boundary": "allowed_files only; no adjacent, generated, unrelated, or repo-wide edits",
        "candidate_id": "larql_intake_smoke_unsupported_file_target_authority_candidate",
        "evidence_boundary": "single synthetic noisy note only",
        "failure_pattern": "allowed_files boundary treated as exclusive authority",
        "held_actions": packet["held_actions"],
        "install_authorized": False,
        "json_contract": packet["runtime_rule_packet_draft"]["json_contract"],
        "packet_family_id": "unsupported_file_target_authority",
        "required_next_step": "explicit_local_install_boundary_review",
        "review_verdict": "held_at_install_boundary",
        "source_allowed_claim": "the noisy note can be reduced into a bounded candidate scaffold",
        "source_failure_id": "synthetic_unsupported_file_target_authority_noisy_note.real",
    }
    packet["report_type"] = "larql_packet_review_from_intake_candidate.v0"
    packet["review_scope"] = "runtime-rule packet draft from reviewed intake candidate only"
    packet["review_status"] = "held_at_install_boundary"
    packet["required_next_step"] = "explicit_local_install_boundary_review"
    packet["install_authorized"] = False
    return packet


def run_script(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def write_json(tmp_path: Path, payload: dict, name: str) -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_review(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_help_works():
    result = run_script("--help")
    assert result.returncode == 0
    assert "usage:" in result.stdout.lower()


def test_accepts_valid_full_chain_fixture(tmp_path):
    out_root = tmp_path / "out"
    paths = {
        "intake_candidate": write_json(tmp_path, intake_candidate_payload(), "intake_candidate.json"),
        "intake_review": write_json(tmp_path, intake_review_payload(), "intake_review.json"),
        "candidate_draft": write_json(tmp_path, candidate_draft_payload(), "candidate_draft.json"),
        "candidate_review": write_json(tmp_path, candidate_review_payload(), "candidate_review.json"),
        "packet_draft": write_json(tmp_path, packet_draft_payload(), "packet_draft.json"),
        "packet_review": write_json(tmp_path, packet_review_payload(), "packet_review.json"),
    }
    result = run_script(
        "--intake-candidate",
        paths["intake_candidate"],
        "--intake-review",
        paths["intake_review"],
        "--candidate-draft",
        paths["candidate_draft"],
        "--candidate-review",
        paths["candidate_review"],
        "--packet-draft",
        paths["packet_draft"],
        "--packet-review",
        paths["packet_review"],
        "--run-id",
        "intake_to_install_boundary_001",
        "--out-root",
        out_root,
    )
    assert result.returncode == 0
    review = load_review(out_root / "intake_to_install_boundary_001/larql_intake_to_install_boundary_chain_review.json")
    assert review["report_type"] == "larql_intake_to_install_boundary_chain_review.v0"
    assert review["review_status"] == "chain_reviewed_install_boundary_hold"
    assert review["chain_status"] == "held_at_install_boundary"
    assert review["stage_count"] == 6
    assert review["source_failure_id"] == "synthetic_unsupported_file_target_authority_noisy_note.real"
    assert review["candidate_id"] == "larql_intake_smoke_unsupported_file_target_authority_candidate"
    assert review["proposed_rule_family_id"] == "unsupported_file_target_authority"
    assert review["packet_allowed_claim"] == "only listed files are authorized targets"
    assert review["source_allowed_claim"] == "the noisy note can be reduced into a bounded candidate scaffold"
    assert review["final_required_next_step"] == "explicit_local_install_boundary_review"
    assert review["install_authorized"] is False
    assert review["registry_promotion_authorized"] is False
    assert review["runtime_rule_creation_authorized"] is False
    assert review["runtime_rule_install_authorized"] is False
    assert review["model_call_performed"] is False
    assert review["candidate_promotion_authorized"] is False
    assert review["packet_promotion_authorized"] is False
    assert review["authority_boundaries_preserved"] is True
    assert len(review["stages"]) == 6


def test_writes_chain_review_markdown(tmp_path):
    out_root = tmp_path / "out"
    paths = {
        "intake_candidate": write_json(tmp_path, intake_candidate_payload(), "intake_candidate.json"),
        "intake_review": write_json(tmp_path, intake_review_payload(), "intake_review.json"),
        "candidate_draft": write_json(tmp_path, candidate_draft_payload(), "candidate_draft.json"),
        "candidate_review": write_json(tmp_path, candidate_review_payload(), "candidate_review.json"),
        "packet_draft": write_json(tmp_path, packet_draft_payload(), "packet_draft.json"),
        "packet_review": write_json(tmp_path, packet_review_payload(), "packet_review.json"),
    }
    run_script(
        "--intake-candidate",
        paths["intake_candidate"],
        "--intake-review",
        paths["intake_review"],
        "--candidate-draft",
        paths["candidate_draft"],
        "--candidate-review",
        paths["candidate_review"],
        "--packet-draft",
        paths["packet_draft"],
        "--packet-review",
        paths["packet_review"],
        "--run-id",
        "intake_to_install_boundary_002",
        "--out-root",
        out_root,
    )
    assert (out_root / "intake_to_install_boundary_002/larql_intake_to_install_boundary_chain_review.md").exists()


def test_chain_review_includes_all_six_stages(tmp_path):
    out_root = tmp_path / "out"
    paths = {
        "intake_candidate": write_json(tmp_path, intake_candidate_payload(), "intake_candidate.json"),
        "intake_review": write_json(tmp_path, intake_review_payload(), "intake_review.json"),
        "candidate_draft": write_json(tmp_path, candidate_draft_payload(), "candidate_draft.json"),
        "candidate_review": write_json(tmp_path, candidate_review_payload(), "candidate_review.json"),
        "packet_draft": write_json(tmp_path, packet_draft_payload(), "packet_draft.json"),
        "packet_review": write_json(tmp_path, packet_review_payload(), "packet_review.json"),
    }
    run_script(
        "--intake-candidate",
        paths["intake_candidate"],
        "--intake-review",
        paths["intake_review"],
        "--candidate-draft",
        paths["candidate_draft"],
        "--candidate-review",
        paths["candidate_review"],
        "--packet-draft",
        paths["packet_draft"],
        "--packet-review",
        paths["packet_review"],
        "--run-id",
        "intake_to_install_boundary_003",
        "--out-root",
        out_root,
    )
    review = load_review(out_root / "intake_to_install_boundary_003/larql_intake_to_install_boundary_chain_review.json")
    assert len(review["stages"]) == 6
    assert [stage["stage"] for stage in review["stages"]] == [
        "intake_candidate",
        "intake_review",
        "candidate_draft",
        "candidate_review",
        "packet_draft",
        "packet_review",
    ]


def test_chain_review_preserves_provenance(tmp_path):
    out_root = tmp_path / "out"
    paths = {
        "intake_candidate": write_json(tmp_path, intake_candidate_payload(), "intake_candidate.json"),
        "intake_review": write_json(tmp_path, intake_review_payload(), "intake_review.json"),
        "candidate_draft": write_json(tmp_path, candidate_draft_payload(), "candidate_draft.json"),
        "candidate_review": write_json(tmp_path, candidate_review_payload(), "candidate_review.json"),
        "packet_draft": write_json(tmp_path, packet_draft_payload(), "packet_draft.json"),
        "packet_review": write_json(tmp_path, packet_review_payload(), "packet_review.json"),
    }
    run_script(
        "--intake-candidate",
        paths["intake_candidate"],
        "--intake-review",
        paths["intake_review"],
        "--candidate-draft",
        paths["candidate_draft"],
        "--candidate-review",
        paths["candidate_review"],
        "--packet-draft",
        paths["packet_draft"],
        "--packet-review",
        paths["packet_review"],
        "--run-id",
        "intake_to_install_boundary_004",
        "--out-root",
        out_root,
    )
    review = load_review(out_root / "intake_to_install_boundary_004/larql_intake_to_install_boundary_chain_review.json")
    assert review["provenance"]["source_note_path"].endswith("larql_intake_smoke_noisy_note.txt")
    assert isinstance(review["provenance"]["source_note_sha256"], str) and review["provenance"]["source_note_sha256"]


def test_chain_review_preserves_source_allowed_claim(tmp_path):
    out_root = tmp_path / "out"
    paths = {
        "intake_candidate": write_json(tmp_path, intake_candidate_payload(), "intake_candidate.json"),
        "intake_review": write_json(tmp_path, intake_review_payload(), "intake_review.json"),
        "candidate_draft": write_json(tmp_path, candidate_draft_payload(), "candidate_draft.json"),
        "candidate_review": write_json(tmp_path, candidate_review_payload(), "candidate_review.json"),
        "packet_draft": write_json(tmp_path, packet_draft_payload(), "packet_draft.json"),
        "packet_review": write_json(tmp_path, packet_review_payload(), "packet_review.json"),
    }
    run_script(
        "--intake-candidate",
        paths["intake_candidate"],
        "--intake-review",
        paths["intake_review"],
        "--candidate-draft",
        paths["candidate_draft"],
        "--candidate-review",
        paths["candidate_review"],
        "--packet-draft",
        paths["packet_draft"],
        "--packet-review",
        paths["packet_review"],
        "--run-id",
        "intake_to_install_boundary_005",
        "--out-root",
        out_root,
    )
    review = load_review(out_root / "intake_to_install_boundary_005/larql_intake_to_install_boundary_chain_review.json")
    assert review["source_allowed_claim"] == "the noisy note can be reduced into a bounded candidate scaffold"


def test_chain_review_keeps_packet_allowed_claim_as_packet_claim(tmp_path):
    out_root = tmp_path / "out"
    paths = {
        "intake_candidate": write_json(tmp_path, intake_candidate_payload(), "intake_candidate.json"),
        "intake_review": write_json(tmp_path, intake_review_payload(), "intake_review.json"),
        "candidate_draft": write_json(tmp_path, candidate_draft_payload(), "candidate_draft.json"),
        "candidate_review": write_json(tmp_path, candidate_review_payload(), "candidate_review.json"),
        "packet_draft": write_json(tmp_path, packet_draft_payload(), "packet_draft.json"),
        "packet_review": write_json(tmp_path, packet_review_payload(), "packet_review.json"),
    }
    run_script(
        "--intake-candidate",
        paths["intake_candidate"],
        "--intake-review",
        paths["intake_review"],
        "--candidate-draft",
        paths["candidate_draft"],
        "--candidate-review",
        paths["candidate_review"],
        "--packet-draft",
        paths["packet_draft"],
        "--packet-review",
        paths["packet_review"],
        "--run-id",
        "intake_to_install_boundary_006",
        "--out-root",
        out_root,
    )
    review = load_review(out_root / "intake_to_install_boundary_006/larql_intake_to_install_boundary_chain_review.json")
    assert review["packet_allowed_claim"] == "only listed files are authorized targets"


def test_chain_review_keeps_install_authorized_false(tmp_path):
    out_root = tmp_path / "out"
    paths = {
        "intake_candidate": write_json(tmp_path, intake_candidate_payload(), "intake_candidate.json"),
        "intake_review": write_json(tmp_path, intake_review_payload(), "intake_review.json"),
        "candidate_draft": write_json(tmp_path, candidate_draft_payload(), "candidate_draft.json"),
        "candidate_review": write_json(tmp_path, candidate_review_payload(), "candidate_review.json"),
        "packet_draft": write_json(tmp_path, packet_draft_payload(), "packet_draft.json"),
        "packet_review": write_json(tmp_path, packet_review_payload(), "packet_review.json"),
    }
    run_script(
        "--intake-candidate",
        paths["intake_candidate"],
        "--intake-review",
        paths["intake_review"],
        "--candidate-draft",
        paths["candidate_draft"],
        "--candidate-review",
        paths["candidate_review"],
        "--packet-draft",
        paths["packet_draft"],
        "--packet-review",
        paths["packet_review"],
        "--run-id",
        "intake_to_install_boundary_007",
        "--out-root",
        out_root,
    )
    review = load_review(out_root / "intake_to_install_boundary_007/larql_intake_to_install_boundary_chain_review.json")
    assert review["install_authorized"] is False


def test_chain_review_keeps_registry_promotion_false(tmp_path):
    out_root = tmp_path / "out"
    paths = {
        "intake_candidate": write_json(tmp_path, intake_candidate_payload(), "intake_candidate.json"),
        "intake_review": write_json(tmp_path, intake_review_payload(), "intake_review.json"),
        "candidate_draft": write_json(tmp_path, candidate_draft_payload(), "candidate_draft.json"),
        "candidate_review": write_json(tmp_path, candidate_review_payload(), "candidate_review.json"),
        "packet_draft": write_json(tmp_path, packet_draft_payload(), "packet_draft.json"),
        "packet_review": write_json(tmp_path, packet_review_payload(), "packet_review.json"),
    }
    run_script(
        "--intake-candidate",
        paths["intake_candidate"],
        "--intake-review",
        paths["intake_review"],
        "--candidate-draft",
        paths["candidate_draft"],
        "--candidate-review",
        paths["candidate_review"],
        "--packet-draft",
        paths["packet_draft"],
        "--packet-review",
        paths["packet_review"],
        "--run-id",
        "intake_to_install_boundary_008",
        "--out-root",
        out_root,
    )
    review = load_review(out_root / "intake_to_install_boundary_008/larql_intake_to_install_boundary_chain_review.json")
    assert review["registry_promotion_authorized"] is False


def test_chain_review_keeps_runtime_rule_creation_false(tmp_path):
    out_root = tmp_path / "out"
    paths = {
        "intake_candidate": write_json(tmp_path, intake_candidate_payload(), "intake_candidate.json"),
        "intake_review": write_json(tmp_path, intake_review_payload(), "intake_review.json"),
        "candidate_draft": write_json(tmp_path, candidate_draft_payload(), "candidate_draft.json"),
        "candidate_review": write_json(tmp_path, candidate_review_payload(), "candidate_review.json"),
        "packet_draft": write_json(tmp_path, packet_draft_payload(), "packet_draft.json"),
        "packet_review": write_json(tmp_path, packet_review_payload(), "packet_review.json"),
    }
    run_script(
        "--intake-candidate",
        paths["intake_candidate"],
        "--intake-review",
        paths["intake_review"],
        "--candidate-draft",
        paths["candidate_draft"],
        "--candidate-review",
        paths["candidate_review"],
        "--packet-draft",
        paths["packet_draft"],
        "--packet-review",
        paths["packet_review"],
        "--run-id",
        "intake_to_install_boundary_009",
        "--out-root",
        out_root,
    )
    review = load_review(out_root / "intake_to_install_boundary_009/larql_intake_to_install_boundary_chain_review.json")
    assert review["runtime_rule_creation_authorized"] is False


def test_chain_review_keeps_runtime_rule_install_false(tmp_path):
    out_root = tmp_path / "out"
    paths = {
        "intake_candidate": write_json(tmp_path, intake_candidate_payload(), "intake_candidate.json"),
        "intake_review": write_json(tmp_path, intake_review_payload(), "intake_review.json"),
        "candidate_draft": write_json(tmp_path, candidate_draft_payload(), "candidate_draft.json"),
        "candidate_review": write_json(tmp_path, candidate_review_payload(), "candidate_review.json"),
        "packet_draft": write_json(tmp_path, packet_draft_payload(), "packet_draft.json"),
        "packet_review": write_json(tmp_path, packet_review_payload(), "packet_review.json"),
    }
    run_script(
        "--intake-candidate",
        paths["intake_candidate"],
        "--intake-review",
        paths["intake_review"],
        "--candidate-draft",
        paths["candidate_draft"],
        "--candidate-review",
        paths["candidate_review"],
        "--packet-draft",
        paths["packet_draft"],
        "--packet-review",
        paths["packet_review"],
        "--run-id",
        "intake_to_install_boundary_010",
        "--out-root",
        out_root,
    )
    review = load_review(out_root / "intake_to_install_boundary_010/larql_intake_to_install_boundary_chain_review.json")
    assert review["runtime_rule_install_authorized"] is False


def test_chain_review_keeps_model_call_false(tmp_path):
    out_root = tmp_path / "out"
    paths = {
        "intake_candidate": write_json(tmp_path, intake_candidate_payload(), "intake_candidate.json"),
        "intake_review": write_json(tmp_path, intake_review_payload(), "intake_review.json"),
        "candidate_draft": write_json(tmp_path, candidate_draft_payload(), "candidate_draft.json"),
        "candidate_review": write_json(tmp_path, candidate_review_payload(), "candidate_review.json"),
        "packet_draft": write_json(tmp_path, packet_draft_payload(), "packet_draft.json"),
        "packet_review": write_json(tmp_path, packet_review_payload(), "packet_review.json"),
    }
    run_script(
        "--intake-candidate",
        paths["intake_candidate"],
        "--intake-review",
        paths["intake_review"],
        "--candidate-draft",
        paths["candidate_draft"],
        "--candidate-review",
        paths["candidate_review"],
        "--packet-draft",
        paths["packet_draft"],
        "--packet-review",
        paths["packet_review"],
        "--run-id",
        "intake_to_install_boundary_011",
        "--out-root",
        out_root,
    )
    review = load_review(out_root / "intake_to_install_boundary_011/larql_intake_to_install_boundary_chain_review.json")
    assert review["model_call_performed"] is False


def test_chain_review_keeps_candidate_promotion_false(tmp_path):
    out_root = tmp_path / "out"
    paths = {
        "intake_candidate": write_json(tmp_path, intake_candidate_payload(), "intake_candidate.json"),
        "intake_review": write_json(tmp_path, intake_review_payload(), "intake_review.json"),
        "candidate_draft": write_json(tmp_path, candidate_draft_payload(), "candidate_draft.json"),
        "candidate_review": write_json(tmp_path, candidate_review_payload(), "candidate_review.json"),
        "packet_draft": write_json(tmp_path, packet_draft_payload(), "packet_draft.json"),
        "packet_review": write_json(tmp_path, packet_review_payload(), "packet_review.json"),
    }
    run_script(
        "--intake-candidate",
        paths["intake_candidate"],
        "--intake-review",
        paths["intake_review"],
        "--candidate-draft",
        paths["candidate_draft"],
        "--candidate-review",
        paths["candidate_review"],
        "--packet-draft",
        paths["packet_draft"],
        "--packet-review",
        paths["packet_review"],
        "--run-id",
        "intake_to_install_boundary_012",
        "--out-root",
        out_root,
    )
    review = load_review(out_root / "intake_to_install_boundary_012/larql_intake_to_install_boundary_chain_review.json")
    assert review["candidate_promotion_authorized"] is False


def test_chain_review_keeps_packet_promotion_false(tmp_path):
    out_root = tmp_path / "out"
    paths = {
        "intake_candidate": write_json(tmp_path, intake_candidate_payload(), "intake_candidate.json"),
        "intake_review": write_json(tmp_path, intake_review_payload(), "intake_review.json"),
        "candidate_draft": write_json(tmp_path, candidate_draft_payload(), "candidate_draft.json"),
        "candidate_review": write_json(tmp_path, candidate_review_payload(), "candidate_review.json"),
        "packet_draft": write_json(tmp_path, packet_draft_payload(), "packet_draft.json"),
        "packet_review": write_json(tmp_path, packet_review_payload(), "packet_review.json"),
    }
    run_script(
        "--intake-candidate",
        paths["intake_candidate"],
        "--intake-review",
        paths["intake_review"],
        "--candidate-draft",
        paths["candidate_draft"],
        "--candidate-review",
        paths["candidate_review"],
        "--packet-draft",
        paths["packet_draft"],
        "--packet-review",
        paths["packet_review"],
        "--run-id",
        "intake_to_install_boundary_013",
        "--out-root",
        out_root,
    )
    review = load_review(out_root / "intake_to_install_boundary_013/larql_intake_to_install_boundary_chain_review.json")
    assert review["packet_promotion_authorized"] is False


def test_chain_review_status_is_chain_reviewed_install_boundary_hold(tmp_path):
    out_root = tmp_path / "out"
    paths = {
        "intake_candidate": write_json(tmp_path, intake_candidate_payload(), "intake_candidate.json"),
        "intake_review": write_json(tmp_path, intake_review_payload(), "intake_review.json"),
        "candidate_draft": write_json(tmp_path, candidate_draft_payload(), "candidate_draft.json"),
        "candidate_review": write_json(tmp_path, candidate_review_payload(), "candidate_review.json"),
        "packet_draft": write_json(tmp_path, packet_draft_payload(), "packet_draft.json"),
        "packet_review": write_json(tmp_path, packet_review_payload(), "packet_review.json"),
    }
    run_script(
        "--intake-candidate",
        paths["intake_candidate"],
        "--intake-review",
        paths["intake_review"],
        "--candidate-draft",
        paths["candidate_draft"],
        "--candidate-review",
        paths["candidate_review"],
        "--packet-draft",
        paths["packet_draft"],
        "--packet-review",
        paths["packet_review"],
        "--run-id",
        "intake_to_install_boundary_014",
        "--out-root",
        out_root,
    )
    review = load_review(out_root / "intake_to_install_boundary_014/larql_intake_to_install_boundary_chain_review.json")
    assert review["review_status"] == "chain_reviewed_install_boundary_hold"


def test_rejects_mismatched_source_failure_id_across_stages(tmp_path):
    payloads = {
        "intake_candidate": intake_candidate_payload(),
        "intake_review": intake_review_payload(),
        "candidate_draft": candidate_draft_payload(),
        "candidate_review": candidate_review_payload(),
        "packet_draft": packet_draft_payload(),
        "packet_review": packet_review_payload(),
    }
    payloads["packet_review"]["source_failure_id"] = "different.real"
    paths = {name: write_json(tmp_path, payload, f"{name}.json") for name, payload in payloads.items()}
    result = run_script(
        "--intake-candidate",
        paths["intake_candidate"],
        "--intake-review",
        paths["intake_review"],
        "--candidate-draft",
        paths["candidate_draft"],
        "--candidate-review",
        paths["candidate_review"],
        "--packet-draft",
        paths["packet_draft"],
        "--packet-review",
        paths["packet_review"],
        "--run-id",
        "intake_to_install_boundary_015",
        "--out-root",
        tmp_path / "out",
    )
    assert result.returncode != 0


def test_rejects_mismatched_candidate_id_across_stages(tmp_path):
    payloads = {
        "intake_candidate": intake_candidate_payload(),
        "intake_review": intake_review_payload(),
        "candidate_draft": candidate_draft_payload(),
        "candidate_review": candidate_review_payload(),
        "packet_draft": packet_draft_payload(),
        "packet_review": packet_review_payload(),
    }
    payloads["candidate_review"]["candidate_id"] = "different"
    paths = {name: write_json(tmp_path, payload, f"{name}.json") for name, payload in payloads.items()}
    result = run_script(
        "--intake-candidate",
        paths["intake_candidate"],
        "--intake-review",
        paths["intake_review"],
        "--candidate-draft",
        paths["candidate_draft"],
        "--candidate-review",
        paths["candidate_review"],
        "--packet-draft",
        paths["packet_draft"],
        "--packet-review",
        paths["packet_review"],
        "--run-id",
        "intake_to_install_boundary_016",
        "--out-root",
        tmp_path / "out",
    )
    assert result.returncode != 0


def test_rejects_missing_provenance_hash(tmp_path):
    payloads = {
        "intake_candidate": intake_candidate_payload(),
        "intake_review": intake_review_payload(),
        "candidate_draft": candidate_draft_payload(),
        "candidate_review": candidate_review_payload(),
        "packet_draft": packet_draft_payload(),
        "packet_review": packet_review_payload(),
    }
    del payloads["packet_review"]["provenance"]["source_note_sha256"]
    paths = {name: write_json(tmp_path, payload, f"{name}.json") for name, payload in payloads.items()}
    result = run_script(
        "--intake-candidate",
        paths["intake_candidate"],
        "--intake-review",
        paths["intake_review"],
        "--candidate-draft",
        paths["candidate_draft"],
        "--candidate-review",
        paths["candidate_review"],
        "--packet-draft",
        paths["packet_draft"],
        "--packet-review",
        paths["packet_review"],
        "--run-id",
        "intake_to_install_boundary_017",
        "--out-root",
        tmp_path / "out",
    )
    assert result.returncode != 0


def test_rejects_intake_stage_claim_reused_as_packet_allowed_claim(tmp_path):
    payloads = {
        "intake_candidate": intake_candidate_payload(),
        "intake_review": intake_review_payload(),
        "candidate_draft": candidate_draft_payload(),
        "candidate_review": candidate_review_payload(),
        "packet_draft": packet_draft_payload(),
        "packet_review": packet_review_payload(),
    }
    payloads["packet_review"]["allowed_claim"] = payloads["packet_review"]["source_allowed_claim"]
    paths = {name: write_json(tmp_path, payload, f"{name}.json") for name, payload in payloads.items()}
    result = run_script(
        "--intake-candidate",
        paths["intake_candidate"],
        "--intake-review",
        paths["intake_review"],
        "--candidate-draft",
        paths["candidate_draft"],
        "--candidate-review",
        paths["candidate_review"],
        "--packet-draft",
        paths["packet_draft"],
        "--packet-review",
        paths["packet_review"],
        "--run-id",
        "intake_to_install_boundary_018",
        "--out-root",
        tmp_path / "out",
    )
    assert result.returncode != 0


def test_rejects_registry_promotion_authorization(tmp_path):
    payloads = {
        "intake_candidate": intake_candidate_payload(),
        "intake_review": intake_review_payload(),
        "candidate_draft": candidate_draft_payload(),
        "candidate_review": candidate_review_payload(),
        "packet_draft": packet_draft_payload(),
        "packet_review": packet_review_payload(),
    }
    payloads["packet_review"]["registry_promotion_authorized"] = True
    paths = {name: write_json(tmp_path, payload, f"{name}.json") for name, payload in payloads.items()}
    result = run_script(
        "--intake-candidate",
        paths["intake_candidate"],
        "--intake-review",
        paths["intake_review"],
        "--candidate-draft",
        paths["candidate_draft"],
        "--candidate-review",
        paths["candidate_review"],
        "--packet-draft",
        paths["packet_draft"],
        "--packet-review",
        paths["packet_review"],
        "--run-id",
        "intake_to_install_boundary_019",
        "--out-root",
        tmp_path / "out",
    )
    assert result.returncode != 0


def test_rejects_runtime_rule_creation_authorization(tmp_path):
    payloads = {
        "intake_candidate": intake_candidate_payload(),
        "intake_review": intake_review_payload(),
        "candidate_draft": candidate_draft_payload(),
        "candidate_review": candidate_review_payload(),
        "packet_draft": packet_draft_payload(),
        "packet_review": packet_review_payload(),
    }
    payloads["packet_review"]["runtime_rule_creation_authorized"] = True
    paths = {name: write_json(tmp_path, payload, f"{name}.json") for name, payload in payloads.items()}
    result = run_script(
        "--intake-candidate",
        paths["intake_candidate"],
        "--intake-review",
        paths["intake_review"],
        "--candidate-draft",
        paths["candidate_draft"],
        "--candidate-review",
        paths["candidate_review"],
        "--packet-draft",
        paths["packet_draft"],
        "--packet-review",
        paths["packet_review"],
        "--run-id",
        "intake_to_install_boundary_020",
        "--out-root",
        tmp_path / "out",
    )
    assert result.returncode != 0


def test_rejects_runtime_rule_install_authorization(tmp_path):
    payloads = {
        "intake_candidate": intake_candidate_payload(),
        "intake_review": intake_review_payload(),
        "candidate_draft": candidate_draft_payload(),
        "candidate_review": candidate_review_payload(),
        "packet_draft": packet_draft_payload(),
        "packet_review": packet_review_payload(),
    }
    payloads["packet_review"]["runtime_rule_install_authorized"] = True
    paths = {name: write_json(tmp_path, payload, f"{name}.json") for name, payload in payloads.items()}
    result = run_script(
        "--intake-candidate",
        paths["intake_candidate"],
        "--intake-review",
        paths["intake_review"],
        "--candidate-draft",
        paths["candidate_draft"],
        "--candidate-review",
        paths["candidate_review"],
        "--packet-draft",
        paths["packet_draft"],
        "--packet-review",
        paths["packet_review"],
        "--run-id",
        "intake_to_install_boundary_021",
        "--out-root",
        tmp_path / "out",
    )
    assert result.returncode != 0


def test_rejects_model_call_performed(tmp_path):
    payloads = {
        "intake_candidate": intake_candidate_payload(),
        "intake_review": intake_review_payload(),
        "candidate_draft": candidate_draft_payload(),
        "candidate_review": candidate_review_payload(),
        "packet_draft": packet_draft_payload(),
        "packet_review": packet_review_payload(),
    }
    payloads["packet_review"]["model_call_performed"] = True
    paths = {name: write_json(tmp_path, payload, f"{name}.json") for name, payload in payloads.items()}
    result = run_script(
        "--intake-candidate",
        paths["intake_candidate"],
        "--intake-review",
        paths["intake_review"],
        "--candidate-draft",
        paths["candidate_draft"],
        "--candidate-review",
        paths["candidate_review"],
        "--packet-draft",
        paths["packet_draft"],
        "--packet-review",
        paths["packet_review"],
        "--run-id",
        "intake_to_install_boundary_022",
        "--out-root",
        tmp_path / "out",
    )
    assert result.returncode != 0


def test_rejects_candidate_promotion_authorization(tmp_path):
    payloads = {
        "intake_candidate": intake_candidate_payload(),
        "intake_review": intake_review_payload(),
        "candidate_draft": candidate_draft_payload(),
        "candidate_review": candidate_review_payload(),
        "packet_draft": packet_draft_payload(),
        "packet_review": packet_review_payload(),
    }
    payloads["packet_review"]["candidate_promotion_authorized"] = True
    paths = {name: write_json(tmp_path, payload, f"{name}.json") for name, payload in payloads.items()}
    result = run_script(
        "--intake-candidate",
        paths["intake_candidate"],
        "--intake-review",
        paths["intake_review"],
        "--candidate-draft",
        paths["candidate_draft"],
        "--candidate-review",
        paths["candidate_review"],
        "--packet-draft",
        paths["packet_draft"],
        "--packet-review",
        paths["packet_review"],
        "--run-id",
        "intake_to_install_boundary_023",
        "--out-root",
        tmp_path / "out",
    )
    assert result.returncode != 0


def test_rejects_packet_promotion_authorization(tmp_path):
    payloads = {
        "intake_candidate": intake_candidate_payload(),
        "intake_review": intake_review_payload(),
        "candidate_draft": candidate_draft_payload(),
        "candidate_review": candidate_review_payload(),
        "packet_draft": packet_draft_payload(),
        "packet_review": packet_review_payload(),
    }
    payloads["packet_review"]["packet_promotion_authorized"] = True
    paths = {name: write_json(tmp_path, payload, f"{name}.json") for name, payload in payloads.items()}
    result = run_script(
        "--intake-candidate",
        paths["intake_candidate"],
        "--intake-review",
        paths["intake_review"],
        "--candidate-draft",
        paths["candidate_draft"],
        "--candidate-review",
        paths["candidate_review"],
        "--packet-draft",
        paths["packet_draft"],
        "--packet-review",
        paths["packet_review"],
        "--run-id",
        "intake_to_install_boundary_024",
        "--out-root",
        tmp_path / "out",
    )
    assert result.returncode != 0


def test_rejects_install_authorization(tmp_path):
    payloads = {
        "intake_candidate": intake_candidate_payload(),
        "intake_review": intake_review_payload(),
        "candidate_draft": candidate_draft_payload(),
        "candidate_review": candidate_review_payload(),
        "packet_draft": packet_draft_payload(),
        "packet_review": packet_review_payload(),
    }
    payloads["packet_review"]["install_authorized"] = True
    paths = {name: write_json(tmp_path, payload, f"{name}.json") for name, payload in payloads.items()}
    result = run_script(
        "--intake-candidate",
        paths["intake_candidate"],
        "--intake-review",
        paths["intake_review"],
        "--candidate-draft",
        paths["candidate_draft"],
        "--candidate-review",
        paths["candidate_review"],
        "--packet-draft",
        paths["packet_draft"],
        "--packet-review",
        paths["packet_review"],
        "--run-id",
        "intake_to_install_boundary_025",
        "--out-root",
        tmp_path / "out",
    )
    assert result.returncode != 0


def test_performs_no_model_call(tmp_path):
    out_root = tmp_path / "out"
    paths = {
        "intake_candidate": write_json(tmp_path, intake_candidate_payload(), "intake_candidate.json"),
        "intake_review": write_json(tmp_path, intake_review_payload(), "intake_review.json"),
        "candidate_draft": write_json(tmp_path, candidate_draft_payload(), "candidate_draft.json"),
        "candidate_review": write_json(tmp_path, candidate_review_payload(), "candidate_review.json"),
        "packet_draft": write_json(tmp_path, packet_draft_payload(), "packet_draft.json"),
        "packet_review": write_json(tmp_path, packet_review_payload(), "packet_review.json"),
    }
    result = run_script(
        "--intake-candidate",
        paths["intake_candidate"],
        "--intake-review",
        paths["intake_review"],
        "--candidate-draft",
        paths["candidate_draft"],
        "--candidate-review",
        paths["candidate_review"],
        "--packet-draft",
        paths["packet_draft"],
        "--packet-review",
        paths["packet_review"],
        "--run-id",
        "intake_to_install_boundary_026",
        "--out-root",
        out_root,
    )
    assert result.returncode == 0
    assert result.stderr == ""
