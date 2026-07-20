#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.overnight_queue_authority import load_registry, load_stage_definitions, render_queue_template
REGISTRY = ROOT / "docs" / "reports" / "model_auditions" / "OVERNIGHT_QUEUE_AUTHORITY_REGISTRY.json"
STAGES = ROOT / "docs" / "reports" / "model_auditions" / "OVERNIGHT_QUEUE_STAGE_DEFINITIONS.json"


def main() -> int:
    template = render_queue_template(load_stage_definitions(STAGES), load_registry(REGISTRY))
    sys.stdout.write(template)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
