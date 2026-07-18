from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CASES_DIR = ROOT / "local_harness" / "fixtures" / "front_door_chain_cases"
REVIEW_SCRIPT = ROOT / "local_harness" / "review_front_door_chain.py"
TRIAGE_VALIDATOR = ROOT / "local_harness" / "validate_messy_input_triage_packet.py"
BOUNDED_VALIDATOR = ROOT / "local_harness" / "validate_bounded_task_packet_draft.py"
REVIEW_VALIDATOR = ROOT / "local_harness" / "validate_bounded_task_review_packet.py"


def case_ids() -> list[str]:
    return sorted({path.name.split(".", 1)[0] for path in CASES_DIR.glob("*.messy_input.txt")})


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def run_validator(script: Path, packet: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), "--packet", str(packet)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def run_review(triage: Path, bounded: Path, review: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(REVIEW_SCRIPT),
            "--triage-packet",
            str(triage),
            "--bounded-task-packet",
            str(bounded),
            "--review-packet",
            str(review),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_fixture_pack_has_expected_case_files():
    ids = case_ids()
    assert len(ids) >= 3
    for case_id in ids:
        for suffix in [
            ".messy_input.txt",
            ".triage_packet.json",
            ".bounded_task_packet_draft.json",
            ".review_packet.json",
        ]:
            path = CASES_DIR / f"{case_id}{suffix}"
            assert path.is_file(), path
        messy = (CASES_DIR / f"{case_id}.messy_input.txt").read_text(encoding="utf-8").strip()
        assert messy


def test_valid_diverse_cases_pass_front_door_chain():
    ids = case_ids()
    assert ids
    for case_id in ids:
        triage = CASES_DIR / f"{case_id}.triage_packet.json"
        bounded = CASES_DIR / f"{case_id}.bounded_task_packet_draft.json"
        review = CASES_DIR / f"{case_id}.review_packet.json"
        triage_result = run_validator(TRIAGE_VALIDATOR, triage)
        bounded_result = run_validator(BOUNDED_VALIDATOR, bounded)
        review_result = run_validator(REVIEW_VALIDATOR, review)
        assert triage_result.returncode == 0, triage_result.stdout + triage_result.stderr
        assert bounded_result.returncode == 0, bounded_result.stdout + bounded_result.stderr
        assert review_result.returncode == 0, review_result.stdout + review_result.stderr
        review_chain = run_review(triage, bounded, review)
        assert review_chain.returncode == 0, review_chain.stdout + review_chain.stderr
        payload = json.loads(review_chain.stdout)
        assert payload["review_status"] == "ready_for_human_review"
        assert payload["automation_status"] == "not_automated"
        assert payload["queue_handoff_status"] == "not_inserted"
        assert payload["downstream_use_status"] == "prohibited_until_review"
        assert payload["repo_mutation_status"] == "not_authorized"
        assert payload["chain_validation"]["validation_status"] == "passed"
        assert payload["scorecard"]["scorecard_status"] == "ready_for_human_review"


def test_fixture_packets_do_not_reference_work_tree():
    for case_id in case_ids():
        for suffix in [
            ".messy_input.txt",
            ".triage_packet.json",
            ".bounded_task_packet_draft.json",
            ".review_packet.json",
        ]:
            path = CASES_DIR / f"{case_id}{suffix}"
            assert ".work" not in path.read_text(encoding="utf-8")
