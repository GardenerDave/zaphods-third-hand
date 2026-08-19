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


def test_launcher_command_has_no_foreground_wait():
    command = build_session_command(["sh", "-c", "exit 0"], Path("run.log"), Path("exit.json"))
    assert command.startswith("set -o pipefail;")
    assert "tmux" not in command
    assert "exit $rc" in command
