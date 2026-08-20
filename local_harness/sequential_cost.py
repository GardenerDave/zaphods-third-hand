"""Model-free accounting helpers for validation-gated sequential policies."""

from __future__ import annotations

from typing import Any, Mapping


def treatment_sequential_elapsed_ms(
    treatment_detail: Mapping[str, Any] | None,
    *,
    fallback_elapsed_ms: float | int | None = None,
) -> float:
    """Return the realized treatment policy elapsed time.

    A local-pass treatment pays for its local-first stage once.  An escalated
    treatment pays for both the local-first stage and the external escalation.
    The scorecard's ``final`` stage alone is insufficient for the latter.
    """

    if treatment_detail is None:
        return float(fallback_elapsed_ms or 0)
    local_first = treatment_detail.get("local_first") or {}
    local_elapsed = float(local_first.get("realized_elapsed_ms") or 0)
    if not treatment_detail.get("escalated"):
        return local_elapsed
    escalation = treatment_detail.get("escalation")
    if not isinstance(escalation, Mapping):
        raise ValueError("escalated treatment is missing terminal escalation details")
    return local_elapsed + float(escalation.get("realized_elapsed_ms") or 0)
