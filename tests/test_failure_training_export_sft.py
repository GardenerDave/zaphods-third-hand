import pytest

from local_harness.failure_training.common import read_jsonl, write_jsonl
from local_harness.failure_training.export_sft import (
    export_sft_jsonl,
    export_sft_rows,
    normalize_message,
    normalize_sft_row,
    write_sft_exports,
)


def training_row(row_id="1"):
    return {
        "messages": [
            {"role": "system", "content": "Return valid JSON."},
            {"role": "user", "content": "Fix this broken response."},
            {"role": "assistant", "content": '{"ok": true}'},
        ],
        "metadata": {
            "candidate_id": f"candidate_{row_id}",
            "failure_event_id": f"failure_{row_id}",
            "cycle_id": "cycle_0001",
        },
    }


def test_normalize_message_accepts_supported_roles():
    assert normalize_message({"role": "assistant", "content": "done"}) == {
        "role": "assistant",
        "content": "done",
    }


def test_normalize_message_rejects_unsupported_role():
    with pytest.raises(ValueError, match="unsupported message role"):
        normalize_message({"role": "tool", "content": "nope"})


def test_normalize_message_rejects_empty_content():
    with pytest.raises(ValueError, match="non-empty string"):
        normalize_message({"role": "assistant", "content": ""})


def test_normalize_sft_row_preserves_metadata_by_default():
    row = normalize_sft_row(training_row("7"))

    assert row["messages"][2]["content"] == '{"ok": true}'
    assert row["metadata"]["candidate_id"] == "candidate_7"


def test_normalize_sft_row_can_strip_metadata():
    row = normalize_sft_row(training_row("7"), include_metadata=False)

    assert row["messages"][0]["role"] == "system"
    assert "metadata" not in row


def test_normalize_sft_row_requires_at_least_two_messages():
    with pytest.raises(ValueError, match="at least two messages"):
        normalize_sft_row({"messages": [{"role": "user", "content": "only one"}]})


def test_export_sft_rows_normalizes_all_rows():
    exported = export_sft_rows([training_row("1"), training_row("2")])

    assert len(exported) == 2
    assert exported[0]["metadata"]["candidate_id"] == "candidate_1"
    assert exported[1]["metadata"]["candidate_id"] == "candidate_2"


def test_export_sft_jsonl_round_trip(tmp_path):
    input_path = tmp_path / "train.jsonl"
    output_path = tmp_path / "sft_train.jsonl"

    write_jsonl(input_path, [training_row("1")])

    exported = export_sft_jsonl(input_path, output_path)
    loaded = read_jsonl(output_path)

    assert loaded == exported
    assert loaded[0]["messages"][2]["role"] == "assistant"


def test_write_sft_exports_writes_train_validation_and_manifest(tmp_path):
    train_path = tmp_path / "train.jsonl"
    validation_path = tmp_path / "validation.jsonl"
    output_dir = tmp_path / "sft"

    write_jsonl(train_path, [training_row("train")])
    write_jsonl(validation_path, [training_row("validation")])

    manifest = write_sft_exports(
        train_path=train_path,
        validation_path=validation_path,
        output_dir=output_dir,
    )

    assert manifest["train_count"] == 1
    assert manifest["validation_count"] == 1
    assert manifest["format"] == "chat_messages_jsonl"
    assert read_jsonl(output_dir / "sft_train.jsonl")[0]["metadata"]["candidate_id"] == "candidate_train"
    assert read_jsonl(output_dir / "sft_validation.jsonl")[0]["metadata"]["candidate_id"] == "candidate_validation"
    assert read_jsonl(output_dir / "sft_manifest.jsonl") == [manifest]


def test_write_sft_exports_can_strip_metadata(tmp_path):
    train_path = tmp_path / "train.jsonl"
    validation_path = tmp_path / "validation.jsonl"
    output_dir = tmp_path / "sft"

    write_jsonl(train_path, [training_row("train")])
    write_jsonl(validation_path, [training_row("validation")])

    manifest = write_sft_exports(
        train_path=train_path,
        validation_path=validation_path,
        output_dir=output_dir,
        include_metadata=False,
    )

    assert manifest["include_metadata"] is False
    assert "metadata" not in read_jsonl(output_dir / "sft_train.jsonl")[0]
