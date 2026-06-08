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
