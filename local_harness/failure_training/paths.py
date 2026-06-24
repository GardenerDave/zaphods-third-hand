"""Path helpers for failure curriculum cycles."""

from __future__ import annotations

from pathlib import Path


CYCLE_SUBDIRS = (
    "inputs",
    "failures",
    "curriculum",
    "datasets",
    "tuning",
    "evaluation",
)


def cycle_dir(root: str | Path, cycle_id: str) -> Path:
    return Path(root) / "cycles" / cycle_id


def ensure_cycle_tree(root: str | Path, cycle_id: str) -> Path:
    base = cycle_dir(root, cycle_id)
    for child in CYCLE_SUBDIRS:
        (base / child).mkdir(parents=True, exist_ok=True)
    return base
