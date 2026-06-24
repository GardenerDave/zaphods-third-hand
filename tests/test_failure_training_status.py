import json

from local_harness.failure_training.status import StatusWriter


def test_status_writer_emits_log_and_jsonl(tmp_path):
    writer = StatusWriter(tmp_path, "cycle_test")
    event = writer.event("collect", "ITEM_COMPLETE", item_id="fail_1", status="ok")

    assert event["cycle_id"] == "cycle_test"
    assert event["phase"] == "collect"
    assert event["event"] == "ITEM_COMPLETE"

    log_text = (tmp_path / "status.log").read_text(encoding="utf-8")
    assert "cycle_test" in log_text
    assert "ITEM_COMPLETE" in log_text
    assert "fail_1" in log_text

    rows = [
        json.loads(line)
        for line in (tmp_path / "status_events.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert len(rows) == 1
    assert rows[0]["item_id"] == "fail_1"
    assert rows[0]["status"] == "ok"
