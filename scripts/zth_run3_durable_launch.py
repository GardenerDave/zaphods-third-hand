#!/usr/bin/env python3
"""Launch a frozen ZTH experiment in a durable tmux session."""

from __future__ import annotations

import argparse
import shlex
import subprocess
from pathlib import Path


def build_session_command(command: list[str], log_path: Path, exit_status_path: Path) -> str:
    command_text = shlex.join(command)
    log = shlex.quote(str(log_path))
    status = shlex.quote(str(exit_status_path))
    status_writer = (
        'import json, os; json.dump({"exit_code": int(os.environ["ZTH_EXIT_CODE"]), '
        '"status": "completed"}, open(os.environ["ZTH_STATUS_PATH"], "w"))'
    )
    return (
        "set -o pipefail; "
        f"{command_text} >{log} 2>&1; "
        "rc=$?; "
        f"ZTH_EXIT_CODE=$rc ZTH_STATUS_PATH={status} python3 -c {shlex.quote(status_writer)}; "
        "exit $rc"
    )


def launch(session: str, log_path: Path, exit_status_path: Path, command: list[str]) -> None:
    if not command:
        raise SystemExit("a durable command is required")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    exit_status_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["tmux", "new-session", "-d", "-s", session, build_session_command(command, log_path, exit_status_path)], check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", required=True)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--exit-status", type=Path, required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.command[:1] == ["--"]:
        args.command = args.command[1:]
    launch(args.session, args.log, args.exit_status, args.command)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
