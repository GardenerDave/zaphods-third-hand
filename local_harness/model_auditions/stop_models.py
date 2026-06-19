#!/usr/bin/env python3
"""Stop configured model audition tmux sessions."""

from __future__ import annotations

import argparse

if __package__ in {None, ""}:
    from common import add_common_model_args, filter_by_keys, load_models, stop_tmux_session
else:
    from .common import add_common_model_args, filter_by_keys, load_models, stop_tmux_session


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    add_common_model_args(parser)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    for model in filter_by_keys(load_models(args.models), args.only):
        if not model.managed_locally:
            print(
                f"SKIP: {model.key} is endpoint-only; no local tmux session is managed."
            )
            continue
        stop_tmux_session(model.tmux_session, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
