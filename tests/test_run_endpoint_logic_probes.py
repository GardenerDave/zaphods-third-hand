from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness" / "run_endpoint_logic_probes.sh"


def _write_stub_bins(tmp_path: Path, *, validate_exit: int = 0, score_exit: int = 0) -> Path:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    real_python = sys.executable

    (bin_dir / "date").write_text(
        "#!/usr/bin/env bash\n"
        "echo 20260712_010203\n",
        encoding="utf-8",
    )
    (bin_dir / "python3").write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"REAL_PYTHON={real_python!r}\n"
        'if [[ "${1:-}" == "-" ]]; then\n'
        '  run_dir="${RUN:?}"\n'
        '  body="$(cat)"\n'
        '  if [[ "${BASE:-}" == "http://127.0.0.1:9/v1" ]]; then\n'
        '    printf \'{"base":"%s","model":"%s","body_len":%s}\\n\' "$BASE" "$MODEL" "${#body}" > "$run_dir/inline_python_log.json"\n'
        '    exit 1\n'
        '  fi\n'
        '  mkdir -p "$run_dir/raw/$MODEL"\n'
        '  cat > "$run_dir/raw/$MODEL/probe_1.json" <<\'EOF\'\n'
        '{\n'
        '  "model_id": "'"$MODEL"'",\n'
        '  "probe_id": "probe_1",\n'
        '  "response_text": "Human review remains required.",\n'
        '  "elapsed_seconds": 1.25,\n'
        '  "usage": {"prompt_tokens": 10, "completion_tokens": 3},\n'
        '  "timings": {"predicted_per_second": 1.23}\n'
        '}\n'
        'EOF\n'
        '  printf \'{"base":"%s","model":"%s","body_len":%s}\\n\' "$BASE" "$MODEL" "${#body}" > "$run_dir/inline_python_log.json"\n'
        '  exit 0\n'
        'fi\n'
        'if [[ "${1:-}" == "local_harness/logic_probe.py" && "${2:-}" == "validate" ]]; then\n'
        f'  exit {validate_exit}\n'
        'fi\n'
        'if [[ "${1:-}" == "local_harness/logic_probe.py" && "${2:-}" == "score" ]]; then\n'
        '  run_dir="${RUN:?}"\n'
        '  mkdir -p "$run_dir"\n'
        '  cat > "$run_dir/LOGIC_PROBE_SUMMARY.md" <<\'EOF\'\n'
        '# stub summary\n'
        'EOF\n'
        f'  exit {score_exit}\n'
        'fi\n'
        'exec "$REAL_PYTHON" "$@"\n',
        encoding="utf-8",
    )
    os.chmod(bin_dir / "date", 0o755)
    os.chmod(bin_dir / "python3", 0o755)
    return bin_dir


def _run_script(tmp_path: Path, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    final_env = os.environ.copy()
    if env:
        final_env.update(env)
    return subprocess.run(
        ["/bin/bash", str(SCRIPT), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        env=final_env,
    )


def _write_prompt(tmp_path: Path) -> Path:
    prompt = tmp_path / "prompt_patch.txt"
    prompt.write_text("You are a bounded local worker.\n", encoding="utf-8")
    return prompt


def _write_fixtures(tmp_path: Path) -> Path:
    fixtures = tmp_path / "fixtures.json"
    fixtures.write_text(
        json.dumps(
            {
                "schema_version": "zth.logic_probes.v0.1",
                "probes": [
                    {
                        "id": "probe_1",
                        "category": "authority_boundary",
                        "title": "Probe",
                        "prompt": "Return a response.",
                        "scoring": {"must_include": ["human review"]},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return fixtures


def test_shell_runner_rejects_missing_prompt_patch(tmp_path: Path) -> None:
    result = _run_script(tmp_path)
    assert result.returncode != 0
    assert "Usage:" in result.stderr


def test_shell_runner_forwards_endpoint_and_writes_metadata(tmp_path: Path) -> None:
    bin_dir = _write_stub_bins(tmp_path)
    prompt = _write_prompt(tmp_path)
    fixtures = _write_fixtures(tmp_path)
    run_root = tmp_path / "runs"
    endpoint = "http://127.0.0.1:8112/v1"
    env = {
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "FIXTURES": str(fixtures),
        "RUN": str(run_root / "fixed-run"),
        "PROMPT_PATCH_CONTENT": prompt.read_text(encoding="utf-8"),
    }
    result = _run_script(
        tmp_path,
        str(prompt),
        "qwen3-coder-30b-a3b",
        endpoint,
        env=env,
    )

    assert result.returncode == 0
    raw_file = run_root / "fixed-run" / "raw" / "qwen3-coder-30b-a3b" / "probe_1.json"
    assert raw_file.is_file()
    raw = json.loads(raw_file.read_text(encoding="utf-8"))
    assert raw["elapsed_seconds"] == 1.25
    assert raw["usage"]["prompt_tokens"] == 10
    assert raw["timings"]["predicted_per_second"] == 1.23
    log = json.loads((run_root / "fixed-run" / "inline_python_log.json").read_text(encoding="utf-8"))
    assert log["base"] == endpoint
    assert log["model"] == "qwen3-coder-30b-a3b"
    assert (run_root / "fixed-run" / "LOGIC_PROBE_SUMMARY.md").is_file()


def test_shell_runner_propagates_fixture_validation_failure(tmp_path: Path) -> None:
    bin_dir = _write_stub_bins(tmp_path, validate_exit=1)
    prompt = _write_prompt(tmp_path)
    fixtures = _write_fixtures(tmp_path)
    env = {
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "FIXTURES": str(fixtures),
    }
    result = _run_script(tmp_path, str(prompt), env=env)
    assert result.returncode != 0


def test_shell_runner_nonzero_on_transport_failure(tmp_path: Path) -> None:
    bin_dir = _write_stub_bins(tmp_path)
    prompt = _write_prompt(tmp_path)
    fixtures = _write_fixtures(tmp_path)
    env = {
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "FIXTURES": str(fixtures),
        "RUN": str(tmp_path / "run"),
    }
    result = _run_script(tmp_path, str(prompt), "qwen3-coder-30b-a3b", "http://127.0.0.1:9/v1", env=env)
    assert result.returncode != 0
