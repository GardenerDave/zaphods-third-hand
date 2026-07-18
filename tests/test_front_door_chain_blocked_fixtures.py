from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CASES_DIR = ROOT / "local_harness" / "fixtures" / "front_door_chain_blocked_cases"
REVIEW_SCRIPT = ROOT / "local_harness" / "review_front_door_chain.py"


def case_ids() -> list[str]:
    return sorted({path.name.split(".", 1)[0] for path in CASES_DIR.glob("*.expected.json")})


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def flatten_strings(value) -> list[str]:
    items: list[str] = []
    if isinstance(value, str):
        items.append(value)
    elif isinstance(value, dict):
        for nested in value.values():
            items.extend(flatten_strings(nested))
    elif isinstance(value, list):
        for nested in value:
            items.extend(flatten_strings(nested))
    return items


def run_review(case_id: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(REVIEW_SCRIPT),
            "--triage-packet",
            str(CASES_DIR / f"{case_id}.triage_packet.json"),
            "--bounded-task-packet",
            str(CASES_DIR / f"{case_id}.bounded_task_packet_draft.json"),
            "--review-packet",
            str(CASES_DIR / f"{case_id}.review_packet.json"),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_blocked_fixture_pack_has_expected_files():
    ids = case_ids()
    assert len(ids) >= 3
    for case_id in ids:
        for suffix in [
            ".messy_input.txt",
            ".triage_packet.json",
            ".bounded_task_packet_draft.json",
            ".review_packet.json",
            ".expected.json",
        ]:
            path = CASES_DIR / f"{case_id}{suffix}"
            assert path.is_file(), path
        assert (CASES_DIR / f"{case_id}.messy_input.txt").read_text(encoding="utf-8").strip()


def test_blocked_fixture_cases_fail_closed():
    for case_id in case_ids():
        expected = load_json(CASES_DIR / f"{case_id}.expected.json")
        result = run_review(case_id)
        assert result.returncode != 0
        payload = json.loads(result.stdout)
        assert payload["review_status"] == expected["expected_review_status"]
        assert payload["automation_status"] == expected["authority_expectation"]["automation_status"]
        assert payload["queue_handoff_status"] == expected["authority_expectation"]["queue_handoff_status"]
        assert payload["downstream_use_status"] == expected["authority_expectation"]["downstream_use_status"]
        assert payload["repo_mutation_status"] == expected["authority_expectation"]["repo_mutation_status"]

        diagnostics = flatten_strings(payload)
        for substring in expected["expected_diagnostic_substrings"]:
            assert any(substring in item for item in diagnostics), (case_id, substring, diagnostics)

        assert payload["review_status"] != "ready_for_human_review"


def test_blocked_fixture_files_do_not_reference_work_tree():
    for case_id in case_ids():
        for suffix in [
            ".messy_input.txt",
            ".triage_packet.json",
            ".bounded_task_packet_draft.json",
            ".review_packet.json",
            ".expected.json",
        ]:
            path = CASES_DIR / f"{case_id}{suffix}"
            assert ".work" not in path.read_text(encoding="utf-8")
