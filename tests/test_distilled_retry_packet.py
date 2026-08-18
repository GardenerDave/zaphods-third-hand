import json

from local_harness.distilled_retry_packet import render_distilled_retry_prompt


def test_renderer_separates_contract_facts_diagnostics_and_patch() -> None:
    task = {
        "task_id": "task-1",
        "task_family": "triage-routing",
        "prompt": "Review the bounded packet.",
        "output_contract": {"format": "json", "required_fields": ["status"]},
        "validator": {"kind": "zth_output_contract", "reference_facts": {"review_status": "review_required"}},
    }
    validation = {
        "validation_status": "failed",
        "diagnostics": ["Missing required field: status"],
        "checks": [{"check_id": "required_fields", "status": "failed", "message": "Missing status"}],
    }

    packet = json.loads(render_distilled_retry_prompt(task, validation, "distilled guidance"))

    assert packet["task_context"]["prompt"] == task["prompt"]
    assert packet["declared_output_contract"] == task["output_contract"]
    assert packet["bounded_reference_facts"] == task["validator"]["reference_facts"]
    assert packet["baseline_deterministic_validation"]["failed_checks"] == [{
        "check_id": "required_fields",
        "reference_fact": None,
        "message": "Missing status",
    }]
    assert packet["experimental_distilled_patch"] == "distilled guidance"
    assert "review_required" in packet["authority"]
