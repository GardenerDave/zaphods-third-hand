from __future__ import annotations

import hashlib

from scripts.zth_qwen3_5_0_8b_review_ontology_isolation import (
    NEW_SUFFIX,
    ORIGINAL_SUFFIX,
    PROMPT_DIFF,
)


def test_only_review_ontology_lines_change():
    assert hashlib.sha256(ORIGINAL_SUFFIX.encode()).hexdigest() == "3a1003f506379b1fd21eae3103cc683bf86a12f5667bdcc07a76828a58b0b9c8"
    assert hashlib.sha256(NEW_SUFFIX.encode()).hexdigest() == "bd6c3d2aa7513fc913c48ba153b7c18d840b493f76db7c30780e084e4a64dbc7"
    assert '"ready_for_review"' in NEW_SUFFIX
    assert '"ready_for_review"' not in ORIGINAL_SUFFIX
    assert '"allowed_targets": ["string"]' in NEW_SUFFIX
    assert '"held_targets": ["string"]' in NEW_SUFFIX
    assert '"scope_expansion_required": true' in NEW_SUFFIX
    assert PROMPT_DIFF.count('+') >= 4

