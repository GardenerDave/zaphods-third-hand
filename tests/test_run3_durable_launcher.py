import json
import sys
from pathlib import Path

from scripts.zth_run3_durable_launch import build_session_command, launch


def test_durable_launcher_detaches_command_and_records_exit_status(tmp_path, monkeypatch):
    calls = []

    def fake_run(argv, **kwargs):
        calls.append((argv, kwargs))

    monkeypatch.setattr("scripts.zth_run3_durable_launch.subprocess.run", fake_run)
    log = tmp_path / "run.log"
    status = tmp_path / "exit-status.json"
    launch("run3b-test", log, status, ["python3", "-c", "print('done')"])
    assert len(calls) == 1
    argv, kwargs = calls[0]
    assert argv[:5] == ["tmux", "new-session", "-d", "-s", "run3b-test"]
    assert kwargs["check"] is True
    command = argv[5]
    assert "python3 -c 'print('" in command
    assert str(log) in command
    assert str(status) in command
    assert "ZTH_EXIT_CODE=$rc" in command
    assert "ZTH_STATUS_PATH=" in command


def test_launcher_command_has_no_foreground_wait():
    command = build_session_command(["sh", "-c", "exit 0"], Path("run.log"), Path("exit.json"))
    assert command.startswith("set -o pipefail;")
    assert "tmux" not in command
    assert "exit $rc" in command


def test_status_path_is_shell_safe_for_spaces_and_quotes(tmp_path):
    status = tmp_path / "dir with spaces" / "status-'quoted'.json"
    command = build_session_command(["sh", "-c", "exit 7"], tmp_path / "run.log", status)
    status.parent.mkdir()
    subprocess = __import__("subprocess")
    completed = subprocess.run(["bash", "-c", command], check=False)
    assert completed.returncode == 7
    assert json.loads(status.read_text())["exit_code"] == 7


def test_main_strips_documented_double_dash(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr("scripts.zth_run3_durable_launch.launch", lambda *args: calls.append(args))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "zth_run3_durable_launch.py",
            "--session", "smoke",
            "--log", str(tmp_path / "run.log"),
            "--exit-status", str(tmp_path / "status.json"),
            "--", "python3", "-c", "print('ok')",
        ],
    )
    from scripts.zth_run3_durable_launch import main
    assert main() == 0
    assert calls[0][-1] == ["python3", "-c", "print('ok')"]
