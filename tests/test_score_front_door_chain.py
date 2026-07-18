from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
CHAIN_SCRIPT = ROOT / "local_harness" / "validate_front_door_chain.py"
SCORE_SCRIPT = ROOT / "local_harness" / "score_front_door_chain.py"
TRIAGE_FIXTURE = ROOT / "local_harness" / "fixtures" / "triage_to_bounded_task_bridge" / "valid_bridge_001.source_triage_packet.json"
BOUNDED_FIXTURE = ROOT / "local_harness" / "fixtures" / "triage_to_bounded_task_bridge" / "valid_bridge_001.bounded_task_packet_draft.json"
REVIEW_FIXTURE = ROOT / "local_harness" / "fixtures" / "bounded_task_review_packet" / "valid_review_packet_001.json"


def run_chain(tmp_path: Path, *, triage_path: Path = TRIAGE_FIXTURE, bounded_path: Path = BOUNDED_FIXTURE, review_path: Path = REVIEW_FIXTURE) -> Path:
    chain_result = tmp_path / "chain_result.json"
    with chain_result.open("w", encoding="utf-8") as handle:
        subprocess.run(
            [
                sys.executable,
                str(CHAIN_SCRIPT),
                "--triage-packet",
                str(triage_path),
                "--bounded-task-packet",
                str(bounded_path),
                "--review-packet",
                str(review_path),
            ],
            cwd=ROOT,
            text=True,
            stdout=handle,
            stderr=subprocess.PIPE,
            check=True,
        )
    return chain_result


def score(chain_result: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCORE_SCRIPT),
            "--chain-result",
            str(chain_result),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_ready_chain_scores_ready_for_human_review(tmp_path):
    chain_result = run_chain(tmp_path)
    result = score(chain_result)
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["scorecard_schema"] == "front_door_chain_scorecard_v1"
    assert payload["scorecard_status"] == "ready_for_human_review"
    assert payload["readiness_level"] == "review_ready"
    assert payload["chain_validation_status"] == "passed"
    assert payload["diagnostics"] == []
    assert payload["automation_status"] == "not_automated"
    assert payload["queue_handoff_status"] == "not_inserted"
    assert payload["downstream_use_status"] == "prohibited_until_review"
    assert payload["repo_mutation_status"] == "not_authorized"


def test_blocked_chain_scores_blocked(tmp_path):
    triage = tmp_path / "triage.json"
    triage.write_text(json.dumps({"packet_schema": "messy_input_triage_packet_v1"}), encoding="utf-8")
    chain_result = tmp_path / "blocked_chain.json"
    with chain_result.open("w", encoding="utf-8") as handle:
        subprocess.run(
            [
                sys.executable,
                str(CHAIN_SCRIPT),
                "--triage-packet",
                str(triage),
                "--bounded-task-packet",
                str(BOUNDED_FIXTURE),
                "--review-packet",
                str(REVIEW_FIXTURE),
            ],
            cwd=ROOT,
            text=True,
            stdout=handle,
            stderr=subprocess.PIPE,
            check=False,
        )
    result = score(chain_result)
    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["scorecard_schema"] == "front_door_chain_scorecard_v1"
    assert payload["scorecard_status"] == "blocked"
    assert payload["readiness_level"] == "needs_repair"
    assert payload["chain_validation_status"] == "failed"
    assert payload["diagnostics"]
    assert payload["automation_status"] == "not_automated"
    assert payload["queue_handoff_status"] == "not_inserted"


@pytest.mark.parametrize(
    "payload, expected",
    [
        ("{", "malformed JSON packet"),
        ("[1, 2, 3]", "chain result must be a JSON object"),
    ],
)
def test_cli_malformed_chain_result_is_invalid(tmp_path, payload, expected):
    chain_result = tmp_path / "chain.json"
    chain_result.write_text(payload, encoding="utf-8")
    result = score(chain_result)
    assert result.returncode != 0
    scorecard = json.loads(result.stdout)
    assert scorecard["scorecard_status"] == "invalid"
    assert expected in " ".join(scorecard["diagnostics"])


def test_missing_required_fields_is_invalid(tmp_path):
    chain_result = tmp_path / "chain.json"
    chain_result.write_text(json.dumps({"validation_schema": "front_door_chain_validation_v1"}), encoding="utf-8")
    result = score(chain_result)
    scorecard = json.loads(result.stdout)
    assert result.returncode != 0
    assert scorecard["scorecard_status"] == "invalid"
    assert "missing required fields" in " ".join(scorecard["diagnostics"])


def test_wrong_validation_schema_is_invalid(tmp_path):
    chain_result = tmp_path / "chain.json"
    payload = json.loads(run_chain(tmp_path).read_text(encoding="utf-8"))
    payload["validation_schema"] = "wrong"
    chain_result.write_text(json.dumps(payload), encoding="utf-8")
    result = score(chain_result)
    scorecard = json.loads(result.stdout)
    assert result.returncode != 0
    assert scorecard["scorecard_status"] == "invalid"
    assert "front_door_chain_validation_v1" in " ".join(scorecard["diagnostics"])


def test_blocked_chain_preserves_diagnostics(tmp_path):
    chain_result = tmp_path / "blocked.json"
    chain_result.write_text(
        json.dumps(
            {
                "validation_schema": "front_door_chain_validation_v1",
                "validation_status": "failed",
                "triage_validation_status": "failed",
                "bounded_task_validation_status": "passed",
                "review_packet_validation_status": "passed",
                "linkage_status": "failed",
                "lifecycle_status": "passed",
                "authority_boundary_status": "passed",
                "diagnostics": ["triage layer failed", "missing task summary"],
            }
        ),
        encoding="utf-8",
    )
    result = score(chain_result)
    scorecard = json.loads(result.stdout)
    assert result.returncode != 0
    assert scorecard["scorecard_status"] == "blocked"
    assert "triage layer failed" in scorecard["diagnostics"]
    assert "missing task summary" in scorecard["diagnostics"]


def test_scorecard_never_grants_authority(tmp_path):
    chain_result = run_chain(tmp_path)
    payload = json.loads(score(chain_result).stdout)
    assert payload["automation_status"] == "not_automated"
    assert payload["queue_handoff_status"] == "not_inserted"
    assert payload["downstream_use_status"] == "prohibited_until_review"
    assert payload["repo_mutation_status"] == "not_authorized"

