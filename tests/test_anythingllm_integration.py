from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = {
    "historian_evidence": ROOT / "integrations" / "anythingllm" / "skills" / "historian_evidence",
    "historian_query": ROOT / "integrations" / "anythingllm" / "skills" / "historian_query",
}


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_anythingllm_skill_manifests_are_project_controlled():
    for skill_name, skill_dir in SKILLS.items():
        manifest = _load_json(skill_dir / "plugin.json")
        handler = (skill_dir / "handler.js").read_text(encoding="utf-8")

        assert manifest["active"] is True
        assert manifest["hubId"] == skill_name
        assert manifest["entrypoint"]["file"] == "handler.js"
        assert "question" in manifest["entrypoint"]["params"]

        assert "http://127.0.0.1:8765/v1" in handler
        assert "expected_record_ids" not in handler
        assert "required_citation_ids" not in handler
        assert "answer_mode" not in handler
        assert "forbidden_misconception" not in handler


def test_anythingllm_sync_script_is_present():
    script = ROOT / "scripts" / "sync_anythingllm_skills.sh"
    assert script.exists()
    assert script.read_text(encoding="utf-8").startswith("#!/usr/bin/env bash")
