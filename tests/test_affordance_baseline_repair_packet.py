import json
import subprocess
import sys
from pathlib import Path

from local_harness.affordance_baseline_repair_packet import (
    AUTHORIZED_TARGET_FILES,
    write_reports,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/affordance_baseline_repair_packet.py"


def run_packet(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def proposal_payload(**overrides):
    payload = {
        "report_type": "affordance_baseline_repair_proposal.v0",
        "candidate_id": "larql_affordance_candidate_example",
        "source_failure_id": "navigator_cuda_failure",
        "selected_lane": "baseline_prompt_context_only",
        "promotion_verdict": "hold_pending_explicit_experiment_approval",
        "proposal_status": "proposal_only",
        "proposal_verdict": "ready_for_repair_decision",
        "recommended_repair_scope": "baseline_prompt_suite_and_scorer_only",
        "runner_code_repair_needed": False,
        "candidate_repair_needed": False,
        "rerun_required_after_repair": True,
        "allowed_next_step": "decide_baseline_prompt_scorer_repair",
    }
    payload.update(overrides)
    return payload


def decision_payload(**overrides):
    payload = {
        "report_type": "affordance_baseline_repair_decision.v0",
        "candidate_id": "larql_affordance_candidate_example",
        "source_failure_id": "navigator_cuda_failure",
        "selected_lane": "baseline_prompt_context_only",
        "input_proposal_verdict": "ready_for_repair_decision",
        "input_recommended_repair_scope": "baseline_prompt_suite_and_scorer_only",
        "decision_status": "decision_only",
        "operator_decision": "accept_prompt_scorer_repair_for_packet_drafting",
        "decision_verdict": "accepted_for_repair_packet_drafting_only",
        "promotion_verdict": "hold_pending_explicit_experiment_approval",
        "operator_rationale": "Accept for packet drafting only.",
        "accepted_repair_scope": "baseline_prompt_suite_and_scorer_only",
        "allowed_next_step": "draft_baseline_prompt_scorer_repair_packet",
        "rerun_required_after_repair": True,
        "runner_code_repair_authorized": False,
        "candidate_repair_authorized": False,
    }
    payload.update(overrides)
    return payload


def v2_proposal_payload(**overrides):
    payload = proposal_payload(
        scorer_false_negative_repairs=[
            {
                "prompt_id": "baseline_no_durable_promotion",
                "repair_type": "scorer_false_negative",
                "proposal": (
                    "Accept language that says the run does not apply a LARQL patch, "
                    "does not train LoRA, and does not perform durable memory/write/promotion."
                ),
                "accepted_language_examples": [
                    "does not apply a LARQL patch",
                    "train LoRA",
                    "does not train LoRA",
                    "not train LoRA",
                    "no LoRA",
                    "LoRA training",
                    "no durable memory",
                    "no durable write",
                    "no promotion",
                ],
            }
        ],
        prompt_weakness_repairs=[
            {
                "prompt_id": "baseline_split_workflow_active_host",
                "repair_type": "structured_prompt_and_scorer_tightening",
                "proposal": (
                    "Replace the prose-only split-workflow prompt with a structured "
                    "answer form requiring exact labeled lines for local host, remote "
                    "host, active execution host, control rule, and candidate applicability."
                ),
                "required_labels": [
                    "Local host:",
                    "Remote host:",
                    "Active execution host:",
                    "Control rule:",
                    "Candidate applies only if:",
                ],
                "required_concepts": [
                    "local host",
                    "remote host",
                    "active execution host",
                    "active host profile controls which affordance applies",
                ],
                "scorer_requirement": (
                    "Require the exact structured labels plus active-host/profile control language."
                ),
            }
        ],
    )
    payload.update(overrides)
    return payload


def write_json(path: Path, payload: dict) -> Path:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def write_proposal(tmp_path: Path, **overrides) -> Path:
    return write_json(tmp_path / "baseline_repair_proposal.json", proposal_payload(**overrides))


def write_decision(tmp_path: Path, **overrides) -> Path:
    return write_json(tmp_path / "baseline_repair_decision.json", decision_payload(**overrides))


def build_ready_packet(tmp_path: Path):
    proposal = write_proposal(tmp_path)
    decision = write_decision(tmp_path)
    return write_reports(proposal, decision, tmp_path / "out")


def build_v2_packet(tmp_path: Path):
    proposal = write_json(tmp_path / "baseline_repair_proposal.json", v2_proposal_payload())
    decision = write_decision(tmp_path)
    return write_reports(proposal, decision, tmp_path / "out")


def test_help_works():
    result = run_packet("--help")

    assert result.returncode == 0
    assert "usage:" in result.stdout


def test_missing_proposal_returns_invalid_input(tmp_path):
    decision = write_decision(tmp_path)

    packet = write_reports(tmp_path / "missing.json", decision, tmp_path / "out")

    assert packet["packet_verdict"] == "invalid_input"
    assert packet["checks"]["repair_proposal_exists"] is False


def test_missing_decision_returns_invalid_input(tmp_path):
    proposal = write_proposal(tmp_path)

    packet = write_reports(proposal, tmp_path / "missing.json", tmp_path / "out")

    assert packet["packet_verdict"] == "invalid_input"
    assert packet["checks"]["repair_decision_exists"] is False


def test_invalid_proposal_json_returns_invalid_input(tmp_path):
    proposal = tmp_path / "bad_proposal.json"
    proposal.write_text("{not json\n", encoding="utf-8")
    decision = write_decision(tmp_path)

    packet = write_reports(proposal, decision, tmp_path / "out")

    assert packet["packet_verdict"] == "invalid_input"
    assert packet["checks"]["repair_proposal_parses"] is False


def test_invalid_decision_json_returns_invalid_input(tmp_path):
    proposal = write_proposal(tmp_path)
    decision = tmp_path / "bad_decision.json"
    decision.write_text("{not json\n", encoding="utf-8")

    packet = write_reports(proposal, decision, tmp_path / "out")

    assert packet["packet_verdict"] == "invalid_input"
    assert packet["checks"]["repair_decision_parses"] is False


def test_non_baseline_lane_returns_invalid_input(tmp_path):
    proposal = write_proposal(tmp_path, selected_lane="larql_affordance_patch_probe_only")
    decision = write_decision(tmp_path, selected_lane="larql_affordance_patch_probe_only")

    packet = write_reports(proposal, decision, tmp_path / "out")

    assert packet["packet_verdict"] == "invalid_input"
    assert packet["checks"]["proposal_selected_lane_baseline"] is False
    assert packet["checks"]["decision_selected_lane_baseline"] is False


def test_promotion_not_held_in_proposal_returns_invalid_input(tmp_path):
    proposal = write_proposal(tmp_path, promotion_verdict="promoted")
    decision = write_decision(tmp_path)

    packet = write_reports(proposal, decision, tmp_path / "out")

    assert packet["packet_verdict"] == "invalid_input"
    assert packet["checks"]["proposal_promotion_held"] is False


def test_promotion_not_held_in_decision_returns_invalid_input(tmp_path):
    proposal = write_proposal(tmp_path)
    decision = write_decision(tmp_path, promotion_verdict="promoted")

    packet = write_reports(proposal, decision, tmp_path / "out")

    assert packet["packet_verdict"] == "invalid_input"
    assert packet["checks"]["decision_promotion_held"] is False


def test_proposal_not_ready_returns_invalid_input(tmp_path):
    proposal = write_proposal(tmp_path, proposal_verdict="not_ready_missing_review")
    decision = write_decision(tmp_path)

    packet = write_reports(proposal, decision, tmp_path / "out")

    assert packet["packet_verdict"] == "invalid_input"
    assert packet["checks"]["proposal_verdict_ready"] is False


def test_decision_not_accepted_returns_not_ready(tmp_path):
    proposal = write_proposal(tmp_path)
    decision = write_decision(tmp_path, decision_verdict="held_for_more_review")

    packet = write_reports(proposal, decision, tmp_path / "out")

    assert packet["packet_verdict"] == "not_ready_missing_decision"
    assert packet["checks"]["decision_verdict_accepted"] is False


def test_wrong_accepted_repair_scope_returns_invalid_input(tmp_path):
    proposal = write_proposal(tmp_path)
    decision = write_decision(tmp_path, accepted_repair_scope="candidate_repair")

    packet = write_reports(proposal, decision, tmp_path / "out")

    assert packet["packet_verdict"] == "invalid_input"
    assert packet["checks"]["accepted_repair_scope_ok"] is False


def test_runner_code_repair_authorization_returns_invalid_input(tmp_path):
    proposal = write_proposal(tmp_path)
    decision = write_decision(tmp_path, runner_code_repair_authorized=True)

    packet = write_reports(proposal, decision, tmp_path / "out")

    assert packet["packet_verdict"] == "invalid_input"
    assert packet["checks"]["runner_code_repair_not_authorized"] is False


def test_candidate_repair_authorization_returns_invalid_input(tmp_path):
    proposal = write_proposal(tmp_path)
    decision = write_decision(tmp_path, candidate_repair_authorized=True)

    packet = write_reports(proposal, decision, tmp_path / "out")

    assert packet["packet_verdict"] == "invalid_input"
    assert packet["checks"]["candidate_repair_not_authorized"] is False


def test_rerun_required_after_repair_false_returns_invalid_input(tmp_path):
    proposal = write_proposal(tmp_path)
    decision = write_decision(tmp_path, rerun_required_after_repair=False)

    packet = write_reports(proposal, decision, tmp_path / "out")

    assert packet["packet_verdict"] == "invalid_input"
    assert packet["checks"]["decision_rerun_required_after_repair"] is False


def test_ready_inputs_produce_ready_packet(tmp_path):
    packet = build_ready_packet(tmp_path)

    assert packet["packet_verdict"] == "ready_for_bounded_repair_application"
    assert packet["allowed_next_step"] == "apply_baseline_prompt_scorer_repair_packet"
    assert packet["promotion_verdict"] == "hold_pending_explicit_experiment_approval"


def test_authorized_target_files_are_exactly_bounded(tmp_path):
    packet = build_ready_packet(tmp_path)

    assert packet["authorized_target_files"] == AUTHORIZED_TARGET_FILES


def test_v2_proposal_shape_produces_ready_packet(tmp_path):
    packet = build_v2_packet(tmp_path)

    assert packet["packet_verdict"] == "ready_for_bounded_repair_application"
    assert packet["promotion_verdict"] == "hold_pending_explicit_experiment_approval"


def test_v2_packet_includes_exactly_one_scorer_repair(tmp_path):
    packet = build_v2_packet(tmp_path)

    assert [repair["prompt_id"] for repair in packet["scorer_repairs"]] == [
        "baseline_no_durable_promotion"
    ]


def test_v2_no_durable_promotion_repair_includes_lora_acceptance_terms(tmp_path):
    packet = build_v2_packet(tmp_path)
    examples = set(packet["scorer_repairs"][0]["accepted_language_examples"])

    assert "train LoRA" in examples
    assert "does not train LoRA" in examples
    assert "not train LoRA" in examples
    assert "no LoRA" in examples
    assert "LoRA training" in examples


def test_v2_packet_includes_exactly_one_prompt_repair(tmp_path):
    packet = build_v2_packet(tmp_path)

    assert [repair["prompt_id"] for repair in packet["prompt_repairs"]] == [
        "baseline_split_workflow_active_host"
    ]


def test_v2_prompt_repair_preserves_structured_repair_type(tmp_path):
    packet = build_v2_packet(tmp_path)

    assert packet["prompt_repairs"][0]["repair_type"] == "structured_prompt_and_scorer_tightening"


def test_v2_prompt_repair_preserves_required_labels(tmp_path):
    packet = build_v2_packet(tmp_path)

    assert packet["prompt_repairs"][0]["required_labels"] == [
        "Local host:",
        "Remote host:",
        "Active execution host:",
        "Control rule:",
        "Candidate applies only if:",
    ]


def test_v2_authorized_repair_actions_mention_structured_split_workflow_repair(tmp_path):
    packet = build_v2_packet(tmp_path)

    descriptions = [action["description"] for action in packet["authorized_repair_actions"]]
    assert any("structured split-workflow" in description.lower() for description in descriptions)


def test_v2_runner_and_candidate_repair_authorization_remain_false(tmp_path):
    packet = build_v2_packet(tmp_path)

    assert packet["runner_code_repair_authorized"] is False
    assert packet["candidate_repair_authorized"] is False


def test_scorer_repairs_include_all_four_expected_prompts(tmp_path):
    packet = build_ready_packet(tmp_path)
    prompt_ids = {repair["prompt_id"] for repair in packet["scorer_repairs"]}

    assert prompt_ids == {
        "baseline_direct_cuda_on_navigator",
        "baseline_cross_host_boundary",
        "baseline_reverify_before_action",
        "baseline_no_durable_promotion",
    }


def test_prompt_repairs_include_split_workflow_active_host_prompt(tmp_path):
    packet = build_ready_packet(tmp_path)
    prompt_ids = {repair["prompt_id"] for repair in packet["prompt_repairs"]}

    assert "baseline_split_workflow_active_host" in prompt_ids
    assert "active execution host" in packet["prompt_repairs"][0]["authorized_change"]


def test_runner_and_candidate_repair_authorization_are_false(tmp_path):
    packet = build_ready_packet(tmp_path)

    assert packet["runner_code_repair_authorized"] is False
    assert packet["candidate_repair_authorized"] is False


def test_markdown_includes_boundary_language(tmp_path):
    proposal = write_proposal(tmp_path)
    decision = write_decision(tmp_path)
    out = tmp_path / "out"

    write_reports(proposal, decision, out)
    markdown = (out / "baseline_repair_packet.md").read_text(encoding="utf-8")

    assert "This is packet only." in markdown
    assert "No repair is applied by this packet." in markdown
    assert "The original run verdict remains preserved." in markdown
    assert "The original review verdict remains preserved." in markdown
    assert "The original proposal verdict remains preserved." in markdown
    assert "The original decision verdict remains preserved." in markdown
    assert "Only the exact target files listed above are authorized." in markdown
    assert "Only the exact repair actions listed above are authorized." in markdown
    assert "Runner execution behavior is not authorized for repair." in markdown
    assert "Candidate repair is not authorized." in markdown
    assert "This packet is not a LARQL patch." in markdown
    assert "This packet is not LoRA training." in markdown
    assert "This packet is not model mutation." in markdown
    assert "This packet is not durable memory promotion." in markdown
    assert "This packet is not comparison lane execution." in markdown
    assert "This packet grants no candidate promotion." in markdown
    assert "Rerun is required after any accepted repair." in markdown


def test_markdown_includes_structured_labels(tmp_path):
    packet = build_v2_packet(tmp_path)
    out = tmp_path / "out"

    write_reports(
        write_json(tmp_path / "baseline_repair_proposal.json", v2_proposal_payload()),
        write_decision(tmp_path),
        out,
    )
    markdown = (out / "baseline_repair_packet.md").read_text(encoding="utf-8")

    assert "structured_prompt_and_scorer_tightening" in markdown
    assert "Local host:" in markdown
    assert "Remote host:" in markdown
    assert "Active execution host:" in markdown
    assert "Control rule:" in markdown
    assert "Candidate applies only if:" in markdown
