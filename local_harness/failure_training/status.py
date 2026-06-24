"""Status logging for failure curriculum runs."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class StatusWriter:
    """Write human-readable and machine-readable status events."""

    def __init__(self, run_dir: str | Path, cycle_id: str) -> None:
        self.run_dir = Path(run_dir)
        self.cycle_id = cycle_id
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.status_log = self.run_dir / "status.log"
        self.status_events = self.run_dir / "status_events.jsonl"

    def event(self, phase: str, event: str, **fields: Any) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "ts": utc_now_iso(),
            "cycle_id": self.cycle_id,
            "phase": phase,
            "event": event,
        }
        payload.update(fields)

        with self.status_events.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, sort_keys=True) + "\n")

        line_bits = [payload["ts"], self.cycle_id, phase, event]
        if "item_id" in fields:
            line_bits.append(str(fields["item_id"]))
        if "status" in fields:
            line_bits.append(str(fields["status"]))

        with self.status_log.open("a", encoding="utf-8") as f:
            f.write(" | ".join(line_bits) + "\n")

        return payload
