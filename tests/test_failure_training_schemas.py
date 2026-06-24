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
def test_curriculum_candidate_schema_is_valid_json():
    schema = load_schema("curriculum_candidate.schema.json")

    assert schema["title"] == "Curriculum Candidate"
    assert schema["type"] == "object"


def test_curriculum_candidate_schema_requires_review_and_provenance():
    schema = load_schema("curriculum_candidate.schema.json")
    required = set(schema["required"])

    assert "failure_event_id" in required
    assert "messages" in required
    assert "review_status" in required
    assert "provenance" in required


def test_curriculum_candidate_review_status_is_controlled():
    schema = load_schema("curriculum_candidate.schema.json")
    allowed = schema["properties"]["review_status"]["enum"]

    assert allowed == [
        "candidate",
        "accepted",
        "rejected",
        "holdout_locked",
        "needs_revision",
    ]


def test_curriculum_candidate_message_roles_are_controlled():
    schema = load_schema("curriculum_candidate.schema.json")
    role_enum = schema["properties"]["messages"]["items"]["properties"]["role"]["enum"]

    assert role_enum == ["system", "user", "assistant"]
def test_training_row_schema_is_valid_json():
    schema = load_schema("training_row.schema.json")

    assert schema["title"] == "Training Row"
    assert schema["type"] == "object"


def test_training_row_schema_requires_messages():
    schema = load_schema("training_row.schema.json")
    required = set(schema["required"])

    assert required == {"messages"}


def test_training_row_message_roles_are_controlled():
    schema = load_schema("training_row.schema.json")
    role_enum = schema["properties"]["messages"]["items"]["properties"]["role"]["enum"]

    assert role_enum == ["system", "user", "assistant"]


def test_training_row_allows_metadata():
    schema = load_schema("training_row.schema.json")

    assert "metadata" in schema["properties"]
def test_cycle_manifest_schema_is_valid_json():
    schema = load_schema("cycle_manifest.schema.json")

    assert schema["title"] == "Cycle Manifest"
    assert schema["type"] == "object"


def test_cycle_manifest_schema_requires_core_lifecycle_fields():
    schema = load_schema("cycle_manifest.schema.json")
    required = set(schema["required"])

    assert "cycle_id" in required
    assert "created_at" in required
    assert "source_run_id" in required
    assert "target_capability" in required
    assert "status" in required
    assert "artifact_paths" in required


def test_cycle_manifest_status_is_controlled():
    schema = load_schema("cycle_manifest.schema.json")
    allowed = schema["properties"]["status"]["enum"]

    assert allowed == [
        "initialized",
        "running",
        "completed",
        "failed",
        "accepted",
        "rejected",
    ]


def test_cycle_manifest_artifact_paths_are_string_map():
    schema = load_schema("cycle_manifest.schema.json")
    artifact_paths = schema["properties"]["artifact_paths"]

    assert artifact_paths["type"] == "object"
    assert artifact_paths["additionalProperties"]["type"] == "string"
