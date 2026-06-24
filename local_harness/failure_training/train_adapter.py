"""Plan adapter training artifacts without launching training."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .common import sha256_text
from .status import utc_now_iso


TRAINING_METHODS = {
    "lora",
    "qlora",
    "sft",
    "external",
}

ADAPTER_STATUSES = {
    "planned",
    "running",
    "completed",
    "failed",
    "skipped",
}


def normalize_training_method(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in TRAINING_METHODS:
        raise ValueError(f"unsupported training method: {value!r}")
    return normalized


def normalize_adapter_status(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in ADAPTER_STATUSES:
        raise ValueError(f"unsupported adapter status: {value!r}")
    return normalized


def default_adapter_id(*, cycle_id: str, base_model_id: str, training_method: str) -> str:
    digest = sha256_text(f"{cycle_id}|{base_model_id}|{training_method}")[:12]
    safe_cycle = cycle_id.replace("/", "_").replace(" ", "_")
    return f"adapter_{safe_cycle}_{training_method}_{digest}"


def dataset_paths_from_dir(dataset_dir: str | Path) -> dict[str, str]:
    base = Path(dataset_dir)
    return {
        "train": str(base / "train.jsonl"),
        "validation": str(base / "validation.jsonl"),
        "holdout": str(base / "holdout.jsonl"),
        "sft_train": str(base / "sft" / "sft_train.jsonl"),
        "sft_validation": str(base / "sft" / "sft_validation.jsonl"),
        "sft_manifest": str(base / "sft" / "sft_manifest.jsonl"),
    }


def build_adapter_manifest(
    *,
    cycle_id: str,
    base_model_id: str,
    dataset_dir: str | Path,
    output_dir: str | Path,
    training_method: str = "lora",
    status: str = "planned",
    trainer: str = "manual",
    notes: str = "",
) -> dict[str, Any]:
    method = normalize_training_method(training_method)
    adapter_status = normalize_adapter_status(status)
    adapter_id = default_adapter_id(
        cycle_id=cycle_id,
        base_model_id=base_model_id,
        training_method=method,
    )

    out = Path(output_dir)

    return {
        "adapter_id": adapter_id,
        "cycle_id": cycle_id,
        "created_at": utc_now_iso(),
        "base_model_id": base_model_id,
        "training_method": method,
        "trainer": trainer,
        "status": adapter_status,
        "dataset_paths": dataset_paths_from_dir(dataset_dir),
        "artifact_paths": {
            "output_dir": str(out),
            "adapter_dir": str(out / "adapter"),
            "adapter_manifest": str(out / "adapter_manifest.json"),
            "trainer_config": str(out / "trainer_config.json"),
        },
        "metrics": {},
        "notes": notes,
    }


def default_trainer_config(
    *,
    base_model_id: str,
    training_method: str,
    dataset_paths: dict[str, str],
) -> dict[str, Any]:
    return {
        "base_model_id": base_model_id,
        "training_method": normalize_training_method(training_method),
        "train_path": dataset_paths["sft_train"],
        "validation_path": dataset_paths["sft_validation"],
        "holdout_path": dataset_paths["holdout"],
        "launch_policy": "manual_only",
        "notes": "Generated plan only. This command does not launch training.",
    }


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_adapter_plan(
    *,
    cycle_id: str,
    base_model_id: str,
    dataset_dir: str | Path,
    output_dir: str | Path,
    training_method: str = "lora",
    trainer: str = "manual",
    notes: str = "",
) -> dict[str, Any]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    manifest = build_adapter_manifest(
        cycle_id=cycle_id,
        base_model_id=base_model_id,
        dataset_dir=dataset_dir,
        output_dir=out,
        training_method=training_method,
        status="planned",
        trainer=trainer,
        notes=notes,
    )
    trainer_config = default_trainer_config(
        base_model_id=base_model_id,
        training_method=manifest["training_method"],
        dataset_paths=manifest["dataset_paths"],
    )

    write_json(out / "adapter_manifest.json", manifest)
    write_json(out / "trainer_config.json", trainer_config)
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--base-model-id", required=True)
    parser.add_argument("--dataset-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--training-method", default="lora")
    parser.add_argument("--trainer", default="manual")
    parser.add_argument("--notes", default="")
    args = parser.parse_args(argv)

    manifest = write_adapter_plan(
        cycle_id=args.cycle_id,
        base_model_id=args.base_model_id,
        dataset_dir=args.dataset_dir,
        output_dir=args.output_dir,
        training_method=args.training_method,
        trainer=args.trainer,
        notes=args.notes,
    )

    print(
        "Adapter plan written: "
        f"{manifest['artifact_paths']['adapter_manifest']} "
        f"method={manifest['training_method']} status={manifest['status']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
