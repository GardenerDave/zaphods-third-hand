import hashlib
import json
from pathlib import Path

from scripts.zth_relation_object_ir import select_direct_target


ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "docs/research/QWEN3_1_7B_ACTION_OBJECT_RELATION_EXTRACTION_MATRIX_2026-08-22.json"
PROJECTION = ROOT / "docs/research/RELATION_OBJECT_IR_PROJECTION_2026-08-22.json"


def test_historical_pair_terminology_is_separated_without_rescoring():
    matrix = json.loads(MATRIX.read_text())
    assert matrix["metrics"]["selected_operation_correct"] == 7
    assert matrix["metrics"]["fully_correct_pairs"] == 3
    assert sum(all(row["all_relations_correct"] for row in matrix["tasks"] if row["pair_id"] == pair) for pair in {row["pair_id"] for row in matrix["tasks"]}) == 0


def test_model_free_ir_projection_reproduces_all_expected_selections():
    projection = json.loads(PROJECTION.read_text())
    assert projection["model_calls_made"] == 0
    assert projection["historical_supplier_responses_rescored"] is False
    assert projection["summary"] == {"task_count": 8, "expected_selection_reproduced": 8, "expected_selection_total": 8}
    assert all(row["correct"] for row in projection["rows"])
    for row in projection["rows"]:
        selected = select_direct_target(row["relations"], row["requested_target"])
        assert selected["selected_operation"] == row["expected_selected_operation"]


def test_reference_entity_alone_never_binds_and_fail_closed_states_work():
    relation = {"action": "inspect", "direct_object": "expiration detail", "reference_entity": "alpha.json"}
    assert select_direct_target([relation], "alpha.json")["classification"] == "NO_DIRECT_TARGET_BINDING"
    ambiguous = [
        {"action": "inspect", "direct_object": "alpha.json", "reference_entity": ""},
        {"action": "document", "direct_object": "alpha.json", "reference_entity": ""},
    ]
    assert select_direct_target(ambiguous, "alpha.json")["classification"] == "AMBIGUOUS_DIRECT_TARGET_BINDING"
    assert select_direct_target([], "alpha.json")["classification"] == "NO_DIRECT_TARGET_BINDING"


def test_historical_report_and_matrix_hashes_are_unchanged():
    expected = {
        ROOT / "docs/research/QWEN3_1_7B_ACTION_OBJECT_RELATION_EXTRACTION_2026-08-22.md": "f116bf34d647a24596076585b0c9dc799c1791507222da895e060e881f3a1196",
        ROOT / "docs/research/QWEN3_1_7B_ACTION_OBJECT_RELATION_EXTRACTION_MATRIX_2026-08-22.json": "62c150e218d47f3ee0ac5b58297198e19adc6e36166ce108e262497654014075",
    }
    for path, digest in expected.items():
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
