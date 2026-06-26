import json

from local_harness.failure_training.apply_reviews import apply_review_decisions_jsonl
from local_harness.failure_training.common import read_jsonl, write_jsonl
from local_harness.failure_training.evaluate_adapter import write_evaluation_report
from local_harness.failure_training.finalize_review import finalize_reviewed_curriculum
from local_harness.failure_training.run_cycle import run_cycle
from local_harness.failure_training.train_adapter import write_adapter_plan


def test_training_eval_seam_e2e_without_launching_training(tmp_path):
    input_path = tmp_path / "raw_rows.jsonl"
    work_root = tmp_path / "work"

    write_jsonl(
        input_path,
        [
            {
                "probe_id": "json_case",
                "score_result": "fail",
                "prompt": "Return a JSON object with key ok.",
                "raw_output": "not json",
                "model_id": "tiny-model",
                "expected_contract": "Valid JSON object.",
                "corrected_output": '{"ok": true}',
            }
        ],
    )

    run_cycle(
        input_path=input_path,
        work_root=work_root,
        cycle_id="cycle_training_eval",
        source_run_id="audition_training_eval",
        target_capability="strict_json_contract",
    )

    cycle_dir = work_root / "cycles" / "cycle_training_eval"
    candidates_path = cycle_dir / "curriculum" / "candidates.jsonl"
    decisions_path = cycle_dir / "curriculum" / "review_decisions.jsonl"
    reviewed_path = cycle_dir / "curriculum" / "reviewed_candidates.jsonl"
    finalized_dir = cycle_dir / "finalized"

    candidates = read_jsonl(candidates_path)
    assert len(candidates) == 1
    candidate_id = candidates[0]["id"]

    write_jsonl(
        decisions_path,
        [
            {
                "candidate_id": candidate_id,
                "review_status": "accepted",
                "reviewer": "test-reviewer",
                "review_notes": "Gold answer checked.",
            }
        ],
    )

    apply_review_decisions_jsonl(
        candidates_path=candidates_path,
        decisions_path=decisions_path,
        output_path=reviewed_path,
    )

    finalize_manifest = finalize_reviewed_curriculum(
        reviewed_candidates_path=reviewed_path,
        output_dir=finalized_dir,
    )

    assert finalize_manifest["train_count"] == 1
    assert finalize_manifest["sft_train_count"] == 1

    sft_train = read_jsonl(finalized_dir / "datasets" / "sft" / "sft_train.jsonl")
    assert sft_train[0]["metadata"]["candidate_id"] == candidate_id

    adapter_manifest = write_adapter_plan(
        cycle_id="cycle_training_eval",
        base_model_id="tiny-model",
        dataset_dir=finalized_dir / "datasets",
        output_dir=cycle_dir / "tuning" / "adapter_plan",
        training_method="lora",
        trainer="manual",
        notes="E2E fixture plan only; no training launched.",
    )

    assert adapter_manifest["status"] == "planned"
    assert adapter_manifest["training_method"] == "lora"
    assert adapter_manifest["dataset_paths"]["sft_train"].endswith(
        "finalized/datasets/sft/sft_train.jsonl"
    )
    assert (cycle_dir / "tuning" / "adapter_plan" / "trainer_config.json").exists()

    baseline_summary = cycle_dir / "evaluation" / "baseline_summary.json"
    adapted_summary = cycle_dir / "evaluation" / "adapted_summary.json"
    baseline_summary.parent.mkdir(parents=True, exist_ok=True)

    baseline_summary.write_text(
        json.dumps({"overall_score": 0.25, "metrics": {"strict_json_contract": 0.0}}),
        encoding="utf-8",
    )
    adapted_summary.write_text(
        json.dumps({"overall_score": 1.0, "metrics": {"strict_json_contract": 1.0}}),
        encoding="utf-8",
    )

    evaluation_report = write_evaluation_report(
        baseline_summary_path=baseline_summary,
        adapted_summary_path=adapted_summary,
        output_dir=cycle_dir / "evaluation" / "adapter_eval",
        cycle_id="cycle_training_eval",
        adapter_id=adapter_manifest["adapter_id"],
        base_model_id="tiny-model",
        adapted_model_id="tiny-model+lora-fixture",
        target_capability="strict_json_contract",
        baseline_run_id="baseline_fixture",
        adapted_run_id="adapted_fixture",
        notes="Fixture comparison only; no model execution performed.",
    )

    assert evaluation_report["verdict"] == "improved"
    assert evaluation_report["metrics"]["baseline_score"] == 0.25
    assert evaluation_report["metrics"]["adapted_score"] == 1.0
    assert evaluation_report["metrics"]["delta"] == 0.75
    assert evaluation_report["metrics"]["improvements"]

    assert (cycle_dir / "evaluation" / "adapter_eval" / "evaluation_report.json").exists()
    assert (cycle_dir / "evaluation" / "adapter_eval" / "evaluation_report.md").exists()
