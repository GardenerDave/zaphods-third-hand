"""Shared helpers for the local model audition harness.

The harness intentionally uses JSON configs and the Python standard library for
runtime calls so it can run on a bare Ubuntu server without fighting PEP 668.
The downloader is the only piece that needs huggingface_hub, and that should be
installed in an isolated venv.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


DEFAULT_MODEL_CONFIG = "local_harness/model_auditions/models.example.json"
DEFAULT_PROMPT_CONFIG = "local_harness/model_auditions/prompts.example.json"
DEFAULT_LLAMA_SERVER = "~/ai/src/llama.cpp/build/bin/llama-server"


class AuditionError(RuntimeError):
    """Raised when an audition command cannot be completed cleanly."""


@dataclass(frozen=True)
class ModelConfig:
    key: str
    label: str
    path: str | None = None
    port: int | None = None
    threads: int = 4
    ctx: int = 4096
    host: str = "127.0.0.1"
    base_url: str | None = None
    api_model: str = "local"
    server_host: str = "0.0.0.0"
    session: str | None = None
    expected_role: str | None = None
    repo: str | None = None
    filename_pattern: str | None = None
    extra_args: list[str] | None = None

    @property
    def tmux_session(self) -> str:
        return self.session or f"audition_{self.key}"

    @property
    def managed_locally(self) -> bool:
        return bool(self.path and self.port is not None)

    @property
    def endpoint_base_url(self) -> str:
        if self.base_url:
            return self.base_url.rstrip("/")
        if self.port is None:
            raise AuditionError(
                f"Model {self.key!r} requires port when base_url is absent."
            )
        return f"http://{self.host}:{self.port}/v1"

    @property
    def url(self) -> str:
        base_url = self.endpoint_base_url
        if base_url.endswith("/chat/completions"):
            return base_url
        return f"{base_url}/chat/completions"


@dataclass(frozen=True)
class PromptConfig:
    key: str
    label: str
    kind: str
    system: str
    user: str
    temperature: float = 0.2
    max_tokens: int = 384
    expected: dict[str, Any] | None = None


def load_json(path: str | Path) -> dict[str, Any]:
    p = Path(path).expanduser()
    if not p.exists():
        raise AuditionError(f"Config file not found: {p}")
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AuditionError(f"Invalid JSON in {p}: {exc}") from exc


def load_models(path: str | Path) -> list[ModelConfig]:
    data = load_json(path)
    raw_models = data.get("models")
    if not isinstance(raw_models, dict):
        raise AuditionError("Model config must contain an object named 'models'.")

    models: list[ModelConfig] = []
    for key, raw in raw_models.items():
        if not isinstance(raw, dict):
            raise AuditionError(f"Model entry {key!r} must be an object.")
        base_url = raw.get("base_url")
        path_value = raw.get("path")
        port_value = raw.get("port")
        host = raw.get("host", "127.0.0.1")
        server_host = raw.get("server_host", "0.0.0.0")
        api_model = raw.get("api_model", "local")
        if base_url is not None and (
            not isinstance(base_url, str) or not base_url.strip()
        ):
            raise AuditionError(
                f"Model {key!r} base_url must be a non-empty string."
            )
        if path_value is not None and (
            not isinstance(path_value, str) or not path_value.strip()
        ):
            raise AuditionError(
                f"Model {key!r} path must be a non-empty string."
            )
        if not base_url and port_value is None:
            raise AuditionError(
                f"Model {key!r} requires either base_url or port."
            )
        try:
            port = int(port_value) if port_value is not None else None
        except (TypeError, ValueError) as exc:
            raise AuditionError(f"Model {key!r} port must be an integer.") from exc
        if port is not None and not 1 <= port <= 65535:
            raise AuditionError(
                f"Model {key!r} port must be between 1 and 65535."
            )
        if not isinstance(host, str) or not host.strip():
            raise AuditionError(f"Model {key!r} host must be a non-empty string.")
        if not isinstance(server_host, str) or not server_host.strip():
            raise AuditionError(
                f"Model {key!r} server_host must be a non-empty string."
            )
        if not isinstance(api_model, str) or not api_model.strip():
            raise AuditionError(
                f"Model {key!r} api_model must be a non-empty string."
            )

        models.append(
            ModelConfig(
                key=key,
                label=raw.get("label", key),
                path=path_value,
                port=port,
                threads=int(raw.get("threads", 4)),
                ctx=int(raw.get("ctx", 4096)),
                host=host,
                base_url=base_url,
                api_model=api_model,
                server_host=server_host,
                session=raw.get("session"),
                expected_role=raw.get("expected_role"),
                repo=raw.get("repo"),
                filename_pattern=raw.get("filename_pattern"),
                extra_args=list(raw.get("extra_args", [])),
            )
        )
    return models


def load_prompts(path: str | Path) -> list[PromptConfig]:
    data = load_json(path)
    raw_prompts = data.get("prompts")
    if not isinstance(raw_prompts, dict):
        raise AuditionError("Prompt config must contain an object named 'prompts'.")

    prompts: list[PromptConfig] = []
    for key, raw in raw_prompts.items():
        if not isinstance(raw, dict):
            raise AuditionError(f"Prompt entry {key!r} must be an object.")
        try:
            prompts.append(
                PromptConfig(
                    key=key,
                    label=raw.get("label", key),
                    kind=raw.get("kind", "prose"),
                    system=raw["system"],
                    user=raw["user"],
                    temperature=float(raw.get("temperature", 0.2)),
                    max_tokens=int(raw.get("max_tokens", 384)),
                    expected=raw.get("expected", {}),
                )
            )
        except KeyError as exc:
            raise AuditionError(f"Prompt {key!r} missing required field: {exc.args[0]}") from exc
    return prompts


def filter_by_keys(items: Iterable[Any], only: str | None, attr: str = "key") -> list[Any]:
    result = list(items)
    if not only:
        return result
    requested = {x.strip() for x in only.split(",") if x.strip()}
    known = {getattr(item, attr) for item in result}
    missing = requested - known
    if missing:
        raise AuditionError(f"Unknown keys in --only: {', '.join(sorted(missing))}")
    return [item for item in result if getattr(item, attr) in requested]


def expand_path(path: str) -> str:
    return str(Path(path).expanduser())


def build_llama_command(model: ModelConfig, llama_server: str) -> list[str]:
    if not model.path or model.port is None:
        raise AuditionError(
            f"Model {model.key!r} is endpoint-only and cannot be started locally."
        )
    cmd = [
        expand_path(llama_server),
        "-m",
        expand_path(model.path),
        "--host",
        model.server_host,
        "--port",
        str(model.port),
        "-c",
        str(model.ctx),
        "-t",
        str(model.threads),
        "--parallel",
        "1",
    ]
    if model.extra_args:
        cmd.extend(model.extra_args)
    return cmd


def tmux_session_exists(session: str) -> bool:
    return subprocess.run(
        ["tmux", "has-session", "-t", session],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    ).returncode == 0


def start_tmux_session(session: str, command: list[str], dry_run: bool = False) -> None:
    shell_command = " ".join(shlex.quote(part) for part in command)
    tmux_cmd = ["tmux", "new-session", "-d", "-s", session, shell_command]
    if dry_run:
        print(" ".join(shlex.quote(part) for part in tmux_cmd))
        return
    if tmux_session_exists(session):
        print(f"SKIP: tmux session already exists: {session}")
        return
    subprocess.run(tmux_cmd, check=True)
    print(f"STARTED: {session}")


def stop_tmux_session(session: str, dry_run: bool = False) -> None:
    cmd = ["tmux", "kill-session", "-t", session]
    if dry_run:
        print(" ".join(shlex.quote(part) for part in cmd))
        return
    if not tmux_session_exists(session):
        print(f"SKIP: tmux session not running: {session}")
        return
    subprocess.run(cmd, check=True)
    print(f"STOPPED: {session}")


def utc_run_id(prefix: str = "model_audition") -> str:
    return f"{prefix}_{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}"


def ensure_dir(path: str | Path) -> Path:
    p = Path(path).expanduser()
    p.mkdir(parents=True, exist_ok=True)
    return p


def add_common_model_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--models", default=DEFAULT_MODEL_CONFIG, help="Path to model config JSON.")
    parser.add_argument("--only", default=None, help="Comma-separated model keys to include.")


def env_flag(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}
