#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.overnight_queue_authority import AuthorityValidationError, validate_allowed_targets


def validate_queue(path: Path) -> None:
    if not path.is_file():
        raise AuthorityValidationError("queue_file_missing")
    schema = None
    with path.open(encoding="utf-8") as fh:
        for line_no, row in enumerate(csv.reader(fh, delimiter="\t"), start=1):
            if not row:
                continue
            if row[0].startswith("#"):
                if row[0].strip() == "# zth-roadmap-queue-schema: 2":
                    schema = 2
                continue
            if schema != 2:
                raise AuthorityValidationError("unsupported_or_missing_schema_version")
            if len(row) != 4:
                raise AuthorityValidationError(f"row_{line_no}_wrong_field_count")
            if not row[0].strip() or not row[1].strip() or not row[2].strip():
                raise AuthorityValidationError(f"row_{line_no}_missing_required_field")
            allowed = json.loads(row[3])
            validate_allowed_targets(allowed)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: validate_overnight_queue <queue-file>", file=sys.stderr)
        return 2
    try:
        validate_queue(Path(argv[1]))
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
