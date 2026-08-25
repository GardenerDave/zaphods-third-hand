#!/usr/bin/env python3
"""Model-free construction of the Explicit-Interface V3 freeze artifacts."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs/research"
V2 = {
    "interface": DOCS / "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_INTERFACE_V2_2026-08-24.json",
    "runtime": DOCS / "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_RUNTIME_MANIFEST_V2_2026-08-24.json",
    "payload": DOCS / "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_PAYLOAD_MANIFEST_V2_2026-08-24.json",
    "evaluator": DOCS / "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_EVALUATOR_CASES_V2_2026-08-24.json",
    "freeze": DOCS / "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_FREEZE_V2_2026-08-24.json",
}
OUT = {
    "interface": DOCS / "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_INTERFACE_V3_2026-08-24.json",
    "runtime": DOCS / "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_RUNTIME_MANIFEST_V3_2026-08-24.json",
    "payload": DOCS / "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_PAYLOAD_MANIFEST_V3_2026-08-24.json",
    "evaluator": DOCS / "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_EVALUATOR_CASES_V3_2026-08-24.json",
    "projection": DOCS / "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_ACQUISITION_PROJECTION_V3_2026-08-24.json",
    "freshness": DOCS / "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_FRESHNESS_AUDIT_V3_2026-08-24.json",
    "freeze": DOCS / "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_FREEZE_V3_2026-08-24.json",
    "harness_freeze": DOCS / "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_V3_EXECUTION_HARNESS_FREEZE_2026-08-24.json",
}
LOCAL_BASE_URL = "http://192.168.1.16:8080/v1"
LOCAL_MODEL = "Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf"
EXTERNAL_WRAPPER = "/home/navigator/bin/zth-codex-teacher"
EXTERNAL_WRAPPER_SHA256 = "2c5fcaf0727bdf466e21d660c927e63d23ecb67857949b2ef21e7e599297ceab"
CODEX_VERSION = "codex-cli 0.146.0"
CODEX_HOME = "/tmp/zth_v3_codex_home"
EXTERNAL_CWD = "/tmp"
EXTERNAL_RUNTIME_ROOT = "/tmp/zth_explicit_interface_v3_external_runtime"
EXTERNAL_HOME = EXTERNAL_RUNTIME_ROOT + "/home"
EXTERNAL_TMPDIR = EXTERNAL_RUNTIME_ROOT + "/tmp"
TRANSPORT_QUALIFICATION_COMMIT = "46638a5ce8b461cd57676a1317a4a57d129c7d02"
INITIAL_V3_FREEZE_COMMIT = "c4bd2c6c386b4df9493ce8e166dc34c4b2f58bab"


def read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def v3_case_id(value: str) -> str:
    return value.replace("explicit-v2-", "explicit-v3-")


def v3_interface_id(value: str) -> str:
    return value.replace("_v2", "_v3")


def main() -> int:
    source = {key: read(path) for key, path in V2.items()}
    interface = copy.deepcopy(source["interface"])
    interface["schema"] = "zth.explicit_interface_direct_unit_calibration.interface.v3"
    interface["experiment_id"] = "explicit_interface_direct_unit_calibration_v3_2026-08-24"
    interface["status"] = "frozen_unexecuted"
    interface["transport_correction"] = "explicitly qualified local endpoint and authenticated isolated external runtime"
    for family, spec in interface["interfaces"].items():
        spec["interface_id"] = v3_interface_id(spec["interface_id"])
        spec["interface_hash"] = sha({k: v for k, v in spec.items() if k != "interface_hash"})

    interface_ids = {family: spec["interface_id"] for family, spec in interface["interfaces"].items()}
    interface_hashes = {family: spec["interface_hash"] for family, spec in interface["interfaces"].items()}

    payload = copy.deepcopy(source["payload"])
    payload.update({"schema": "zth.explicit_interface_direct_unit_calibration.payload.v3", "experiment_id": "explicit_interface_direct_unit_calibration_v3_2026-08-24", "status": "frozen_unexecuted"})
    for case in payload["cases"]:
        family = "triage-routing" if "triage" in case["case_id"] else "unsupported-certainty"
        case["case_id"] = v3_case_id(case["case_id"])
        case["interface_id"] = interface_ids[family]
        case["interface_hash"] = interface_hashes[family]
        case["experiment_metadata_payload"]["case_id"] = case["case_id"]
        case["experiment_metadata_payload"]["interface_id"] = interface_ids[family]
        case["experiment_metadata_payload"]["supplier_message_sha256"] = case["supplier_message_sha256"]
        assert hashlib.sha256(case["supplier_message_text"].encode("utf-8")).hexdigest() == case["supplier_message_sha256"]

    evaluator = copy.deepcopy(source["evaluator"])
    evaluator.update({"schema": "zth.explicit_interface_direct_unit_calibration.evaluator.v3", "experiment_id": "explicit_interface_direct_unit_calibration_v3_2026-08-24", "runtime_visibility": "scoring_only_after_raw_seal", "protocol_correction": "PROTOCOL_VALID = TRANSPORT_VALID AND PROHIBITED_ACTIONS_NOT_OBSERVED"})
    for case in evaluator["cases"]:
        family = case["family"]
        case["case_id"] = v3_case_id(case["case_id"])
        case["interface_contract"]["interface_id"] = interface_ids[family]

    runtime = copy.deepcopy(source["runtime"])
    runtime.update({"schema": "zth.explicit_interface_direct_unit_calibration.runtime.v3", "experiment_id": "explicit_interface_direct_unit_calibration_v3_2026-08-24", "status": "frozen_unexecuted", "local_base_url": LOCAL_BASE_URL, "local_model": LOCAL_MODEL, "external_wrapper": EXTERNAL_WRAPPER, "external_wrapper_sha256": EXTERNAL_WRAPPER_SHA256, "external_codex_version": CODEX_VERSION, "external_codex_home": CODEX_HOME, "external_cwd": EXTERNAL_CWD, "external_home": EXTERNAL_HOME, "external_tmpdir": EXTERNAL_TMPDIR, "transport_qualification_commit": TRANSPORT_QUALIFICATION_COMMIT, "initial_v3_freeze_commit": INITIAL_V3_FREEZE_COMMIT})
    runtime["case_order"] = [v3_case_id(case_id) for case_id in runtime["case_order"]]
    for case in runtime["cases"]:
        family = case["capability_family"]
        case["case_id"] = v3_case_id(case["case_id"])
        case["interface_id"] = interface_ids[family]
        case["interface_hash"] = interface_hashes[family]
        case["payload_manifest_case_ref"] = case["case_id"]
    runtime["interface_contract_path"] = "docs/research/EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_INTERFACE_V3_2026-08-24.json"

    payload_by_id = {case["case_id"]: case for case in payload["cases"]}
    schedule: list[dict[str, Any]] = []
    ordinal = 1
    for family in ("triage-routing", "unsupported-certainty"):
        family_cases = [case for case in payload["cases"] if ("triage" in case["case_id"]) == (family == "triage-routing")]
        for index, case in enumerate(family_cases, 1):
            first = "local_teacher" if index % 2 == 1 else "external_teacher"
            second = "external_teacher" if first == "local_teacher" else "local_teacher"
            for supplier in (first, second):
                schedule.append({"ordinal": ordinal, "case_id": case["case_id"], "capability_family": family, "interface_id": case["interface_id"], "supplier_id": supplier, "first_arm_supplier_id": first, "supplier_message_sha256": case["supplier_message_sha256"]})
                ordinal += 1

    projection_cases: list[dict[str, Any]] = []
    for case in runtime["cases"]:
        payload_case = payload_by_id[case["case_id"]]
        projection_cases.append({"case_id": case["case_id"], "capability_family": case["capability_family"], "interface_id": case["interface_id"], "interface_hash": case["interface_hash"], "authority_context": case["authority_context"], "supplier_message_text": payload_case["supplier_message_text"], "supplier_message_sha256": payload_case["supplier_message_sha256"], "supplier_arms": ["local_teacher", "external_teacher"]})
    projection = {"schema": "zth.explicit_interface_direct_unit_calibration.acquisition_projection.v3", "experiment_id": runtime["experiment_id"], "status": "frozen_unexecuted", "evaluator_information_included": False, "scoring_policy_included": False, "case_order": runtime["case_order"], "schedule": schedule, "cases": projection_cases}

    freshness = {"schema": "zth.explicit_interface_direct_unit_calibration.freshness.v3", "experiment_id": runtime["experiment_id"], "source_v2_case_set": source["freeze"]["experiment_id"], "case_count": 16, "cases": [{"case_id": case["case_id"], "source_v2_case_id": case["case_id"].replace("explicit-v3-", "explicit-v2-"), "exact_request_reuse": True, "semantic_case_preserved": True, "reason": "same preregistered semantic case; new V3 execution/interface artifact lineage; no V2 response evidence reused"} for case in runtime["cases"]], "supplier_outcomes_used": False}

    for key, value in (("interface", interface), ("payload", payload), ("evaluator", evaluator), ("runtime", runtime), ("projection", projection), ("freshness", freshness)):
        write(OUT[key], value)
    evaluator["interface_contract_artifact"] = {
        "path": "docs/research/EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_INTERFACE_V3_2026-08-24.json",
        "sha256": sha_file(OUT["interface"]),
    }
    runtime["interface_contract_sha256"] = sha_file(OUT["interface"])
    write(OUT["evaluator"], evaluator)
    write(OUT["runtime"], runtime)

    schedule_hash = hashlib.sha256(canonical(schedule)).hexdigest()
    case_hashes = {case["case_id"]: sha({"case_id": case["case_id"], "family": case["family"], "request": case["request"], "authority_context": case["authority_context"]}) for case in evaluator["cases"]}
    freeze = {
        "schema": "zth.explicit_interface_direct_unit_calibration.freeze.v3",
        "experiment_id": runtime["experiment_id"],
        "status": "frozen_unexecuted",
        "source_v2_freeze_commit": "a00d8a72e3c547ea401b8ab0075a4260c85eb82a",
        "transport_qualification_commit": TRANSPORT_QUALIFICATION_COMMIT,
        "initial_v3_freeze_commit": INITIAL_V3_FREEZE_COMMIT,
        "v2_characterization": "LOCAL_AND_EXTERNAL_CAPABILITY_NOT_MEASURED_DUE_TO_TRANSPORT_FAILURES",
        "question": "Compare the local 30B supplier and external Codex supplier on identical frozen explicit-interface tasks under matched supplier-message bytes; calibration only.",
        "case_count": 16,
        "cases_per_family": {"triage-routing": 8, "unsupported-certainty": 8},
        "case_order": runtime["case_order"],
        "case_hashes": case_hashes,
        "planned_local_calls": 16,
        "planned_external_calls": 16,
        "planned_supplier_calls": 32,
        "sample_size_frozen_before_outcomes": True,
        "outcome_conditional_sample_extension_permitted": False,
        "contradiction_reserve_present": False,
        "transport_qualification": {"commit": "46638a5ce8b461cd57676a1317a4a57d129c7d02", "local": {"qualified": True, "base_url": LOCAL_BASE_URL, "model": LOCAL_MODEL, "qualification": "TRANSPORT_OK", "models_response_sha256": "56a4a28d039d1e378d561319b17ae0da276c2806231105c6bbadd21979fb20a7"}, "external": {"qualified": True, "wrapper": EXTERNAL_WRAPPER, "wrapper_sha256": EXTERNAL_WRAPPER_SHA256, "codex_cli": CODEX_VERSION, "codex_home": CODEX_HOME, "cwd": EXTERNAL_CWD, "return_code": 0, "stdout": "TRANSPORT_OK", "stdout_sha256": "52c39f2b1f4fa8585552879bc993f277904438f439a300241bf0d895a634139a"}},
        "local_supplier": {"supplier_id": "local_teacher", "base_url": LOCAL_BASE_URL, "model": LOCAL_MODEL, "endpoint_alias": "JARVIS_LOCAL", "transport_qualified": True},
        "external_supplier": {"supplier_id": "external_teacher", "wrapper": EXTERNAL_WRAPPER, "wrapper_sha256": EXTERNAL_WRAPPER_SHA256, "codex_cli": CODEX_VERSION, "authenticated_codex_home": CODEX_HOME, "cwd": EXTERNAL_CWD, "external_home": EXTERNAL_HOME, "external_tmpdir": EXTERNAL_TMPDIR, "transport_qualified": True, "tools_mechanically_disabled": False, "tool_calls_observed": "BEST_AVAILABLE_OBSERVATION", "repository_access_observed": "BEST_AVAILABLE_OBSERVATION"},
        "matched_supplier_messages": {"bytes": True, "hashes": True, "runtime_reconstruction": False},
        "schedule": schedule,
        "schedule_sha256": schedule_hash,
        "protocol_correction": {"independent_dimension": "PROHIBITED_ACTIONS_NOT_OBSERVED", "protocol_valid_definition": "TRANSPORT_VALID AND PROHIBITED_ACTIONS_NOT_OBSERVED"},
        "transport_failure_dispositions": ["LOCAL_TRANSPORT_FAILURE", "EXTERNAL_TRANSPORT_FAILURE", "EXTERNAL_NONZERO_EXIT"],
        "firewall": {"evaluator_imported_during_acquisition": False, "evaluator_cases_loaded_during_acquisition": False, "evaluator_runtime_influence": 0, "raw_sealed_before_evaluation": True},
        "one_shot": {"prepare_before_guard": True, "guard_before_running": True, "second_execute_rejected_before_acquisition": True, "retries": 0, "replays": 0, "resume": False},
        "terminal_evidence": {"call_started_requires_terminal_evidence": True, "recording_failure_fallback": "terminal_recording_failure.json", "recording_failure_is_incomplete": True},
        "artifact_hashes": {
            "interface": sha_file(OUT["interface"]), "runtime": sha_file(OUT["runtime"]), "payload": sha_file(OUT["payload"]), "evaluator_cases": sha_file(OUT["evaluator"]), "projection": sha_file(OUT["projection"]), "freshness": sha_file(OUT["freshness"]), "evaluator_implementation": sha_file(ROOT / "scripts/evaluate_explicit_interface_direct_unit_calibration_v3.py"), "projection_implementation": sha_file(ROOT / "scripts/project_explicit_interface_direct_unit_calibration_v2_inputs.py"), "execution_harness": sha_file(ROOT / "scripts/execute_explicit_interface_direct_unit_calibration_v3.py"),
        },
        "contamination": {"v3_supplier_calls": 0, "v3_target_outcomes": 0, "model_calls": 0, "external_inference_calls": 0, "v2_mutated": False, "v2_outcomes_reused": False},
        "claim_boundary": "direct-unit calibration only; no routing-policy winner, qualification, or production-routing claim",
        "characterization": "EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_V3_FROZEN_UNEXECUTED",
        "next_decision": "EXECUTE_EXPLICIT_INTERFACE_DIRECT_UNIT_CALIBRATION_V3",
    }
    write(OUT["freeze"], freeze)

    harness_freeze = {"schema": "zth.explicit_interface_direct_unit_calibration.execution_harness_freeze.v3", "status": "frozen_unexecuted", "freeze_artifact": str(OUT["freeze"].relative_to(ROOT)), "freeze_sha256": sha_file(OUT["freeze"]), "initial_v3_freeze_commit": INITIAL_V3_FREEZE_COMMIT, "transport_qualification_commit": TRANSPORT_QUALIFICATION_COMMIT, "execution_harness_path": "scripts/execute_explicit_interface_direct_unit_calibration_v3.py", "execution_harness_sha256": sha_file(ROOT / "scripts/execute_explicit_interface_direct_unit_calibration_v3.py"), "evaluator_implementation_sha256": freeze["artifact_hashes"]["evaluator_implementation"], "projection_sha256": freeze["artifact_hashes"]["projection"], "schedule": schedule, "schedule_sha256": schedule_hash, "planned_local_calls": 16, "planned_external_calls": 16, "planned_supplier_calls": 32, "matched_runtime_message_bytes_across_arms": True, "matched_runtime_message_hash_across_arms": True, "supplier_message_runtime_reconstruction": False, "local_endpoint_binding": LOCAL_BASE_URL, "external_cwd": EXTERNAL_CWD, "external_codex_home": CODEX_HOME, "external_home": EXTERNAL_HOME, "external_tmpdir": EXTERNAL_TMPDIR, "external_runtime_root": EXTERNAL_RUNTIME_ROOT, "raw_seal_marker_ordering": "artifact coverage; raw manifest; lifecycle; marker true last; false for incomplete", "one_shot_guard_ordering": "PREPARED; guard; RUNNING", "terminal_recording_failure_fallback": "terminal_recording_failure.json", "evaluator_file_access_during_acquisition": False, "evaluator_semantics_loaded_during_acquisition": False, "evaluator_runtime_influence": 0, "retries": 0, "replays": 0, "v3_supplier_calls": 0, "v3_target_outcomes": 0}
    write(OUT["harness_freeze"], harness_freeze)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
