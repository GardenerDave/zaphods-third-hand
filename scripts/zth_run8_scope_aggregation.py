"""Future-only aggregation for validation-gated Run 8-style outputs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from local_harness.sequential_cost import treatment_sequential_elapsed_ms
from scripts import zth_run7_scope_escalation as repaired


def aggregate_future_run8(output_dir: Path) -> dict[str, Any]:
    """Correct treatment sequential cost in a newly generated output.

    This utility is deliberately separate from the historical Run 8 driver.
    It must not be run against the frozen Run 8 directory.
    """

    aggregate_path = output_dir / "aggregate.json"
    aggregate = repaired._read_json(aggregate_path)
    rows = [
        repaired._read_json(path)
        for path in sorted((output_dir / "tasks" / "scope-authority-boundary").glob("*/scorecard.json"))
    ]
    comparable = [row for row in rows if row.get("disposition") == "comparable"]
    treatment_elapsed = sum(
        treatment_sequential_elapsed_ms(
            row.get("treatment_detail"),
            fallback_elapsed_ms=row.get("treatment", {}).get("elapsed_ms"),
        )
        for row in comparable
    )
    control_elapsed = sum(float(row.get("control", {}).get("elapsed_ms") or 0) for row in comparable)
    aggregate["treatment_post_baseline_elapsed_ms"] = treatment_elapsed if comparable else None
    aggregate["resource_reduced"] = treatment_elapsed < control_elapsed if comparable else None
    aggregate["economic_routing_success"] = (
        bool(
            comparable
            and aggregate.get("treatment_final_validated_solves")
            >= aggregate.get("control_validated_solves")
            and treatment_elapsed < control_elapsed
        )
        if comparable
        else None
    )
    repaired._json_write(aggregate_path, aggregate)
    return aggregate
