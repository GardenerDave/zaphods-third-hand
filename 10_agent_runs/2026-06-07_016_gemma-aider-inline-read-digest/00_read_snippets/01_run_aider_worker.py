# Read-only snippet
# Source: local_harness/run_aider_worker.py

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
