from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURES_DIR = ROOT / "local_harness" / "fixtures" / "queue_handoff_review"
SCRIPT = ROOT / "local_harness" / "validate_queue_handoff_review.py"


def case_ids() -> list[str]:
    return sorted({path.name.split(".", 1)[0] for path in FIXTURES_DIR.glob("*.expected.json")})


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def run_validator(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(path)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


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


def test_fixture_pack_has_expected_files():
    ids = case_ids()
    assert len(ids) == 10
    for case_id in ids:
        for suffix in [".json", ".expected.json"]:
            path = FIXTURES_DIR / f"{case_id}{suffix}"
            assert path.is_file(), path
        assert (FIXTURES_DIR / f"{case_id}.json").read_text(encoding="utf-8").strip()


def test_queue_handoff_review_fixtures_validate_as_expected():
    for case_id in case_ids():
        expected = load_json(FIXTURES_DIR / f"{case_id}.expected.json")
        fixture = FIXTURES_DIR / f"{case_id}.json"
        result = run_validator(fixture)
        payload = json.loads(result.stdout)
        assert payload["validation_status"] == expected["expected_validation_status"]
        assert result.returncode == (0 if expected["expected_exit_code"] == "zero" else 1)
        if expected["expected_validation_status"] == "passed":
            assert payload["validation_schema"] == "queue_handoff_review_validation_v1"
        diagnostics = flatten_strings(payload)
        if expected["expected_validation_status"] == "passed":
            diagnostics.extend(flatten_strings(load_json(fixture)))
        for substring in expected["expected_diagnostic_substrings"]:
            assert any(substring in item for item in diagnostics), (case_id, substring, diagnostics)


def test_passing_fixtures_preserve_non_authoritative_statuses():
    for case_id in [
        "approved_candidate_valid_001",
        "rejected_valid_001",
        "needs_repair_valid_001",
    ]:
        payload = load_json(FIXTURES_DIR / f"{case_id}.json")
        assert payload["automation_status"] == "not_automated"
        assert payload["queue_handoff_status"] == "not_inserted"
        assert payload["repo_mutation_status"] == "not_authorized"
        assert payload["downstream_use_status"] == "prohibited_until_review"


def test_fixture_files_do_not_reference_work_tree():
    for case_id in case_ids():
        for suffix in [".json", ".expected.json"]:
            path = FIXTURES_DIR / f"{case_id}{suffix}"
            assert ".work" not in path.read_text(encoding="utf-8")
            assert "ready_for_human_review" not in path.read_text(encoding="utf-8")
