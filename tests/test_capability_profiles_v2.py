from __future__ import annotations

import json
import subprocess
from copy import deepcopy
from pathlib import Path

import pytest

from historian.capability_profile import (
    CapabilityProfileError,
    aggregate_capability_observations,
    load_capability_profiles,
    validate_capability_profile,
)
from historian.fleet_router import legacy_normalize_capability_entry


ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "docs" / "capability_profiles_v2.json"
V2_MANIFEST = ROOT / "docs" / "v2_shared_memory_qualification_manifest.json"
FLEET_MANIFEST = ROOT / "docs" / "fleet_routing_v1_manifest.json"
FOCUSED_30B_MANIFEST = ROOT / "docs" / "focused_30b_shared_memory_v1_manifest.json"


def _manifests() -> dict[str, dict]:
    return {
        "cross_model_shared_memory_v2": json.loads(V2_MANIFEST.read_text()),
        "fleet_routing_v1": json.loads(FLEET_MANIFEST.read_text()),
        "focused_30b_shared_memory_v1": json.loads(FOCUSED_30B_MANIFEST.read_text()),
    }


def test_profile_is_mechanically_derivable_from_tracked_manifests():
    profile = load_capability_profiles(PROFILE)
    manifests = _manifests()
    validated = validate_capability_profile(profile, manifests=manifests)
    assert validated["worker_contract_version"] == "shared_memory_worker_v2"
    assert validated["models"]["Qwen_Qwen3-1.7B-Q4_K_M.gguf"]["confidence"]["sample_count"] == 10
    assert validated["models"]["Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf"]["confidence"]["sample_count"] == 8

    refs = {
        "1.7_fact": [{"experiment": "cross_model_shared_memory_v2", "query_id": "A"}, {"experiment": "fleet_routing_v1", "query_id": "R01"}, {"experiment": "fleet_routing_v1", "query_id": "R02"}],
        "1.7_syn": [{"experiment": "cross_model_shared_memory_v2", "query_id": "B"}, {"experiment": "fleet_routing_v1", "query_id": "R03"}, {"experiment": "fleet_routing_v1", "query_id": "R04"}],
        "1.7_boundary": [{"experiment": "cross_model_shared_memory_v2", "query_id": "C"}, {"experiment": "fleet_routing_v1", "query_id": "R05"}, {"experiment": "fleet_routing_v1", "query_id": "R06"}],
        "1.7_exact": [{"experiment": "cross_model_shared_memory_v2", "query_id": "D"}],
        "30_fact": [{"experiment": "focused_30b_shared_memory_v1", "query_id": "Q01"}, {"experiment": "focused_30b_shared_memory_v1", "query_id": "Q02"}],
        "30_syn": [{"experiment": "focused_30b_shared_memory_v1", "query_id": "Q03"}, {"experiment": "focused_30b_shared_memory_v1", "query_id": "Q04"}],
        "30_boundary": [{"experiment": "focused_30b_shared_memory_v1", "query_id": "Q05"}, {"experiment": "focused_30b_shared_memory_v1", "query_id": "Q06"}],
        "30_exact": [{"experiment": "fleet_routing_v1", "query_id": "R07"}, {"experiment": "fleet_routing_v1", "query_id": "R08"}],
    }
    expected = {
        "1.7_fact": (3, 3, 3, 3, 3),
        "1.7_syn": (3, 2, 2, 2, 3),
        "1.7_boundary": (3, 3, 3, 3, 3),
        "1.7_exact": (1, 0, 1, 1, 0),
        "30_fact": (2, 2, 2, 2, 2),
        "30_syn": (2, 2, 2, 2, 2),
        "30_boundary": (2, 2, 2, 2, 2),
        "30_exact": (2, 0, 1, 1, 0),
    }
    for name, evidence_refs in refs.items():
        summary = aggregate_capability_observations(
            model_id="m",
            task_class=name,
            evidence_refs=evidence_refs,
            manifests=manifests,
        )
        assert (
            summary["sample_count"],
            summary["task_success_count"],
            summary["contract_success_count"],
            summary["citation_id_valid_count"],
            summary["restraint_success_count"],
        ) == expected[name]

    assert profile["models"]["Qwen_Qwen3-1.7B-Q4_K_M.gguf"]["capabilities"]["exact_causal_inference_from_incomplete_history"]["observed_outcome"] == "ESCALATION_CANDIDATE"
    assert profile["models"]["Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf"]["capabilities"]["exact_causal_inference_from_incomplete_history"]["routing_recommendation"] == "DO_NOT_SELECT"


def test_legacy_escalation_candidate_preserves_escalate_and_native_do_not_select_stays_put():
    legacy = legacy_normalize_capability_entry({"observed_outcome": "ESCALATION_CANDIDATE"})
    assert legacy == {"qualification": "NOT_QUALIFIED", "routing_recommendation": "ESCALATE"}
    native = legacy_normalize_capability_entry({"qualification": "NOT_QUALIFIED", "routing_recommendation": "DO_NOT_SELECT"})
    assert native == {"qualification": "NOT_QUALIFIED", "routing_recommendation": "DO_NOT_SELECT"}


def test_inconsistent_profile_cannot_validate():
    profile = load_capability_profiles(PROFILE)
    broken = deepcopy(profile)
    broken["models"]["Qwen_Qwen3-1.7B-Q4_K_M.gguf"]["confidence"]["sample_count"] = 9
    with pytest.raises(CapabilityProfileError):
        validate_capability_profile(broken, manifests=_manifests())


def test_tracked_profile_and_manifests_are_sanitized():
    for path in (PROFILE, V2_MANIFEST, FLEET_MANIFEST, FOCUSED_30B_MANIFEST):
        text = path.read_text()
        assert "192.168." not in text
        assert ".work/" not in text


def test_historian_cli_validate_passes():
    result = subprocess.run(
        ["python3", "-m", "historian.cli", "validate"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "valid"
    assert payload["manifest_count"] == 3
