from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from local_harness.prompt_patch_library import (
    PromptPatchError,
    PromptPatchLibrary,
    render_prompt_deltas,
    render_validator_expectations,
    validate_patch,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness" / "prompt_patch_library.py"
PATCH_DIR = ROOT / "examples" / "prompt_patches"
EXPECTED_PATCH_IDS = [
    "absence_of_evidence_v1",
    "allowed_held_mapping_v1",
    "output_contract_v1",
    "placeholder_leakage_v1",
    "reason_required_v1",
    "required_fields_boolean_v1",
    "scope_boundary_v1",
    "single_pass_json_object_v1",
    "stop_condition_quality_v1",
    "unique_json_keys_v1",
    "unsupported_certainty_v1",
]

EXPECTED_SELECTABLE_PATCH_IDS = [
    "absence_of_evidence_v1",
    "output_contract_v1",
    "placeholder_leakage_v1",
    "reason_required_v1",
    "scope_boundary_v1",
    "stop_condition_quality_v1",
    "unsupported_certainty_v1",
]


def make_patch(**overrides):
    patch = {
        "patch_id": "scope_boundary_v1",
        "title": "Scope boundary enforcement",
        "status": "candidate",
        "failure_signature": [
            "model includes plausible but unauthorized targets",
        ],
        "applies_to": {
            "stage": ["target_selection"],
            "task_type": ["repo_patch", "triage"],
            "model_size": ["any"],
        },
        "prompt_delta": "Only include targets explicitly listed in allowed_targets.",
        "required_output_fields": ["allowed_targets", "held_targets", "reason"],
        "validator_expectations": ["no held target may appear in allowed_targets"],
    }
    patch.update(overrides)
    return patch


def test_accepts_valid_patch():
    assert validate_patch(make_patch())["patch_id"] == "scope_boundary_v1"


@pytest.mark.parametrize("missing_key", [
    "patch_id",
    "title",
    "status",
    "failure_signature",
    "applies_to",
    "prompt_delta",
    "required_output_fields",
    "validator_expectations",
])
def test_rejects_missing_required_field(missing_key):
    patch = make_patch()
    del patch[missing_key]
    with pytest.raises(PromptPatchError):
        validate_patch(patch)


def test_rejects_unknown_status():
    with pytest.raises(PromptPatchError):
        validate_patch(make_patch(status="promoted"))


def test_rejects_unknown_stage():
    patch = make_patch()
    patch["applies_to"]["stage"] = ["autonomous_execution"]
    with pytest.raises(PromptPatchError):
        validate_patch(patch)


def test_rejects_authority_fields():
    with pytest.raises(PromptPatchError):
        validate_patch(make_patch(auto_promote=True))


def test_accepts_explicit_only_selection_policy():
    patch = make_patch(selection_policy="explicit_only")
    assert validate_patch(patch)["selection_policy"] == "explicit_only"


def test_rejects_unknown_selection_policy():
    with pytest.raises(PromptPatchError):
        validate_patch(make_patch(selection_policy="auto"))


def test_rejects_duplicate_patch_id():
    library = PromptPatchLibrary()
    library.add_patch(make_patch())
    with pytest.raises(PromptPatchError):
        library.add_patch(make_patch())


def test_loads_seed_examples():
    library = PromptPatchLibrary()
    library.load_dir(PATCH_DIR)
    assert library.patch_ids == EXPECTED_PATCH_IDS


def test_filters_by_stage():
    library = PromptPatchLibrary()
    library.load_dir(PATCH_DIR)
    selected = library.filter_by_stage("target_selection")
    assert [p["patch_id"] for p in selected] == ["scope_boundary_v1"]


def test_filters_by_task_type():
    library = PromptPatchLibrary()
    library.load_dir(PATCH_DIR)
    selected = library.filter_by_task_type("docs_update")
    ids = [p["patch_id"] for p in selected]
    assert "scope_boundary_v1" in ids
    assert "placeholder_leakage_v1" in ids
    assert "allowed_held_mapping_v1" not in ids


def test_explicit_only_patches_are_not_generic_selectable():
    library = PromptPatchLibrary()
    library.load_dir(PATCH_DIR)
    selectable = library.selectable_patch_ids()
    assert "allowed_held_mapping_v1" not in selectable
    assert "required_fields_boolean_v1" not in selectable
    assert "unique_json_keys_v1" not in selectable
    assert "single_pass_json_object_v1" not in selectable


def test_filters_by_failure_signature_keyword():
    library = PromptPatchLibrary()
    library.load_dir(PATCH_DIR)
    selected = library.filter_by_failure_signature("unauthorized targets")
    assert [p["patch_id"] for p in selected] == ["scope_boundary_v1"]


def test_deprecated_patches_excluded_by_default():
    library = PromptPatchLibrary()
    library.add_patch(make_patch(status="deprecated"))
    assert library.filter_by_stage("target_selection") == []
    included = library.filter_by_stage("target_selection", include_deprecated=True)
    assert [p["patch_id"] for p in included] == ["scope_boundary_v1"]


def test_render_prompt_deltas_keeps_patch_ids():
    library = PromptPatchLibrary()
    library.load_dir(PATCH_DIR)
    selected = library.filter_by_task_type("triage")
    text = render_prompt_deltas(selected)
    for patch in selected:
        assert patch["patch_id"] in text
        assert patch["prompt_delta"].strip() in text
    assert "no execution" in text.lower()


def test_render_validator_expectations_structure():
    library = PromptPatchLibrary()
    library.load_dir(PATCH_DIR)
    selected = library.filter_by_stage("output_contract")
    records = render_validator_expectations(selected)
    assert records
    for record in records:
        assert record["patch_id"]
        assert record["validator_expectations"]
        assert record["required_output_fields"]


def test_cli_lists_seed_patch_ids():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--patch-dir", str(PATCH_DIR)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["selected_patch_ids"] == EXPECTED_SELECTABLE_PATCH_IDS


def test_selectable_patch_ids_exclude_explicit_only_patches():
    library = PromptPatchLibrary()
    library.load_dir(PATCH_DIR)
    assert library.selectable_patch_ids() == EXPECTED_SELECTABLE_PATCH_IDS


def test_cli_rejects_malformed_patch(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"patch_id": "broken"}) + "\n", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--patch-dir", str(tmp_path)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0
    assert "missing required fields" in result.stdout
