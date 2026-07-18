from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURES_DIR = ROOT / "local_harness" / "fixtures" / "queue_approval_path"
SCRIPT = ROOT / "local_harness" / "validate_queue_approval_path.py"


def case_ids() -> list[str]:
    return sorted({path.name.split(".", 1)[0] for path in FIXTURES_DIR.glob("*.expected.json")})


def run_validator(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(path)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_fixture_pack_has_expected_files():
    ids = case_ids()
    assert len(ids) == 12
    for case_id in ids:
        for suffix in [".json", ".expected.json"]:
            path = FIXTURES_DIR / f"{case_id}{suffix}"
            assert path.is_file(), path


def test_queue_approval_path_fixtures_validate_as_expected():
    for case_id in case_ids():
        expected = load_json(FIXTURES_DIR / f"{case_id}.expected.json")
        fixture = FIXTURES_DIR / f"{case_id}.json"
        result = run_validator(fixture)
        payload = json.loads(result.stdout)
        assert payload["validation_status"] == expected["expected_validation_status"], case_id
        assert result.returncode == (0 if expected["expected_exit_code"] == "zero" else 1), case_id
        diagnostics_text = json.dumps(payload, sort_keys=True)
        for substring in expected["expected_diagnostic_substrings"]:
            assert substring in diagnostics_text, (case_id, substring, diagnostics_text)
        for code in expected.get("expected_diagnostic_codes", []):
            assert code in payload["diagnostic_codes"], (case_id, code, payload["diagnostic_codes"])


def test_passing_fixtures_preserve_non_authoritative_statuses():
    for case_id in [
        "approved_manual_candidate_valid_001",
        "rejected_before_insertion_valid_001",
        "needs_repair_before_insertion_valid_001",
    ]:
        payload = load_json(FIXTURES_DIR / f"{case_id}.json")
        assert payload["automation_status"] == "not_automated"
        assert payload["queue_insertion_status"] == "not_inserted"
        assert payload["queue_writing_status"] == "not_implemented"
        assert payload["repo_mutation_status"] == "not_authorized"
        assert payload["downstream_use_status"] == "prohibited_until_review"


def test_fixture_files_do_not_reference_work_tree():
    for case_id in case_ids():
        for suffix in [".json", ".expected.json"]:
            path = FIXTURES_DIR / f"{case_id}{suffix}"
            assert ".work" not in path.read_text(encoding="utf-8")
            assert "ready_for_human_review" not in path.read_text(encoding="utf-8")
