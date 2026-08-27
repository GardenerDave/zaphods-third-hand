from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any, Iterable, Mapping


ROOT = Path(__file__).resolve().parents[1]
CAPABILITY_PROFILE_PATH = ROOT / "docs" / "capability_profiles_v2.json"


class CapabilityProfileError(ValueError):
    pass


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def load_capability_profiles(path: Path | None = None) -> dict[str, Any]:
    path = path or CAPABILITY_PROFILE_PATH
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise CapabilityProfileError("capability profile payload must be a JSON object")
    if payload.get("schema") != "historian_capability_profiles_v2":
        raise CapabilityProfileError("unexpected capability profile schema")
    if payload.get("worker_contract_version") != "shared_memory_worker_v2":
        raise CapabilityProfileError("unexpected worker contract version")
    if not isinstance(payload.get("models"), dict) or not payload["models"]:
        raise CapabilityProfileError("capability profile must include model entries")
    return payload


def structured_ref(experiment: str, query_id: str) -> dict[str, str]:
    return {"experiment": experiment, "query_id": query_id}


def _normalize_evidence_ref(ref: Any) -> dict[str, str]:
    if isinstance(ref, str):
        if ":" not in ref:
            raise CapabilityProfileError(f"malformed evidence reference: {ref!r}")
        experiment, query_id = ref.split(":", 1)
        return structured_ref(experiment, query_id)
    if not isinstance(ref, Mapping):
        raise CapabilityProfileError(f"evidence reference must be a mapping or compact string, got {type(ref)!r}")
    experiment = ref.get("experiment")
    query_id = ref.get("query_id")
    if not isinstance(experiment, str) or not experiment:
        raise CapabilityProfileError(f"evidence reference missing experiment: {ref!r}")
    if not isinstance(query_id, str) or not query_id:
        raise CapabilityProfileError(f"evidence reference missing query_id: {ref!r}")
    return structured_ref(experiment, query_id)


def _manifest_rows(manifest: Mapping[str, Any]) -> dict[tuple[str, str], Mapping[str, Any]]:
    rows = manifest.get("rows")
    if not isinstance(rows, list):
        raise CapabilityProfileError("manifest rows must be a list")
    index: dict[tuple[str, str], Mapping[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise CapabilityProfileError("manifest row must be an object")
        experiment = row.get("experiment")
        query_id = row.get("query_id")
        if not isinstance(experiment, str) or not isinstance(query_id, str):
            raise CapabilityProfileError(f"manifest row missing experiment/query_id: {row!r}")
        index[(experiment, query_id)] = row
    return index


def _row_value(row: Mapping[str, Any], key: str) -> int:
    value = row.get(key)
    if not isinstance(value, int):
        raise CapabilityProfileError(f"manifest row {row.get('query_id')!r} missing integer {key}")
    return value


def aggregate_capability_observations(
    *,
    model_id: str,
    task_class: str,
    evidence_refs: Iterable[Any],
    manifests: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    normalized_refs = [_normalize_evidence_ref(ref) for ref in evidence_refs]
    unique_refs = list(dict.fromkeys((ref["experiment"], ref["query_id"]) for ref in normalized_refs))
    rows: list[Mapping[str, Any]] = []
    for experiment, query_id in unique_refs:
        manifest = manifests.get(experiment)
        if manifest is None:
            raise CapabilityProfileError(f"missing manifest for experiment {experiment!r}")
        index = _manifest_rows(manifest)
        try:
            row = index[(experiment, query_id)]
        except KeyError as exc:
            raise CapabilityProfileError(f"missing evidence row {experiment!r}/{query_id!r}") from exc
        rows.append(row)

    sample_count = len(rows)
    summary = {
        "model_id": model_id,
        "task_class": task_class,
        "evidence_refs": normalized_refs,
        "sample_count": sample_count,
        "task_success_count": sum(_row_value(row, "task_success") for row in rows),
        "contract_success_count": sum(_row_value(row, "contract_success") for row in rows),
        "citation_id_valid_count": sum(_row_value(row, "citation_id_valid") for row in rows),
        "restraint_success_count": sum(_row_value(row, "restraint_success") for row in rows),
    }
    return summary


def _validate_observation_block(
    *,
    model_id: str,
    task_class: str,
    observations: Mapping[str, Any],
    evidence_refs: list[dict[str, str]],
    manifests: Mapping[str, Mapping[str, Any]] | None,
) -> None:
    sample_count = observations.get("sample_count")
    if not isinstance(sample_count, int):
        raise CapabilityProfileError(f"{model_id}/{task_class} sample_count must be int")
    if sample_count != len(evidence_refs):
        raise CapabilityProfileError(f"{model_id}/{task_class} sample_count does not match evidence refs")

    for key in ("task_success_count", "contract_success_count", "citation_id_valid_count", "restraint_success_count"):
        value = observations.get(key)
        if not isinstance(value, int):
            raise CapabilityProfileError(f"{model_id}/{task_class} {key} must be int")
        if value < 0 or value > sample_count:
            raise CapabilityProfileError(f"{model_id}/{task_class} {key} out of bounds")

    if manifests is not None:
        derived = aggregate_capability_observations(
            model_id=model_id,
            task_class=task_class,
            evidence_refs=evidence_refs,
            manifests=manifests,
        )
        for key in ("sample_count", "task_success_count", "contract_success_count", "citation_id_valid_count", "restraint_success_count"):
            if observations.get(key) != derived[key]:
                raise CapabilityProfileError(
                    f"{model_id}/{task_class} {key} mismatch: expected {derived[key]!r}, got {observations.get(key)!r}"
                )


def _validate_capability_block(
    *,
    model_id: str,
    task_class: str,
    capability: Mapping[str, Any],
    manifests: Mapping[str, Mapping[str, Any]] | None,
) -> None:
    qualification = capability.get("qualification")
    routing_recommendation = capability.get("routing_recommendation")
    if qualification not in {"CAN_HANDLE", "NOT_QUALIFIED", "UNMEASURED"}:
        raise CapabilityProfileError(f"{model_id}/{task_class} qualification invalid")
    if routing_recommendation not in {"DIRECT", "ESCALATE", "DO_NOT_SELECT", "UNMEASURED"}:
        raise CapabilityProfileError(f"{model_id}/{task_class} routing recommendation invalid")

    if qualification == "UNMEASURED":
        if capability.get("observations", {}).get("sample_count", 0) != 0:
            raise CapabilityProfileError(f"{model_id}/{task_class} unmeasured capability must have zero samples")
        return

    evidence_refs = [_normalize_evidence_ref(ref) for ref in capability.get("evidence_refs", [])]
    observations = capability.get("observations")
    if not isinstance(observations, Mapping):
        raise CapabilityProfileError(f"{model_id}/{task_class} observations must be an object")
    _validate_observation_block(
        model_id=model_id,
        task_class=task_class,
        observations=observations,
        evidence_refs=evidence_refs,
        manifests=manifests,
    )
    if qualification == "CAN_HANDLE" and routing_recommendation != "DIRECT":
        raise CapabilityProfileError(f"{model_id}/{task_class} CAN_HANDLE must route DIRECT")
    if qualification == "NOT_QUALIFIED" and routing_recommendation == "DIRECT":
        raise CapabilityProfileError(f"{model_id}/{task_class} NOT_QUALIFIED cannot route DIRECT")
    if not evidence_refs:
        raise CapabilityProfileError(f"{model_id}/{task_class} must reference evidence when measured")


def validate_capability_profile(profile: Mapping[str, Any], manifests: Mapping[str, Mapping[str, Any]] | None = None) -> dict[str, Any]:
    if not isinstance(profile, Mapping):
        raise CapabilityProfileError("profile must be a JSON object")
    if profile.get("schema") != "historian_capability_profiles_v2":
        raise CapabilityProfileError("unexpected profile schema")
    models = profile.get("models")
    if not isinstance(models, Mapping) or not models:
        raise CapabilityProfileError("profile must contain model entries")

    validated: dict[str, Any] = {"schema": profile["schema"], "worker_contract_version": profile.get("worker_contract_version"), "models": {}}
    for model_id, model in models.items():
        if not isinstance(model, Mapping):
            raise CapabilityProfileError(f"model entry {model_id!r} must be a JSON object")
        confidence = model.get("confidence")
        if not isinstance(confidence, Mapping):
            raise CapabilityProfileError(f"model entry {model_id!r} must contain confidence")
        total_direct_observations = confidence.get("total_direct_observations")
        sample_count = confidence.get("sample_count")
        if not isinstance(total_direct_observations, int) or not isinstance(sample_count, int):
            raise CapabilityProfileError(f"model entry {model_id!r} must contain integer confidence counts")
        if total_direct_observations != sample_count:
            raise CapabilityProfileError(f"model entry {model_id!r} confidence counts disagree")
        capabilities = model.get("capabilities")
        if not isinstance(capabilities, Mapping) or not capabilities:
            raise CapabilityProfileError(f"model entry {model_id!r} must contain capabilities")
        represented: set[tuple[str, str]] = set()
        normalized_model = dict(model)
        for task_class, capability in capabilities.items():
            if not isinstance(capability, Mapping):
                raise CapabilityProfileError(f"{model_id}/{task_class} capability must be a JSON object")
            _validate_capability_block(
                model_id=model_id,
                task_class=task_class,
                capability=capability,
                manifests=manifests,
            )
            for ref in capability.get("evidence_refs", []):
                normalized_ref = _normalize_evidence_ref(ref)
                represented.add((normalized_ref["experiment"], normalized_ref["query_id"]))
        if sample_count != len(represented):
            raise CapabilityProfileError(f"model entry {model_id!r} confidence sample_count must match unique evidence refs")
        validated["models"][model_id] = normalized_model
    return validated


def build_capability_profiles_from_manifests(
    manifest_map: Mapping[str, Mapping[str, Any]],
    *,
    model_specs: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    models: dict[str, Any] = {}
    for model_id, spec in model_specs.items():
        capabilities: dict[str, Any] = {}
        for task_class, refs in spec["evidence_refs"].items():
            observations = aggregate_capability_observations(
                model_id=model_id,
                task_class=task_class,
                evidence_refs=refs,
                manifests=manifest_map,
            )
            capabilities[task_class] = {
                "evidence_refs": [_normalize_evidence_ref(ref) for ref in refs],
                "observations": observations,
                "qualification": spec["qualification"][task_class],
                "routing_recommendation": spec["routing_recommendation"][task_class],
            }
        models[model_id] = {
            "model_id": model_id,
            "endpoint_alias": spec.get("endpoint_alias"),
            "model_class": spec.get("model_class"),
            "priority": spec.get("priority"),
            "qualification_source": list(spec.get("qualification_source", [])),
            "capabilities": capabilities,
            "confidence": {
                "sample_count": len({(ref["experiment"], ref["query_id"]) for task in capabilities.values() for ref in task["evidence_refs"]}),
                "total_direct_observations": len({(ref["experiment"], ref["query_id"]) for task in capabilities.values() for ref in task["evidence_refs"]}),
                "limitations": list(spec.get("limitations", [])),
            },
        }
    profile = {"schema": "historian_capability_profiles_v2", "worker_contract_version": "shared_memory_worker_v2", "models": models}
    return validate_capability_profile(profile, manifests=manifest_map)
