from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from historian.capability_profile import load_capability_profiles
from historian.escalation_controller import (
    DETERMINISTIC_ESCALATION_TRIGGERS,
    build_sanitized_manifest,
    run_task_with_escalation,
    summarize_task_rows,
)
from historian.fleet_router import route_initial_model, select_fallback_model


ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "docs" / "capability_profiles_v2.json"


AVAILABLE_MODELS = [
    {
        "model_id": "Qwen_Qwen3-1.7B-Q4_K_M.gguf",
        "base_url": "http://small.example/v1",
        "priority": 0,
    },
    {
        "model_id": "Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf",
        "base_url": "http://large.example/v1",
        "priority": 1,
    },
]


def _profiles() -> dict:
    return load_capability_profiles(PROFILE)


def _task(task_id: str, task_class: str, question: str) -> dict[str, str]:
    return {"id": task_id, "task_class": task_class, "question": question}


def _evidence_factory():
    counter = {"value": 0}

    def evidence_fn(question: str, *, historian_base_url: str, request_label: str, work_dir_root):
        counter["value"] += 1
        return {
            "api_version": "v1",
            "request_id": f"hist-{counter['value']}",
            "question": question,
            "question_fingerprint": f"fp-{counter['value']}",
            "selected_record_ids": ["CLM-v2-unmeasured", "EVT-v2-acquisition"],
            "evidence": [{"id": "CLM-v2-unmeasured"}, {"id": "EVT-v2-acquisition"}],
            "retrieval_provenance_by_channel": {
                "semantic": {"selected": ["CLM-v2-unmeasured"]},
                "structured": {"selected": ["EVT-v2-acquisition"]},
            },
            "parsed_constraints": {"task_class": "historical_fact_recovery"},
        }

    return evidence_fn


def _worker_factory(primary_result: dict, fallback_result: dict):
    calls: list[dict] = []

    def worker_fn(
        question: str,
        *,
        model_id: str,
        model_base_url: str,
        historian_base_url: str,
        historian_evidence,
        request_label: str,
        work_dir_root,
    ):
        calls.append(
            {
                "request_label": request_label,
                "model_id": model_id,
                "historian_request_id": historian_evidence["request_id"],
                "historian_evidence": deepcopy(historian_evidence),
            }
        )
        if request_label.endswith(":primary"):
            return deepcopy(primary_result)
        assert "primary-answer" not in json.dumps(historian_evidence)
        assert historian_evidence["request_id"] != calls[0]["historian_request_id"]
        return deepcopy(fallback_result)

    return worker_fn, calls


def test_route_initial_model_prefers_smallest_measured_capable_model() -> None:
    route = route_initial_model("historical_fact_recovery", _profiles(), AVAILABLE_MODELS)
    assert route["selected_model"] == "Qwen_Qwen3-1.7B-Q4_K_M.gguf"
    assert route["selection_status"] == "direct"
    assert route["profile_outcome"] == "CAN_HANDLE"


def test_select_fallback_model_requires_direct_can_handle() -> None:
    profiles = _profiles()
    broken = deepcopy(profiles)
    broken["models"]["Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf"]["capabilities"]["historical_fact_recovery"]["qualification"] = "NOT_QUALIFIED"
    broken["models"]["Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf"]["capabilities"]["historical_fact_recovery"]["routing_recommendation"] = "DO_NOT_SELECT"
    fallback = select_fallback_model("historical_fact_recovery", broken, AVAILABLE_MODELS, exclude_model="Qwen_Qwen3-1.7B-Q4_K_M.gguf")
    assert fallback is None


def test_controller_escalates_for_each_deterministic_trigger() -> None:
    primary_template = {
        "consumer_request_id": "primary-req",
        "request_id": "primary-req",
        "historian_request_id": "hist-primary",
        "question_fingerprint": "fp-primary",
        "selected_record_ids": ["CLM-v2-unmeasured"],
        "answer": "primary-answer",
        "cited_record_ids": ["CLM-v2-unmeasured"],
        "evidence_used": ["CLM-v2-unmeasured"],
        "uncertainty_or_limitations": "",
        "contradictions_or_missing_evidence": [],
        "validation": {
            "schema_valid": True,
            "grounding_valid": True,
            "contract_valid": False,
            "citation_id_valid": True,
            "transport_valid": True,
            "parse_valid": True,
            "errors": ["primary failure"],
        },
        "status": "failed",
        "error_code": "WORKER_CONTRACT_FAILURE",
    }
    fallback_template = {
        "consumer_request_id": "fallback-req",
        "request_id": "fallback-req",
        "historian_request_id": "hist-fallback",
        "question_fingerprint": "fp-fallback",
        "selected_record_ids": ["CLM-v2-unmeasured"],
        "answer": "fallback-answer",
        "cited_record_ids": ["CLM-v2-unmeasured"],
        "evidence_used": ["CLM-v2-unmeasured"],
        "uncertainty_or_limitations": "",
        "contradictions_or_missing_evidence": [],
        "validation": {
            "schema_valid": True,
            "grounding_valid": True,
            "contract_valid": True,
            "citation_id_valid": True,
            "transport_valid": True,
            "parse_valid": True,
            "errors": [],
        },
        "status": "ok",
        "error_code": None,
    }

    trigger_payloads = {
        "TRANSPORT_FAILURE": ("reasoner_unavailable", {"status": "failed", "error_code": "reasoner_unavailable"}),
        "PARSE_FAILURE": ("PARSE_FAILURE", {"status": "failed", "error_code": "PARSE_FAILURE"}),
        "SCHEMA_FAILURE": ("SCHEMA_FAILURE", {"status": "ok", "validation": {"schema_valid": False, "grounding_valid": True, "contract_valid": False, "citation_id_valid": True, "transport_valid": True, "parse_valid": True, "errors": ["schema"]}, "error_code": "SCHEMA_FAILURE"}),
        "WORKER_CONTRACT_FAILURE": ("WORKER_CONTRACT_FAILURE", {"status": "ok", "validation": {"schema_valid": True, "grounding_valid": True, "contract_valid": False, "citation_id_valid": True, "transport_valid": True, "parse_valid": True, "errors": ["contract"]}, "error_code": "WORKER_CONTRACT_FAILURE"}),
        "CITATION_ID_FAILURE": ("CITATION_ID_FAILURE", {"status": "ok", "validation": {"schema_valid": True, "grounding_valid": False, "contract_valid": False, "citation_id_valid": False, "transport_valid": True, "parse_valid": True, "errors": ["citations"]}, "error_code": "CITATION_ID_FAILURE"}),
    }

    for trigger, (error_code, primary_result) in trigger_payloads.items():
        evidence_fn = _evidence_factory()
        worker_fn, calls = _worker_factory(primary_result, fallback_template)
        result = run_task_with_escalation(
            _task("T1", "historical_fact_recovery", f"{trigger} question"),
            capability_profiles=_profiles(),
            available_models=AVAILABLE_MODELS,
            historian_base_url="http://historian.example",
            worker_fn=worker_fn,
            evidence_fn=evidence_fn,
        )
        assert result["initial_routing_decision"]["selected_model"] == "Qwen_Qwen3-1.7B-Q4_K_M.gguf"
        assert result["primary_model"] == "Qwen_Qwen3-1.7B-Q4_K_M.gguf"
        assert result["fallback_model"] == "Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf"
        assert result["escalation_trigger"] == trigger
        assert result["final_worker"] == "Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf"
        assert result["attempt_count"] == 2
        assert [call["request_label"] for call in calls] == ["T1:primary", "T1:fallback"]
        assert result["primary_request"]["historian_request_id"] == "hist-1"
        assert result["fallback_request"]["historian_request_id"] == "hist-2"
        assert calls[1]["historian_request_id"] == "hist-2"
        assert calls[1]["historian_evidence"]["question"] == f"{trigger} question"
        assert calls[1]["historian_evidence"]["request_id"] == "hist-2"
        assert calls[1]["historian_evidence"] != calls[0]["historian_evidence"]
        assert primary_result["error_code"] == error_code


def test_primary_success_does_not_escalate() -> None:
    evidence_fn = _evidence_factory()
    primary_result = {
        "consumer_request_id": "primary-req",
        "request_id": "primary-req",
        "historian_request_id": "hist-primary",
        "question_fingerprint": "fp-primary",
        "selected_record_ids": ["CLM-v2-unmeasured"],
        "answer": "primary-answer",
        "cited_record_ids": ["CLM-v2-unmeasured"],
        "evidence_used": ["CLM-v2-unmeasured"],
        "uncertainty_or_limitations": "",
        "contradictions_or_missing_evidence": [],
        "validation": {
            "schema_valid": True,
            "grounding_valid": True,
            "contract_valid": True,
            "citation_id_valid": True,
            "transport_valid": True,
            "parse_valid": True,
            "errors": [],
        },
        "status": "ok",
        "error_code": None,
    }
    fallback_result = deepcopy(primary_result)
    worker_fn, calls = _worker_factory(primary_result, fallback_result)
    result = run_task_with_escalation(
        _task("T2", "historical_synthesis", "succeeds cleanly"),
        capability_profiles=_profiles(),
        available_models=AVAILABLE_MODELS,
        historian_base_url="http://historian.example",
        worker_fn=worker_fn,
        evidence_fn=evidence_fn,
    )
    assert result["escalation_trigger"] == "NONE"
    assert result["fallback_model"] is None
    assert result["attempt_count"] == 1
    assert [call["request_label"] for call in calls] == ["T2:primary"]


def test_semantic_failure_but_contract_valid_does_not_escalate() -> None:
    evidence_fn = _evidence_factory()
    primary_result = {
        "consumer_request_id": "primary-req",
        "request_id": "primary-req",
        "historian_request_id": "hist-primary",
        "question_fingerprint": "fp-primary",
        "selected_record_ids": ["CLM-v2-unmeasured"],
        "answer": "semantic miss",
        "cited_record_ids": ["CLM-v2-unmeasured"],
        "evidence_used": ["CLM-v2-unmeasured"],
        "uncertainty_or_limitations": "",
        "contradictions_or_missing_evidence": [],
        "validation": {
            "schema_valid": True,
            "grounding_valid": True,
            "contract_valid": True,
            "citation_id_valid": True,
            "transport_valid": True,
            "parse_valid": True,
            "errors": [],
        },
        "status": "ok",
        "error_code": None,
        "semantic_task_success": False,
    }
    worker_fn, calls = _worker_factory(primary_result, primary_result)
    result = run_task_with_escalation(
        _task("T3", "historical_fact_recovery", "semantic only failure"),
        capability_profiles=_profiles(),
        available_models=AVAILABLE_MODELS,
        historian_base_url="http://historian.example",
        worker_fn=worker_fn,
        evidence_fn=evidence_fn,
    )
    assert result["escalation_trigger"] == "NONE"
    assert result["fallback_model"] is None
    assert result["attempt_count"] == 1
    assert result["primary_outcome"]["semantic_task_success"] is False
    assert [call["request_label"] for call in calls] == ["T3:primary"]


def test_no_qualified_fallback_returns_explicit_bounded_status() -> None:
    evidence_fn = _evidence_factory()
    primary_result = {
        "consumer_request_id": "primary-req",
        "request_id": "primary-req",
        "historian_request_id": "hist-primary",
        "question_fingerprint": "fp-primary",
        "selected_record_ids": ["CLM-v2-unmeasured"],
        "answer": "primary-fail",
        "cited_record_ids": ["CLM-v2-unmeasured"],
        "evidence_used": ["CLM-v2-unmeasured"],
        "uncertainty_or_limitations": "",
        "contradictions_or_missing_evidence": [],
        "validation": {
            "schema_valid": True,
            "grounding_valid": True,
            "contract_valid": False,
            "citation_id_valid": True,
            "transport_valid": True,
            "parse_valid": True,
            "errors": ["contract"],
        },
        "status": "ok",
        "error_code": None,
    }
    worker_fn, calls = _worker_factory(primary_result, deepcopy(primary_result))
    single_model = [AVAILABLE_MODELS[0]]
    result = run_task_with_escalation(
        _task("T4", "historical_fact_recovery", "no fallback"),
        capability_profiles=_profiles(),
        available_models=single_model,
        historian_base_url="http://historian.example",
        worker_fn=worker_fn,
        evidence_fn=evidence_fn,
    )
    assert result["final_result_status"] == "NO_QUALIFIED_FALLBACK"
    assert result["fallback_model"] is None
    assert result["attempt_count"] == 1
    assert [call["request_label"] for call in calls] == ["T4:primary"]


def test_sanitized_manifest_hides_private_lan_addresses_and_derives_aggregate() -> None:
    manifest = build_sanitized_manifest(
        experiment_name="fleet_routing_v1",
        historian_commit="abc",
        capability_profile_sha256="def",
        fixture_sha256="ghi",
        router_commit="jkl",
        worker_contract_version="shared_memory_worker_v2",
        model_id="Qwen_Qwen3-1.7B-Q4_K_M.gguf",
        endpoint_alias="small_local_inference",
        tasks=[
            {
                "task_id": "R01",
                "routing_policy_compliance": True,
                "task_success": True,
                "primary_structural_success": True,
                "primary_semantic_success": True,
                "escalation_trigger": "NONE",
                "fallback_model": None,
                "fallback_structural_success": False,
                "fallback_semantic_success": False,
                "final_worker": "Qwen_Qwen3-1.7B-Q4_K_M.gguf",
                "final_result_status": "ok",
                "unsupported_certainty_failure": False,
                "citation_id_valid": True,
                "primary_model": "Qwen_Qwen3-1.7B-Q4_K_M.gguf",
                "latency_seconds": 1.25,
            }
        ],
    )
    assert "192.168." not in json.dumps(manifest)
    assert manifest["aggregate"]["task_success"] == 1
    assert manifest["aggregate"]["routing_policy_compliance"] == 1
