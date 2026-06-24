import json
from pathlib import Path


SCHEMA_DIR = Path("schemas")


def load_schema(name: str) -> dict:
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


def test_failure_event_schema_is_valid_json():
    schema = load_schema("failure_event.schema.json")

    assert schema["title"] == "Failure Event"
    assert schema["type"] == "object"


def test_failure_event_schema_requires_core_provenance_fields():
    schema = load_schema("failure_event.schema.json")
    required = set(schema["required"])

    assert "id" in required
    assert "cycle_id" in required
    assert "source_run_id" in required
    assert "model_id" in required
    assert "probe_id" in required
    assert "prompt_hash" in required
    assert "raw_output_hash" in required


def test_failure_event_score_result_is_controlled():
    schema = load_schema("failure_event.schema.json")
    allowed = schema["properties"]["score_result"]["enum"]

    assert allowed == ["fail", "partial", "unknown"]
