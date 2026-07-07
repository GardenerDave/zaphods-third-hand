from __future__ import annotations

from local_harness.render_supervised_chain_smoke_report import render_supervised_chain_smoke_report
from local_harness.supervised_chain_smoke import run_supervised_chain_smoke


def _build_record() -> dict:
    return run_supervised_chain_smoke(
        messy_input="The LoRA stuff and prompt injection got messy. We need to tie it back together."
    )


def test_renders_all_required_sections():
    rendered = render_supervised_chain_smoke_report(_build_record())
    for heading in [
        "# Supervised Chain Smoke Report",
        "## Smoke Status",
        "## Chain IDs",
        "## Input Summary",
        "## Artifact Summary",
        "## Checks",
        "## Diagnostics",
        "## Authority Boundaries",
        "## Provenance",
        "## Review Requirement",
    ]:
        assert heading in rendered


def test_includes_smoke_id_status_and_all_chain_ids():
    record = _build_record()
    rendered = render_supervised_chain_smoke_report(record)
    assert record["smoke_id"] in rendered
    assert f"smoke_status: {record['smoke_status']}" in rendered
    for key, value in record["chain"].items():
        assert f"{key}: {value}" in rendered


def test_includes_checks_diagnostics_and_authority_boundaries():
    record = _build_record()
    rendered = render_supervised_chain_smoke_report(record)
    for check in record["checks"]:
        assert check["check_id"] in rendered
    assert "- <none>" in rendered
    for boundary in record["authority_boundaries"]:
        assert f"- {boundary}" in rendered


def test_states_smoke_is_evidence_not_authority():
    rendered = render_supervised_chain_smoke_report(_build_record())
    assert "This smoke report is evidence of deterministic chain integration." in rendered
    assert "Smoke evidence is not execution authority." in rendered


def test_does_not_include_execution_instructions():
    lowered = render_supervised_chain_smoke_report(_build_record()).lower()
    for forbidden in ["execute this command", "run this command", "bash -lc", "sudo "]:
        assert forbidden not in lowered
