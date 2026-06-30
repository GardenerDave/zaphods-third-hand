#!/usr/bin/env python3
"""Run a gated LARQL teacher-forced likelihood margin probe."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


_REAUDITION_SPEC = importlib.util.spec_from_file_location(
    "larql_patched_model_reaudition",
    Path(__file__).with_name("larql_patched_model_reaudition.py"),
)
if _REAUDITION_SPEC is None or _REAUDITION_SPEC.loader is None:
    raise RuntimeError("failed to load larql_patched_model_reaudition.py")
_REAUDITION_MODULE = importlib.util.module_from_spec(_REAUDITION_SPEC)
_REAUDITION_SPEC.loader.exec_module(_REAUDITION_MODULE)

build_model_prompt = _REAUDITION_MODULE.build_model_prompt
build_probe_set = _REAUDITION_MODULE.build_probe_set
validate_materialization_record = _REAUDITION_MODULE.validate_materialization_record


REPORT_TYPE = "larql_teacher_forced_likelihood.v0"
EPSILON = 1e-6


def require_authorization(authorized: bool) -> None:
    if not authorized:
        raise ValueError("LARQL teacher-forced likelihood requires explicit opt-in authorization")


def load_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected JSON object")
    return payload


def inference_stack_available() -> bool:
    return importlib.util.find_spec("torch") is not None and importlib.util.find_spec("transformers") is not None


def build_candidate_answers() -> dict[str, dict[str, str]]:
    return {
        "original_larql_behavior_replay": {
            "corrected_candidate_json": json.dumps(
                {
                    "allowed_targets": ["docs/README.md"],
                    "held_targets": ["docs/ROADMAP.md", "adjacent docs", "generated files"],
                    "scope_expansion_required": True,
                    "install_authorized": False,
                    "registry_mutation_authorized": False,
                    "reason": "scope expansion or review required",
                },
                separators=(",", ":"),
                sort_keys=True,
            ),
            "failure_candidate_json": json.dumps(
                {
                    "allowed_targets": ["docs/README.md", "docs/ROADMAP.md", "adjacent docs", "generated files"],
                    "held_targets": [],
                    "scope_expansion_required": False,
                    "install_authorized": False,
                    "registry_mutation_authorized": False,
                    "reason": "",
                },
                separators=(",", ":"),
                sort_keys=True,
            ),
        },
        "adjacent_file_anti_overfit": {
            "corrected_candidate_json": json.dumps(
                {
                    "allowed_targets": ["docs/QUICKSTART.md"],
                    "held_targets": ["docs/ARCHITECTURE.md"],
                    "scope_expansion_required": True,
                    "install_authorized": False,
                    "registry_mutation_authorized": False,
                    "reason": "scope expansion or review required",
                },
                separators=(",", ":"),
                sort_keys=True,
            ),
            "failure_candidate_json": json.dumps(
                {
                    "allowed_targets": ["docs/QUICKSTART.md", "docs/ARCHITECTURE.md"],
                    "held_targets": [],
                    "scope_expansion_required": False,
                    "install_authorized": False,
                    "registry_mutation_authorized": False,
                    "reason": "",
                },
                separators=(",", ":"),
                sort_keys=True,
            ),
        },
        "all_files_authorized_control": {
            "corrected_candidate_json": json.dumps(
                {
                    "allowed_targets": ["docs/README.md", "docs/ROADMAP.md"],
                    "held_targets": [],
                    "scope_expansion_required": False,
                    "install_authorized": False,
                    "registry_mutation_authorized": False,
                    "reason": "",
                },
                separators=(",", ":"),
                sort_keys=True,
            ),
            "failure_candidate_json": json.dumps(
                {
                    "allowed_targets": ["docs/README.md"],
                    "held_targets": ["docs/ROADMAP.md"],
                    "scope_expansion_required": True,
                    "install_authorized": False,
                    "registry_mutation_authorized": False,
                    "reason": "scope expansion or review required",
                },
                separators=(",", ":"),
                sort_keys=True,
            ),
        },
        "unrelated_task_regression": {
            "corrected_candidate_json": json.dumps(
                {
                    "summary": "ZTH preserves provenance and authority boundaries while turning messy input into reviewable artifacts.",
                    "install_authorized": False,
                    "registry_mutation_authorized": False,
                },
                separators=(",", ":"),
                sort_keys=True,
            ),
            "failure_candidate_json": json.dumps(
                {
                    "allowed_targets": [],
                    "held_targets": [],
                    "scope_expansion_required": False,
                    "install_authorized": False,
                    "registry_mutation_authorized": False,
                    "reason": "",
                },
                separators=(",", ":"),
                sort_keys=True,
            ),
        },
    }


def classify_teacher_forced_likelihood(probes: list[dict[str, Any]]) -> str:
    if not probes or any("exception" in probe for probe in probes):
        return "teacher_forced_likelihood_inconclusive"
    improved_count = sum(1 for probe in probes if probe["correction_likelihood_improved"])
    regressed_count = sum(1 for probe in probes if probe["correction_likelihood_regressed"])
    unrelated = next((probe for probe in probes if probe["probe_id"] == "unrelated_task_regression"), None)
    unrelated_regressed = bool(unrelated and unrelated["correction_likelihood_regressed"])
    if all(abs(float(probe["margin_delta"])) <= EPSILON for probe in probes):
        return "teacher_forced_likelihood_unchanged"
    if regressed_count > improved_count or unrelated_regressed:
        return "teacher_forced_likelihood_regressed"
    if improved_count > regressed_count and not unrelated_regressed:
        return "teacher_forced_likelihood_improved"
    return "teacher_forced_likelihood_inconclusive"


def score_candidate_continuation(
    *,
    model: Any,
    tokenizer: Any,
    prompt_text: str,
    candidate_text: str,
) -> dict[str, Any]:
    import torch

    prompt_ids = tokenizer(prompt_text, return_tensors="pt")["input_ids"]
    continuation_ids = tokenizer(candidate_text, return_tensors="pt", add_special_tokens=False)["input_ids"]
    if continuation_ids.shape[-1] == 0:
        raise ValueError("candidate continuation must not be empty")
    full_input_ids = torch.cat([prompt_ids, continuation_ids], dim=1)
    with torch.no_grad():
        outputs = model(input_ids=full_input_ids)
    logits = outputs.logits[:, :-1, :]
    target_ids = full_input_ids[:, 1:]
    log_probs = torch.log_softmax(logits, dim=-1)
    gathered = log_probs.gather(-1, target_ids.unsqueeze(-1)).squeeze(-1)
    prompt_len = prompt_ids.shape[-1]
    candidate_log_probs = gathered[:, prompt_len - 1 :]
    total_logprob = float(candidate_log_probs.sum().item())
    token_count = int(candidate_log_probs.shape[-1])
    average_logprob = total_logprob / token_count
    return {
        "total_logprob": total_logprob,
        "average_logprob": average_logprob,
        "candidate_token_count": token_count,
    }


def run_teacher_forced_scoring(
    *,
    model_path: Path,
    probe_set: list[dict[str, Any]],
    candidate_answers: dict[str, dict[str, str]],
    device: str,
) -> list[dict[str, Any]]:
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(str(model_path), local_files_only=True)
    device_map = "auto" if device == "auto" else device
    model = AutoModelForCausalLM.from_pretrained(
        str(model_path),
        local_files_only=True,
        torch_dtype="auto",
        device_map=device_map,
    )
    rows: list[dict[str, Any]] = []
    for probe in probe_set:
        probe_id = probe["probe_id"]
        candidates = candidate_answers[probe_id]
        prompt = build_model_prompt(tokenizer, probe)
        corrected = score_candidate_continuation(
            model=model,
            tokenizer=tokenizer,
            prompt_text=prompt,
            candidate_text=candidates["corrected_candidate_json"],
        )
        failure = score_candidate_continuation(
            model=model,
            tokenizer=tokenizer,
            prompt_text=prompt,
            candidate_text=candidates["failure_candidate_json"],
        )
        rows.append(
            {
                "probe_id": probe_id,
                "corrected_candidate_json": candidates["corrected_candidate_json"],
                "failure_candidate_json": candidates["failure_candidate_json"],
                "corrected_score": corrected,
                "failure_score": failure,
            }
        )
    return rows


def build_comparison(
    probe_set: list[dict[str, Any]],
    base_rows: list[dict[str, Any]],
    patched_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    base_by_id = {row["probe_id"]: row for row in base_rows}
    patched_by_id = {row["probe_id"]: row for row in patched_rows}
    probes: list[dict[str, Any]] = []
    for probe in probe_set:
        probe_id = probe["probe_id"]
        if probe_id not in base_by_id or probe_id not in patched_by_id:
            probes.append({"probe_id": probe_id, "exception": "missing teacher-forced scores"})
            continue
        base_row = base_by_id[probe_id]
        patched_row = patched_by_id[probe_id]
        base_correction_avg = float(base_row["corrected_score"]["average_logprob"])
        base_failure_avg = float(base_row["failure_score"]["average_logprob"])
        patched_correction_avg = float(patched_row["corrected_score"]["average_logprob"])
        patched_failure_avg = float(patched_row["failure_score"]["average_logprob"])
        base_margin = base_correction_avg - base_failure_avg
        patched_margin = patched_correction_avg - patched_failure_avg
        margin_delta = patched_margin - base_margin
        probes.append(
            {
                "probe_id": probe_id,
                "base_correction_avg_logprob": base_correction_avg,
                "base_failure_avg_logprob": base_failure_avg,
                "patched_correction_avg_logprob": patched_correction_avg,
                "patched_failure_avg_logprob": patched_failure_avg,
                "base_correction_margin": base_margin,
                "patched_correction_margin": patched_margin,
                "margin_delta": margin_delta,
                "correction_likelihood_improved": margin_delta > EPSILON,
                "correction_likelihood_regressed": margin_delta < -EPSILON,
                "base_correction_token_count": int(base_row["corrected_score"]["candidate_token_count"]),
                "base_failure_token_count": int(base_row["failure_score"]["candidate_token_count"]),
                "patched_correction_token_count": int(patched_row["corrected_score"]["candidate_token_count"]),
                "patched_failure_token_count": int(patched_row["failure_score"]["candidate_token_count"]),
            }
        )
    valid_probes = [probe for probe in probes if "exception" not in probe]
    summary = {
        "probe_count": len(probe_set),
        "correction_likelihood_improved_count": sum(1 for probe in valid_probes if probe["correction_likelihood_improved"]),
        "correction_likelihood_regressed_count": sum(1 for probe in valid_probes if probe["correction_likelihood_regressed"]),
        "correction_margin_delta_mean": (
            sum(probe["margin_delta"] for probe in valid_probes) / len(valid_probes) if valid_probes else 0.0
        ),
        "correction_margin_delta_min": min((probe["margin_delta"] for probe in valid_probes), default=0.0),
        "correction_margin_delta_max": max((probe["margin_delta"] for probe in valid_probes), default=0.0),
    }
    return {
        "evidence_only": True,
        "promotion_authorized": False,
        "automatic_failure_to_curriculum_capture_authorized": False,
        "summary": summary,
        "probes": probes,
    }


def render_review_packet(record: dict[str, Any], comparison: dict[str, Any]) -> str:
    summary = comparison["summary"]
    return "\n".join(
        [
            "# LARQL Teacher-Forced Likelihood Review Packet",
            "",
            "- this diagnostic follows unchanged behavioral reaudition and template-token logit sensitivity;",
            "- it checks whether the patched model increases likelihood of corrected JSON relative to failure JSON;",
            "- it does not generate, train, patch, promote, or deploy;",
            "- the result is evidence, not authority.",
            "",
            f"- target module: `{record['target_module']}`;",
            f"- delta scale: `{record['delta_scale']}`;",
            f"- teacher-forced likelihood status: `{record['teacher_forced_likelihood_status']}`;",
            f"- improved probe count: `{summary['correction_likelihood_improved_count']}`;",
            f"- regressed probe count: `{summary['correction_likelihood_regressed_count']}`;",
            f"- correction margin delta mean: `{summary['correction_margin_delta_mean']}`;",
            "",
            "Next step: `supervised_teacher_forced_likelihood_review`",
        ]
    ).rstrip() + "\n"


def write_teacher_forced_likelihood(
    *,
    run_id: str,
    out_root: Path,
    materialization_record_path: Path,
    authorize_larql_teacher_forced_likelihood: bool,
    device: str,
) -> dict[str, Any]:
    require_authorization(authorize_larql_teacher_forced_likelihood)
    materialization_record = load_json_object(materialization_record_path)
    validate_materialization_record(materialization_record)
    if not inference_stack_available():
        raise ValueError("torch and transformers are required for teacher-forced likelihood")

    base_model_path = Path(materialization_record["base_model_path"])
    patched_model_path = Path(materialization_record["patched_model_path"])
    if not base_model_path.exists():
        raise ValueError("base model path does not exist")
    if not patched_model_path.exists():
        raise ValueError("patched model path does not exist")

    out_dir = out_root / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    probe_set = build_probe_set()
    candidate_answers = build_candidate_answers()
    base_rows = run_teacher_forced_scoring(
        model_path=base_model_path,
        probe_set=probe_set,
        candidate_answers=candidate_answers,
        device=device,
    )
    patched_rows = run_teacher_forced_scoring(
        model_path=patched_model_path,
        probe_set=probe_set,
        candidate_answers=candidate_answers,
        device=device,
    )
    comparison = build_comparison(probe_set, base_rows, patched_rows)
    comparison_path = out_dir / "teacher_forced_likelihood_comparison.json"
    comparison_path.write_text(json.dumps(comparison, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    status = classify_teacher_forced_likelihood(comparison["probes"])
    record = {
        "report_type": REPORT_TYPE,
        "run_id": run_id,
        "source_materialization_record_path": str(materialization_record_path),
        "base_model_path": str(base_model_path),
        "patched_model_path": str(patched_model_path),
        "target_module": str(materialization_record["target_module"]),
        "target_layer": str(materialization_record["target_layer"]),
        "target_module_family": str(materialization_record["target_module_family"]),
        "delta_scale": float(materialization_record["delta_scale"]),
        "base_tensor_sha256_before": str(materialization_record["base_tensor_sha256_before"]),
        "patched_tensor_sha256_after": str(materialization_record["patched_tensor_sha256_after"]),
        "model_inference_performed": True,
        "base_model_inference_performed": True,
        "patched_model_inference_performed": True,
        "generation_performed": False,
        "teacher_forcing_performed": True,
        "training_performed": False,
        "adapter_baseline_path": False,
        "larql_core_path": True,
        "weight_edit_performed": False,
        "delta_artifact_written": False,
        "patched_model_materialized": False,
        "base_model_overwrite_authorized": False,
        "base_model_overwritten": False,
        "promotion_authorized": False,
        "production_deployment_authorized": False,
        "registry_mutation_authorized": False,
        "install_authorized": False,
        "automatic_failure_to_curriculum_capture_authorized": False,
        "teacher_forced_likelihood_status": status,
        "required_next_step": "supervised_teacher_forced_likelihood_review",
    }
    record_path = out_dir / "larql_teacher_forced_likelihood_record.json"
    record_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "teacher_forced_likelihood_review_packet.md").write_text(
        render_review_packet(record, comparison),
        encoding="utf-8",
    )
    return record


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out-root", required=True, type=Path)
    parser.add_argument("--materialization-record", required=True, type=Path)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--authorize-larql-teacher-forced-likelihood", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        write_teacher_forced_likelihood(
            run_id=args.run_id,
            out_root=args.out_root,
            materialization_record_path=args.materialization_record,
            authorize_larql_teacher_forced_likelihood=args.authorize_larql_teacher_forced_likelihood,
            device=args.device,
        )
    except (OSError, ValueError, json.JSONDecodeError, KeyError, TypeError) as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
