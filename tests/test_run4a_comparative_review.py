from __future__ import annotations

import json
from pathlib import Path

from local_harness.run4a_comparative_review import (
    TIME_PRIORS_MS,
    build_comparative_freeze,
    build_objective_review,
    canonical,
    pareto_frontier,
    sha256_path,
    verify_comparative_freeze,
    verify_terminal_run4a,
)


ROOT = Path(__file__).resolve().parents[1]
RUN_ROOT = ROOT / ".work/run4a_intervention_market_calibration/run_20260819T184835Z"
REPORT = ROOT / "docs/reports/model_auditions/SUPERVISED_CAPABILITY_MINING_RUN_4A_2026-08-19.md"


def test_terminal_run4a_matrix_and_bindings_are_verified():
    verified = verify_terminal_run4a(RUN_ROOT)
    assert len(verified["selected_task_ids"]) == 16
    assert verified["aggregate"]["evidence_formation_criterion_met"] is True


def test_pareto_frontier_uses_frozen_costs_and_supported_positive_only():
    rows = {
        "deterministic_patch_retry": {"evidence_status": "supported_positive", "rescue_rate": 0.50},
        "local_teacher": {"evidence_status": "supported_positive", "rescue_rate": 0.50},
        "external_teacher": {"evidence_status": "supported_positive", "rescue_rate": 0.75},
    }
    result = pareto_frontier(rows)
    assert {row["intervention"] for row in result["frontier"]} == {"deterministic_patch_retry", "external_teacher"}
    assert [row["intervention"] for row in result["dominated"]] == ["local_teacher"]
    assert TIME_PRIORS_MS["local_teacher"] == 21497.191


def test_comparative_freeze_has_non_self_referential_digest():
    existing = verify_comparative_freeze(ROOT / "docs/research/RUN_4A_COMPARATIVE_EVIDENCE_FREEZE_2026-08-19.json")
    assert existing["blocks"]["scope-authority-boundary"]["deterministic_patch_retry"]["resolution"] == "failure_class"
    verified = verify_terminal_run4a(RUN_ROOT)
    freeze = build_comparative_freeze(
        verified,
        run_root=RUN_ROOT,
        execution_commit="15dd84cfa82d9c2cef47778111e811e11ecf7274",
        closeout_report_path=REPORT,
        harness_path=ROOT / "local_harness/run4a_intervention_harness.py",
        driver_path=ROOT / "scripts/zth_run4a_intervention_calibration.py",
    )
    basis = dict(freeze)
    digest = basis.pop("freeze_sha256")
    assert digest == __import__("hashlib").sha256(canonical({**basis, "freeze_sha256": None}).encode()).hexdigest()
    assert freeze["authority"] == "not_production_routing_authority"
    assert sha256_path(REPORT)


def test_objective_review_makes_triage_tradeoff_explicit():
    verified = verify_terminal_run4a(RUN_ROOT)
    freeze = build_comparative_freeze(
        verified,
        run_root=RUN_ROOT,
        execution_commit="15dd84cfa82d9c2cef47778111e811e11ecf7274",
        closeout_report_path=REPORT,
        harness_path=ROOT / "local_harness/run4a_intervention_harness.py",
        driver_path=ROOT / "scripts/zth_run4a_intervention_calibration.py",
    )
    review = build_objective_review(verified, freeze)
    assert review["triage_tradeoff"]["incremental_expected_cost_ms"] == 28704.012
    assert review["triage_tradeoff"]["incremental_empirical_rescue_probability"] == 0.25
    assert review["recommended_rule"]["name"] == "cheapest_supported_positive"
    assert review["comparison_design"]["preferred"] == "Option 2"
