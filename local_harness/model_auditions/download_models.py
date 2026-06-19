#!/usr/bin/env python3
"""Download GGUF files declared in the model audition config.

This command intentionally uses huggingface_hub only here. On Ubuntu/Debian
systems with PEP 668, install it in a venv, for example:

    python3 -m venv ~/ai/tools/hf-venv
    ~/ai/tools/hf-venv/bin/python -m pip install -U "huggingface_hub[cli]" hf_xet
    ~/ai/tools/hf-venv/bin/python local_harness/model_auditions/download_models.py
"""

from __future__ import annotations

import argparse
from fnmatch import fnmatch
from pathlib import Path

if __package__ in {None, ""}:
    from common import AuditionError, DEFAULT_MODEL_CONFIG, filter_by_keys, load_models
else:
    from .common import AuditionError, DEFAULT_MODEL_CONFIG, filter_by_keys, load_models


def import_hf() -> tuple[object, object]:
    try:
        from huggingface_hub import hf_hub_download, list_repo_files  # type: ignore
    except ImportError as exc:
        raise AuditionError(
            "Missing huggingface_hub. Install it in a venv instead of system Python, e.g.\n"
            "  python3 -m venv ~/ai/tools/hf-venv\n"
            "  ~/ai/tools/hf-venv/bin/python -m pip install -U 'huggingface_hub[cli]' hf_xet\n"
            "Then run this script with ~/ai/tools/hf-venv/bin/python."
        ) from exc
    return hf_hub_download, list_repo_files


def choose_file(files: list[str], pattern: str) -> str | None:
    matches = [f for f in files if f.endswith(".gguf") and fnmatch(Path(f).name, pattern)]
    if not matches:
        return None
    # Prefer top-level files over nested paths, then shortest name for stability.
    return sorted(matches, key=lambda item: (item.count("/"), len(item), item))[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", default=DEFAULT_MODEL_CONFIG)
    parser.add_argument("--only", default=None, help="Comma-separated model keys to download.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    hf_hub_download, list_repo_files = import_hf()
    models = filter_by_keys(load_models(args.models), args.only)

    for model in models:
        print(f"\n=== {model.key}: {model.label} ===")
        if not model.repo or not model.filename_pattern:
            print("SKIP: repo or filename_pattern not declared.")
            continue
        if not model.path:
            print("SKIP: no local model path declared for this endpoint-only model.")
            continue

        print(f"Repo: {model.repo}")
        print(f"Pattern: {model.filename_pattern}")
        files = list_repo_files(model.repo)  # type: ignore[misc]
        selected = choose_file(files, model.filename_pattern)
        if not selected:
            print("NO MATCH. Available Q4-ish GGUF files:")
            for f in files:
                name = Path(f).name
                if f.endswith(".gguf") and ("Q4" in name or "IQ4" in name):
                    print(f"  {f}")
            continue

        out_dir = Path(model.path).expanduser().parent
        print(f"Selected: {selected}")
        print(f"Local dir: {out_dir}")
        if args.dry_run:
            continue
        out_dir.mkdir(parents=True, exist_ok=True)
        path = hf_hub_download(  # type: ignore[misc]
            repo_id=model.repo,
            filename=selected,
            local_dir=out_dir,
            local_dir_use_symlinks=False,
        )
        print(f"Downloaded: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
