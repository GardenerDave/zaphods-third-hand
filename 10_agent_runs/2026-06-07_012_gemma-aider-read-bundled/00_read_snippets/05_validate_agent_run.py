# Read-only snippet
# Source: XX_backend/validate_agent_run.py

#!/usr/bin/env python3
"""Validate the file shape of a single-worker local-agent run folder."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


REQUIRED_FILES: tuple[str, ...] = (
    "TASK.md",
    "INPUT.md",
    "MODEL_REQUEST.md",
    "OUTPUT.md",
    "REVIEW.md",
    "METRICS.json",
    "ACCEPTED.md",
)


@dataclass(frozen=True)
class ValidationResult:
    """Presence-only validation result for a local-agent run folder."""

    run_folder: Path
    missing_files: tuple[str, ...]
    path_error: str | None = None

    @property
    def valid(self) -> bool:
        return self.path_error is None and not self.missing_files


def validate_run_folder(
    run_folder: str | Path,
    required_files: Iterable[str] = REQUIRED_FILES,
) -> ValidationResult:
    """Check that required artifact filenames exist without reading file contents."""

    folder = Path(run_folder)
    if not folder.exists():
        return ValidationResult(folder, tuple(required_files), "path does not exist")
    if not folder.is_dir():
        return ValidationResult(folder, tuple(required_files), "path is not a directory")

    missing = tuple(name for name in required_files if not (folder / name).is_file())
    return ValidationResult(folder, missing)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate the required artifact files for a local-agent run folder.",
    )
    parser.add_argument("run_folder", help="Path to the local-agent run folder.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    result = validate_run_folder(args.run_folder)

    if result.valid:
        print(f"Valid local-agent run folder: {result.run_folder}")
        return 0

    print(f"Invalid local-agent run folder: {result.run_folder}")
    if result.path_error:

[truncated after 70 lines]
