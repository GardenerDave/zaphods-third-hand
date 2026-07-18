from __future__ import annotations

import json
from pathlib import Path

import pytest

from local_harness.validate_bounded_task_packet_draft import (
    BoundedTaskPacketDraftError,
    validate_bounded_task_packet_draft,
)
from local_harness.validate_messy_input_triage_packet import (
    MessyInputTriagePacketError,
    validate_messy_input_triage_packet,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "local_harness" / "fixtures" / "triage_to_bounded_task_bridge"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def test_valid_bridge_fixture_passes_both_validators():
    source = load_fixture("valid_bridge_001.source_triage_packet.json")
    draft = load_fixture("valid_bridge_001.bounded_task_packet_draft.json")

    source_result = validate_messy_input_triage_packet(source)
    draft_result = validate_bounded_task_packet_draft(draft)

    assert source_result["validation_status"] == "passed"
    assert draft_result["validation_status"] == "passed"
    assert source["review_required"] is True
    assert draft["review_required"] is True
    assert draft["downstream_use_status"] == "prohibited_until_review"
    assert draft["automation_status"] == "not_automated"
    assert draft["queue_handoff_status"] == "not_inserted"


def test_invalid_source_fixture_fails_closed():
    source = load_fixture("invalid_source_missing_review_required.source_triage_packet.json")
    with pytest.raises(MessyInputTriagePacketError, match="review_required"):
        validate_messy_input_triage_packet(source)


@pytest.mark.parametrize(
    "fixture_name, expected",
    [
        (
            "invalid_bounded_task_queue_inserted.bounded_task_packet_draft.json",
            "queue_handoff_status",
        ),
        (
            "invalid_bounded_task_unsafe_action.bounded_task_packet_draft.json",
            "unsafe authority",
        ),
    ],
)
def test_invalid_bounded_task_fixtures_fail_closed(fixture_name, expected):
    draft = load_fixture(fixture_name)
    with pytest.raises(BoundedTaskPacketDraftError, match=expected):
        validate_bounded_task_packet_draft(draft)


def test_valid_bridge_fixture_has_no_model_dependency():
    # The fixture pack is deterministic and model-free; validation only reads JSON.
    source = load_fixture("valid_bridge_001.source_triage_packet.json")
    draft = load_fixture("valid_bridge_001.bounded_task_packet_draft.json")
    validate_messy_input_triage_packet(source)
    validate_bounded_task_packet_draft(draft)

