# Read-only snippet
# Source: local_harness/run_single_worker.py

#!/usr/bin/env python3
"""Execute a single-worker local-agent run into the audited folder shape."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "XX_backend"))

from validate_agent_run import validate_run_folder  # type: ignore  # noqa: E402
from icm_call import DEFAULT_WORKERS, call_worker, resolve_worker_spec  # noqa: E402


REQUIRED_INPUT_FILES = ("TASK.md", "INPUT.md", "MODEL_REQUEST.md")

[truncated after 20 lines]
