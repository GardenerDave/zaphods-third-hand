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

[truncated after 32 lines]
