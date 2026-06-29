from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/larql_rule_registry.py"
REGISTRY = ROOT / "docs/reports/affordance_larql/larql_rule_registry.json"


def run_script(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_help_works():
    result = run_script("--help")
    assert result.returncode == 0
    assert "usage:" in result.stdout.lower()


def test_registry_json_parses():
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    assert payload["registry_id"] == "larql_rule_registry.v0"
    assert len(payload["rules"]) == 3


def test_valid_registry_writes_status_markdown(tmp_path):
    out = tmp_path / "status.md"
    result = run_script("--registry", REGISTRY, "--out", out)
    assert result.returncode == 0
    text = out.read_text(encoding="utf-8")
    assert "LARQL Rule Registry Status" in text
    assert "absence_of_evidence_file_authority_v0" in text
    assert "unsupported_certainty_scope_claim_v0" in text
    assert "unsupported_file_target_authority_v0" in text
    assert "passed_after_transport_repair" in text
    assert "failed_probe_preserved" in text
    assert "Next machinery step" in text


def test_rejects_duplicate_rule_id(tmp_path):
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    payload["rules"].append(dict(payload["rules"][0]))
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result = run_script("--registry", bad, "--out", tmp_path / "status.md")
    assert result.returncode != 0


def test_rejects_missing_required_field(tmp_path):
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    del payload["rules"][0]["status"]
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result = run_script("--registry", bad, "--out", tmp_path / "status.md")
    assert result.returncode != 0


def test_rejects_missing_json_contract(tmp_path):
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    del payload["rules"][0]["json_contract"]
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result = run_script("--registry", bad, "--out", tmp_path / "status.md")
    assert result.returncode != 0


def test_rejects_missing_closeout_report_for_docs_path(tmp_path):
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    payload["rules"][0]["closeout_report"] = "docs/reports/affordance_larql/DOES_NOT_EXIST.md"
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result = run_script("--registry", bad, "--out", tmp_path / "status.md")
    assert result.returncode != 0


def test_generator_performs_no_model_call():
    result = run_script("--registry", REGISTRY, "--out", Path("/tmp") / "larql_registry_status.md")
    assert result.returncode == 0
    assert "model" not in result.stderr.lower()
