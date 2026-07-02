#!/usr/bin/env python3
"""Run a gated LARQL teacher-forced token-position diagnostic."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


_TEACHER_FORCED_SPEC = importlib.util.spec_from_file_location(
    "larql_patched_model_teacher_forced_likelihood",
    Path(__file__).with_name("larql_patched_model_teacher_forced_likelihood.py"),
)
if _TEACHER_FORCED_SPEC is None or _TEACHER_FORCED_SPEC.loader is None:
    raise RuntimeError("failed to load larql_patched_model_teacher_forced_likelihood.py")
_TEACHER_FORCED_MODULE = importlib.util.module_from_spec(_TEACHER_FORCED_SPEC)
_TEACHER_FORCED_SPEC.loader.exec_module(_TEACHER_FORCED_MODULE)

build_probe_set = _TEACHER_FORCED_MODULE.build_probe_set
build_model_prompt = _TEACHER_FORCED_MODULE.build_model_prompt
build_candidate_answers = _TEACHER_FORCED_MODULE.build_candidate_answers
validate_materialization_record = _TEACHER_FORCED_MODULE.validate_materialization_record


REPORT_TYPE = "larql_teacher_forced_token_diagnostic.v0"
REQUIRED_NEXT_STEP = "supervised_token_diagnostic_review"
EPSILON = 1e-6
SPECIAL_CHAT_MARKERS = ("<|im_start|>", "<|im_end|>", "<think>", "</think>")
STRUCTURAL_JSON_MARKERS = ("{", "}", "[", "]", ":", ",", '"', "true", "false", "null")
TARGET_PROBES = {
    "original_larql_behavior_replay",
    "adjacent_file_anti_overfit",
}
CONTROL_PROBES = {
    "all_files_authorized_control",
    "unrelated_task_regression",
}


def require_authorization(authorized: bool) -> None:
    if not authorized:
        raise ValueError("LARQL teacher-forced token diagnostic requires explicit opt-in authorization")


def load_json_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ValueError(f"{path}: required file path does not exist")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected JSON object")
    return payload


def inference_stack_available() -> bool:
    return importlib.util.find_spec("torch") is not None and importlib.util.find_spec("transformers") is not None


def validate_record_provenance(record: dict[str, Any]) -> None:
    validate_materialization_record(record)
    for field in [
        "training_performed",
        "promotion_authorized",
        "registry_mutation_authorized",
        "install_authorized",
        "automatic_failure_to_curriculum_capture_authorized",
    ]:
        if record.get(field) is not False:
            raise ValueError(f"{field} must be false")


def tokenize_candidate_text(tokenizer: Any, candidate_text: str) -> tuple[list[int], list[str]]:
    continuation_ids = tokenizer(candidate_text, return_tensors="pt", add_special_tokens=False)["input_ids"]
    if continuation_ids.shape[-1] == 0:
        raise ValueError("candidate continuation must not be empty")
    token_ids = [int(token_id) for token_id in continuation_ids[0].tolist()]
    token_texts = [
        tokenizer.decode([token_id], skip_special_tokens=False, clean_up_tokenization_spaces=False)
        for token_id in token_ids
    ]
    if len(token_ids) != len(token_texts):
        raise ValueError("tokenization/label alignment is invalid")
    return token_ids, token_texts


def categorize_token(token_text: str, *, token_id: int | None = None, special_token_ids: set[int] | None = None) -> str:
    stripped = token_text.strip()
    if token_id is not None and special_token_ids and token_id in special_token_ids:
        return "special_or_chat_template"
    if any(marker in token_text for marker in SPECIAL_CHAT_MARKERS):
        return "special_or_chat_template"
    if stripped and any(marker in stripped for marker in SPECIAL_CHAT_MARKERS):
        return "special_or_chat_template"
    if any(marker in token_text for marker in STRUCTURAL_JSON_MARKERS):
        return "structural_json"
    if not stripped or all(not ch.isalnum() for ch in stripped):
        return "whitespace_or_punctuation"
    if stripped and any(ch.isalpha() for ch in stripped):
        return "semantic_text"
    if stripped and any(ch.isdigit() for ch in stripped):
        return "numeric_or_literal"
    return "unknown"


def margin_direction_for_token(continuation_type: str, delta: float) -> bool | None:
    if abs(delta) <= EPSILON:
        return None
    if continuation_type == "corrected":
        return delta > 0.0
    if continuation_type == "failure":
        return delta < 0.0
    raise ValueError(f"unknown continuation_type: {continuation_type}")


def score_token_continuation(
    *,
    model: Any,
    tokenizer: Any,
    prompt_text: str,
    candidate_text: str,
    continuation_type: str,
) -> list[dict[str, Any]]:
    import torch

    prompt_ids = tokenizer(prompt_text, return_tensors="pt")["input_ids"]
    candidate_ids, candidate_texts = tokenize_candidate_text(tokenizer, candidate_text)
    continuation_ids = torch.tensor([candidate_ids], dtype=prompt_ids.dtype)
    full_input_ids = torch.cat([prompt_ids, continuation_ids], dim=1)
    with torch.no_grad():
        outputs = model(input_ids=full_input_ids)
    logits = outputs.logits[:, :-1, :]
    target_ids = full_input_ids[:, 1:]
    log_probs = torch.log_softmax(logits, dim=-1)
    gathered = log_probs.gather(-1, target_ids.unsqueeze(-1)).squeeze(-1)[0]
    prompt_len = int(prompt_ids.shape[-1])
    candidate_log_probs = gathered[prompt_len - 1 :]
    if int(candidate_log_probs.shape[-1]) != len(candidate_ids):
        raise ValueError("tokenization/label alignment is invalid")
    special_token_ids = set(getattr(tokenizer, "all_special_ids", []) or [])
    rows: list[dict[str, Any]] = []
    for index, (token_id, token_text, logprob) in enumerate(
        zip(candidate_ids, candidate_texts, candidate_log_probs.tolist())
    ):
        rows.append(
            {
                "continuation_type": continuation_type,
                "token_index": index,
                "token_id": token_id,
                "token_text": token_text,
                "logprob": float(logprob),
                "is_special_token": token_id in special_token_ids,
                "token_category": categorize_token(
                    token_text,
                    token_id=token_id,
                    special_token_ids=special_token_ids,
                ),
            }
        )
    return rows


def run_token_position_scoring(
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
        prompt = build_model_prompt(tokenizer, probe)
        candidates = candidate_answers[probe_id]
        rows.extend(
            {
                "probe_id": probe_id,
                "candidate_kind": "corrected",
                **row,
            }
            for row in score_token_continuation(
                model=model,
                tokenizer=tokenizer,
                prompt_text=prompt,
                candidate_text=candidates["corrected_candidate_json"],
                continuation_type="corrected",
            )
        )
        rows.extend(
            {
                "probe_id": probe_id,
                "candidate_kind": "failure",
                **row,
            }
            for row in score_token_continuation(
                model=model,
                tokenizer=tokenizer,
                prompt_text=prompt,
                candidate_text=candidates["failure_candidate_json"],
                continuation_type="failure",
            )
        )
    return rows


def run_token_position_scoring_for_model_path(
    *,
    model_path: Path,
    probe_set: list[dict[str, Any]],
    candidate_answers: dict[str, dict[str, str]],
    device: str,
) -> list[dict[str, Any]]:
    return run_token_position_scoring(
        model_path=model_path,
        probe_set=probe_set,
        candidate_answers=candidate_answers,
        device=device,
    )


def summarize_probe_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_continuation: dict[str, list[dict[str, Any]]] = {"corrected": [], "failure": []}
    for row in rows:
        by_continuation.setdefault(str(row["continuation_type"]), []).append(row)
    corrected_rows = sorted(by_continuation.get("corrected", []), key=lambda row: int(row["token_index"]))
    failure_rows = sorted(by_continuation.get("failure", []), key=lambda row: int(row["token_index"]))
    if not corrected_rows or not failure_rows:
        raise ValueError("probe is missing corrected or failure token rows")
    corrected_avg_delta = sum(float(row["patched_minus_base_logprob"]) for row in corrected_rows) / len(corrected_rows)
    failure_avg_delta = sum(float(row["patched_minus_base_logprob"]) for row in failure_rows) / len(failure_rows)
    semantic_token_delta_sum = sum(
        float(row["patched_minus_base_logprob"])
        for row in corrected_rows + failure_rows
        if row["token_category"] == "semantic_text"
    )
    special_token_delta_sum = sum(
        float(row["patched_minus_base_logprob"])
        for row in corrected_rows + failure_rows
        if row["token_category"] == "special_or_chat_template"
    )
    structural_json_token_delta_sum = sum(
        float(row["patched_minus_base_logprob"])
        for row in corrected_rows + failure_rows
        if row["token_category"] == "structural_json"
    )
    margin_delta = corrected_avg_delta - failure_avg_delta
    corrected_tokens_improved_count = sum(
        1 for row in corrected_rows if float(row["patched_minus_base_logprob"]) > EPSILON
    )
    corrected_tokens_regressed_count = sum(
        1 for row in corrected_rows if float(row["patched_minus_base_logprob"]) < -EPSILON
    )
    failure_tokens_less_likely_count = sum(
        1 for row in failure_rows if float(row["patched_minus_base_logprob"]) < -EPSILON
    )
    failure_tokens_more_likely_count = sum(
        1 for row in failure_rows if float(row["patched_minus_base_logprob"]) > EPSILON
    )
    token_deltas = [
        {
            "continuation_type": row["continuation_type"],
            "token_index": int(row["token_index"]),
            "token_id": int(row["token_id"]),
            "token_text": row["token_text"],
            "patched_minus_base_logprob": float(row["patched_minus_base_logprob"]),
        }
        for row in corrected_rows + failure_rows
    ]
    top_positive = sorted(token_deltas, key=lambda row: row["patched_minus_base_logprob"], reverse=True)[:5]
    top_negative = sorted(token_deltas, key=lambda row: row["patched_minus_base_logprob"])[:5]
    if margin_delta < -EPSILON:
        interpretation = "regressed"
    elif semantic_token_delta_sum > 0.0 and semantic_token_delta_sum >= abs(special_token_delta_sum) + abs(structural_json_token_delta_sum):
        interpretation = "semantic_improvement_detected"
    elif abs(special_token_delta_sum) + abs(structural_json_token_delta_sum) > abs(semantic_token_delta_sum):
        interpretation = "template_or_structure_dominated"
    else:
        interpretation = "mixed_or_unclear"
    return {
        "corrected_avg_delta": corrected_avg_delta,
        "failure_avg_delta": failure_avg_delta,
        "margin_delta": margin_delta,
        "corrected_tokens_improved_count": corrected_tokens_improved_count,
        "corrected_tokens_regressed_count": corrected_tokens_regressed_count,
        "failure_tokens_less_likely_count": failure_tokens_less_likely_count,
        "failure_tokens_more_likely_count": failure_tokens_more_likely_count,
        "top_positive_token_deltas": top_positive,
        "top_negative_token_deltas": top_negative,
        "semantic_token_delta_sum": semantic_token_delta_sum,
        "special_token_delta_sum": special_token_delta_sum,
        "structural_json_token_delta_sum": structural_json_token_delta_sum,
        "interpretation": interpretation,
    }


def compare_and_score(base_rows: list[dict[str, Any]], patched_rows: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    base_index = {
        (row["probe_id"], row["continuation_type"], int(row["token_index"])): row
        for row in base_rows
    }
    patched_index = {
        (row["probe_id"], row["continuation_type"], int(row["token_index"])): row
        for row in patched_rows
    }
    if set(base_index) != set(patched_index):
        raise ValueError("tokenization/label alignment is invalid")

    rows: list[dict[str, Any]] = []
    per_probe: dict[str, list[dict[str, Any]]] = {}
    for key in sorted(base_index):
        base_row = base_index[key]
        patched_row = patched_index[key]
        for field in ["token_id", "token_text", "continuation_type", "probe_id"]:
            if base_row[field] != patched_row[field]:
                raise ValueError("tokenization/label alignment is invalid")
        if int(base_row["token_index"]) != int(patched_row["token_index"]):
            raise ValueError("tokenization/label alignment is invalid")
        delta = float(patched_row["logprob"]) - float(base_row["logprob"])
        row = {
            "probe_id": base_row["probe_id"],
            "continuation_type": base_row["continuation_type"],
            "token_index": int(base_row["token_index"]),
            "token_id": int(base_row["token_id"]),
            "token_text": base_row["token_text"],
            "base_logprob": float(base_row["logprob"]),
            "patched_logprob": float(patched_row["logprob"]),
            "patched_minus_base_logprob": delta,
            "absolute_delta": abs(delta),
            "is_special_token": bool(base_row["is_special_token"] or patched_row["is_special_token"]),
            "token_category": base_row["token_category"],
            "contributes_to_margin_direction": margin_direction_for_token(base_row["continuation_type"], delta),
        }
        rows.append(row)
        per_probe.setdefault(row["probe_id"], []).append(row)

    probe_summaries: list[dict[str, Any]] = []
    for probe in build_probe_set():
        probe_id = probe["probe_id"]
        probe_rows = per_probe.get(probe_id, [])
        summary = summarize_probe_rows(probe_rows)
        probe_summaries.append({"probe_id": probe_id, **summary})

    corrected_rows = [row for row in rows if row["continuation_type"] == "corrected"]
    failure_rows = [row for row in rows if row["continuation_type"] == "failure"]
    overall = {
        "probe_count": len(probe_summaries),
        "corrected_token_count": len(corrected_rows),
        "failure_token_count": len(failure_rows),
        "semantic_token_delta_sum": sum(float(row["patched_minus_base_logprob"]) for row in rows if row["token_category"] == "semantic_text"),
        "special_token_delta_sum": sum(float(row["patched_minus_base_logprob"]) for row in rows if row["token_category"] == "special_or_chat_template"),
        "structural_json_token_delta_sum": sum(float(row["patched_minus_base_logprob"]) for row in rows if row["token_category"] == "structural_json"),
        "probes_semantic_improvement_count": sum(1 for probe in probe_summaries if probe["interpretation"] == "semantic_improvement_detected"),
        "probes_template_or_structure_dominated_count": sum(1 for probe in probe_summaries if probe["interpretation"] == "template_or_structure_dominated"),
        "probes_mixed_or_unclear_count": sum(1 for probe in probe_summaries if probe["interpretation"] == "mixed_or_unclear"),
        "probes_regressed_count": sum(1 for probe in probe_summaries if probe["interpretation"] == "regressed"),
        "largest_positive_token_deltas": sorted(
            [
                {
                    "probe_id": row["probe_id"],
                    "continuation_type": row["continuation_type"],
                    "token_index": row["token_index"],
                    "token_text": row["token_text"],
                    "patched_minus_base_logprob": row["patched_minus_base_logprob"],
                }
                for row in rows
            ],
            key=lambda row: row["patched_minus_base_logprob"],
            reverse=True,
        )[:10],
        "largest_negative_token_deltas": sorted(
            [
                {
                    "probe_id": row["probe_id"],
                    "continuation_type": row["continuation_type"],
                    "token_index": row["token_index"],
                    "token_text": row["token_text"],
                    "patched_minus_base_logprob": row["patched_minus_base_logprob"],
                }
                for row in rows
            ],
            key=lambda row: row["patched_minus_base_logprob"],
        )[:10],
    }
    return {"probe_summaries": probe_summaries, "summary": overall}, rows


def render_review_packet(record: dict[str, Any], diagnostic: dict[str, Any]) -> str:
    summary = diagnostic["summary"]
    return "\n".join(
        [
            "# LARQL Teacher-Forced Token Diagnostic Review Packet",
            "",
            "- this diagnostic compares base vs patched teacher-forced token logprobs at each continuation token position;",
            "- it does not generate text;",
            "- it does not train, patch, promote, or deploy;",
            "- the result is evidence, not authority.",
            "",
            f"- target module: `{record['target_module']}`;",
            f"- target module family: `{record['target_module_family']}`;",
            f"- delta scale: `{record['delta_scale']}`;",
            f"- corrected token count: `{summary['corrected_token_count']}`;",
            f"- failure token count: `{summary['failure_token_count']}`;",
            f"- semantic token delta sum: `{summary['semantic_token_delta_sum']}`;",
            f"- special token delta sum: `{summary['special_token_delta_sum']}`;",
            f"- structural JSON token delta sum: `{summary['structural_json_token_delta_sum']}`;",
            "",
            "Next step: `supervised_token_diagnostic_review`",
        ]
    ).rstrip() + "\n"


def write_token_diagnostic(
    *,
    run_id: str,
    out_root: Path,
    materialization_record_path: Path,
    authorize_larql_teacher_forced_token_diagnostic: bool,
    device: str,
    top_n: int,
) -> dict[str, Any]:
    require_authorization(authorize_larql_teacher_forced_token_diagnostic)
    if top_n <= 0:
        raise ValueError("top_n must be positive")
    materialization_record = load_json_object(materialization_record_path)
    validate_record_provenance(materialization_record)

    base_model_path = Path(materialization_record["base_model_path"])
    patched_model_path = Path(materialization_record["patched_model_path"])
    if not base_model_path.exists():
        raise ValueError("base model path does not exist")
    if not patched_model_path.exists():
        raise ValueError("patched model path does not exist")

    out_dir = out_root / run_id
    if out_dir.exists():
        raise ValueError("output directory already exists")
    out_dir.mkdir(parents=True, exist_ok=False)

    if not inference_stack_available():
        raise ValueError("torch and transformers are required for the token diagnostic")

    probe_set = build_probe_set()
    candidate_answers = build_candidate_answers()

    base_rows = run_token_position_scoring_for_model_path(
        model_path=base_model_path,
        probe_set=probe_set,
        candidate_answers=candidate_answers,
        device=device,
    )
    patched_rows = run_token_position_scoring_for_model_path(
        model_path=patched_model_path,
        probe_set=probe_set,
        candidate_answers=candidate_answers,
        device=device,
    )
    diagnostic, rows = compare_and_score(base_rows, patched_rows)

    comparison_path = out_dir / "token_position_diagnostic.json"
    comparison_path.write_text(json.dumps(diagnostic, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    rows_path = out_dir / "token_position_rows.jsonl"
    rows_path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )

    record = {
        "report_type": REPORT_TYPE,
        "run_id": run_id,
        "source_materialization_record_path": str(materialization_record_path),
        "base_model_path": str(base_model_path),
        "patched_model_path": str(patched_model_path),
        "target_module": str(materialization_record["target_module"]),
        "target_module_family": str(materialization_record["target_module_family"]),
        "delta_scale": float(materialization_record["delta_scale"]),
        "model_inference_performed": True,
        "base_model_inference_performed": True,
        "patched_model_inference_performed": True,
        "generation_performed": False,
        "training_performed": False,
        "weight_edit_performed": False,
        "delta_artifact_written": False,
        "patched_model_materialized": False,
        "base_model_overwritten": False,
        "promotion_authorized": False,
        "production_deployment_authorized": False,
        "registry_mutation_authorized": False,
        "install_authorized": False,
        "automatic_failure_to_curriculum_capture_authorized": False,
        "required_next_step": REQUIRED_NEXT_STEP,
        "probe_count": diagnostic["summary"]["probe_count"],
        "corrected_token_count": diagnostic["summary"]["corrected_token_count"],
        "failure_token_count": diagnostic["summary"]["failure_token_count"],
        "semantic_token_delta_sum": diagnostic["summary"]["semantic_token_delta_sum"],
        "special_token_delta_sum": diagnostic["summary"]["special_token_delta_sum"],
        "structural_json_token_delta_sum": diagnostic["summary"]["structural_json_token_delta_sum"],
        "token_diagnostic_status": (
            "semantic_improvement_detected"
            if diagnostic["summary"]["probes_semantic_improvement_count"] > 0
            else (
                "regressed"
                if diagnostic["summary"]["probes_regressed_count"] > 0
                else "mixed_or_unclear"
            )
        ),
    }
    record_path = out_dir / "larql_teacher_forced_token_diagnostic_record.json"
    record_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "token_position_diagnostic_review_packet.md").write_text(
        render_review_packet(record, diagnostic),
        encoding="utf-8",
    )
    return record


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--out-root", required=True, type=Path)
    parser.add_argument("--materialization-record", required=True, type=Path)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--top-n", type=int, default=20)
    parser.add_argument("--authorize-larql-teacher-forced-token-diagnostic", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        write_token_diagnostic(
            run_id=args.run_id,
            out_root=args.out_root,
            materialization_record_path=args.materialization_record,
            authorize_larql_teacher_forced_token_diagnostic=args.authorize_larql_teacher_forced_token_diagnostic,
            device=args.device,
            top_n=args.top_n,
        )
    except (OSError, ValueError, json.JSONDecodeError, KeyError, TypeError) as exc:
        print(f"error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
