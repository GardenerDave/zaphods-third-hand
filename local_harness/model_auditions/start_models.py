#!/usr/bin/env python3
"""Start configured llama.cpp servers in tmux sessions."""

from __future__ import annotations

import argparse
from pathlib import Path

if __package__ in {None, ""}:
    from common import (
        AuditionError,
        DEFAULT_LLAMA_SERVER,
        add_common_model_args,
        build_llama_command,
        filter_by_keys,
        load_models,
        start_tmux_session,
    )
else:
    from .common import (
        AuditionError,
        DEFAULT_LLAMA_SERVER,
        add_common_model_args,
        build_llama_command,
        filter_by_keys,
        load_models,
        start_tmux_session,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    add_common_model_args(parser)
    parser.add_argument("--llama-server", default=DEFAULT_LLAMA_SERVER)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    llama_server = Path(args.llama_server).expanduser()
    if not args.dry_run and not llama_server.exists():
        raise AuditionError(f"llama-server not found: {llama_server}")

    models = filter_by_keys(load_models(args.models), args.only)
    for model in models:
        if not model.managed_locally:
            print(
                f"SKIP: {model.key} uses an already-running endpoint: "
                f"{model.endpoint_base_url}"
            )
            continue
        model_path = Path(model.path).expanduser()
        if not args.dry_run and not model_path.exists():
            raise AuditionError(f"Model file not found for {model.key}: {model_path}")
        command = build_llama_command(model, str(llama_server))
        start_tmux_session(model.tmux_session, command, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
