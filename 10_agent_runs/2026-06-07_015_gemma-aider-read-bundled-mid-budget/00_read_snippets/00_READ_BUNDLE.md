# Bundled read-only context

## Source 1: local_harness/run_aider_worker.py

#!/usr/bin/env python3
"""Execute a supervised Aider run into the audited single-worker folder shape."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

## Source 2: local_harness/run_single_worker.py

#!/usr/bin/env python3
"""Execute a single-worker local-agent run into the audited folder shape."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

## Source 3: local_harness/icm_call.py

#!/usr/bin/env python3
"""Call local ICM model workers with configurable endpoints."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

[truncated after 13 lines]

## Source 4: local_harness/README.md

# Local Harness

This folder contains the manager-side helper scripts for supervised local-worker runs.

## Scripts

- `icm_call.py`: configurable one-shot worker caller for native `/completion` and OpenAI-compatible `/v1` endpoints.

[truncated after 7 lines]

## Source 5: XX_backend/validate_agent_run.py

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

## Source 6: 10_agent_runs/README.md

# Local Agent Runs

Author: [REDACTED]

This folder stores file-mediated local-agent runs for ICM and InternalCodename support work.


[truncated after 6 lines]
