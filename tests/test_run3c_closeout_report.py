import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / ".work/capability_batch_reviewed_v3c/run3c_execution_2026-08-20"
REPORT = ROOT / "docs/reports/model_auditions/SUPERVISED_CAPABILITY_MINING_RUN_3C_2026-08-18.md"
FAMILIES = (
    "contradiction-handling",
    "destructive-action-restraint",
    "evidence-grounding",
    "queue-authority-boundary",
    "scope-authority-boundary",
    "unsupported-certainty",
)


def _summaries(arm):
    paths = sorted((EVIDENCE / arm).glob("*/trajectory_summary.json"))
    if not paths:
        pytest.skip("Run 3C ignored evidence is not present")
    return [json.loads(path.read_text()) for path in paths]


def _metrics(rows):
    return {
        "passes": sum(bool(row.get("capability_verdict_available") and row["pass"]) for row in rows),
        "unresolved": sum(bool(row.get("capability_verdict_available") and row["unresolved"]) for row in rows),
        "worker_calls": sum(row["model_attempt_count"] for row in rows),
        "patch_calls": sum(bool(row["patch_retry_attempted"]) for row in rows),
        "local_tasks": sum(row["teacher_pass_count"] > 0 for row in rows),
        "local_calls": sum(row["teacher_pass_count"] for row in rows),
        "external_tasks": sum(row["external_escalation_count"] > 0 for row in rows),
        "external_calls": sum(row["external_teacher_call_count"] for row in rows),
    }


def test_run3c_report_family_additive_metrics_match_durable_summaries():
    report = REPORT.read_text()
    for arm in ("control", "treatment"):
        rows = _summaries(arm)
        total = _metrics(rows)
        family = defaultdict(list)
        for row in rows:
            family[row["task_family"]].append(row)
        family_metrics = {name: _metrics(family[name]) for name in FAMILIES}

        assert sum(item["passes"] for item in family_metrics.values()) == total["passes"]
        assert sum(item["local_calls"] + item["external_calls"] for item in family_metrics.values()) == total["local_calls"] + total["external_calls"]

        expected_passes = total["passes"]
        expected_teacher_calls = total["local_calls"] + total["external_calls"]
        if arm == "control":
            assert f"| Validated passes | {expected_passes}/24" in report
            assert f"| Expensive teacher calls | {expected_teacher_calls} | 33 |" in report
        else:
            assert f"| Validated passes | 14/24 (58.3%) | {expected_passes}/24" in report
            assert f"| Expensive teacher calls | 35 | {expected_teacher_calls} |" in report

        for family_name, values in family_metrics.items():
            escaped = re.escape(family_name)
            row_match = re.search(rf"\| {escaped} \| ([^|]+) \| ([^|]+) \| (\d+) \| (\d+) \|", report)
            assert row_match, family_name
            pass_column = row_match.group(1 if arm == "control" else 2).strip()
            teacher_column = int(row_match.group(3 if arm == "control" else 4))
            assert pass_column == f"{values['passes']}/4"
            assert teacher_column == values["local_calls"] + values["external_calls"]
