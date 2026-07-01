from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/larql_delta_design_packet.py"


def write_json(path: Path, payload: dict | list) -> Path:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def activation_capture_record_payload() -> dict:
    return {
        "report_type": "larql_activation_capture_probe.v0",
        "capture_mode": "prompt_forward",
        "compact_vectors_written": True,
        "target_module": "model.layers.0.mlp.down_proj.weight",
        "target_layer": "0",
        "target_module_family": "mlp_projection",
        "larql_core_path": True,
        "adapter_baseline_path": False,
    }


def direction_packet_payload(
    *,
    selected_source: str = "prompt_mean_pool",
    status: str = "direction_candidate_reviewable",
    include_target_metadata: bool = True,
    target_module: str = "model.layers.0.mlp.down_proj.weight",
    target_layer: str = "0",
    target_module_family: str = "mlp_projection",
) -> dict:
    payload = {
        "report_type": "larql_prompt_activation_direction_packet.v0",
        "direction_candidate_status": status,
        "recommended_vector_source": selected_source,
        "delta_artifact_recommended": False,
    }
    if include_target_metadata:
        payload["target_module"] = target_module
        payload["target_layer"] = target_layer
        payload["target_module_family"] = target_module_family
    return payload


def coherence_payload() -> dict:
    return {
        "selection_rule": "max_positive_coherence_margin",
        "file_scope_mean_pool_mean_cosine": 0.73,
        "regression_vs_file_scope_mean_pool_cosine": 0.21,
    }


def compact_rows(*, missing_input: bool = False) -> list[dict]:
    rows = []
    probe_specs = {
        "original_larql_behavior_replay": {
            "failure_out": [0.0, 0.0],
            "correction_out": [1.0, 0.0],
            "failure_in": [1.0, 0.0, 0.0],
        },
        "adjacent_file_anti_overfit": {
            "failure_out": [0.0, 0.0],
            "correction_out": [0.8, 0.2],
            "failure_in": [0.8, 0.1, 0.1],
        },
        "all_files_authorized_control": {
            "failure_out": [0.0, 0.0],
            "correction_out": [0.9, 0.1],
            "failure_in": [0.9, 0.0, 0.1],
        },
        "unrelated_task_regression": {
            "failure_out": [0.0, 0.0],
            "correction_out": [0.1, 1.0],
            "failure_in": [0.0, 1.0, 0.0],
        },
    }
    for probe_id, spec in probe_specs.items():
        rows.append(
            {
                "probe_id": probe_id,
                "side": "failure",
                "target_module": "model.layers.0.mlp.down_proj.weight",
                "target_layer": "0",
                "target_module_family": "mlp_projection",
                "capture_mode": "prompt_forward",
                "vector_dtype": "float32",
                "vector_length": 2,
                "prompt_last_token_vector": spec["failure_out"],
                "prompt_mean_pool_vector": spec["failure_out"],
                "input_vector_dtype": "float32",
                "input_vector_length": 3,
                "prompt_last_token_input_vector": spec["failure_in"] if not missing_input else None,
                "prompt_mean_pool_input_vector": spec["failure_in"] if not missing_input else None,
            }
        )
        rows.append(
            {
                "probe_id": probe_id,
                "side": "correction",
                "target_module": "model.layers.0.mlp.down_proj.weight",
                "target_layer": "0",
                "target_module_family": "mlp_projection",
                "capture_mode": "prompt_forward",
                "vector_dtype": "float32",
                "vector_length": 2,
                "prompt_last_token_vector": spec["correction_out"],
                "prompt_mean_pool_vector": spec["correction_out"],
                "input_vector_dtype": "float32",
                "input_vector_length": 3,
                "prompt_last_token_input_vector": spec["failure_in"] if not missing_input else None,
                "prompt_mean_pool_input_vector": spec["failure_in"] if not missing_input else None,
            }
        )
    return rows


def prepare_inputs(
    tmp_path: Path,
    *,
    missing_input: bool = False,
    selected_source: str = "prompt_mean_pool",
    status: str = "direction_candidate_reviewable",
    include_direction_target_metadata: bool = True,
    capture_has_target_metadata: bool = True,
    compact_has_target_metadata: bool = True,
    direction_target_module: str = "model.layers.0.mlp.down_proj.weight",
    direction_target_layer: str = "0",
    direction_target_module_family: str = "mlp_projection",
) -> tuple[Path, Path, Path, Path]:
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    capture_payload = activation_capture_record_payload()
    if not capture_has_target_metadata:
        capture_payload.pop("target_module", None)
        capture_payload.pop("target_layer", None)
        capture_payload.pop("target_module_family", None)
    capture = write_json(input_dir / "larql_activation_capture_probe.json", capture_payload)
    direction = write_json(
        input_dir / "larql_prompt_activation_direction_packet.json",
        direction_packet_payload(
            selected_source=selected_source,
            status=status,
            include_target_metadata=include_direction_target_metadata,
            target_module=direction_target_module,
            target_layer=direction_target_layer,
            target_module_family=direction_target_module_family,
        ),
    )
    coherence = write_json(input_dir / "direction_coherence_report.json", coherence_payload())
    rows = compact_rows(missing_input=missing_input)
    if not compact_has_target_metadata:
        rows = [dict(row) for row in rows]
        for row in rows:
            row.pop("target_module", None)
            row.pop("target_layer", None)
            row.pop("target_module_family", None)
    compact = input_dir / "compact_prompt_vectors.jsonl"
    compact.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )
    return capture, direction, coherence, compact


def orthogonal_rows(*, zero_output: bool = False, zero_input: bool = False, missing_control_probe: bool = False) -> list[dict]:
    rows = []
    probe_specs = {
        "original_larql_behavior_replay": {
            "failure_out": [0.0, 0.0],
            "correction_out": [1.0, 0.0],
            "failure_in": [1.0, 0.0, 0.0],
        },
        "adjacent_file_anti_overfit": {
            "failure_out": [0.0, 0.0],
            "correction_out": [0.8, 0.2],
            "failure_in": [0.8, 0.1, 0.1],
        },
        "all_files_authorized_control": {
            "failure_out": [0.0, 0.0],
            "correction_out": [0.0, 1.0] if not zero_output else [0.9, 0.1],
            "failure_in": [0.0, 1.0, 0.0] if not zero_input else [0.9, 0.05, 0.05],
        },
        "unrelated_task_regression": {
            "failure_out": [0.0, 0.0],
            "correction_out": [0.1, 1.0] if not zero_output else [0.9, 0.1],
            "failure_in": [0.0, 1.0, 0.0] if not zero_input else [0.9, 0.05, 0.05],
        },
    }
    for probe_id, spec in probe_specs.items():
        if missing_control_probe and probe_id == "unrelated_task_regression":
            continue
        rows.append(
            {
                "probe_id": probe_id,
                "side": "failure",
                "target_module": "model.layers.0.mlp.down_proj.weight",
                "target_layer": "0",
                "target_module_family": "mlp_projection",
                "capture_mode": "prompt_forward",
                "vector_dtype": "float32",
                "vector_length": 2,
                "prompt_last_token_vector": spec["failure_out"],
                "prompt_mean_pool_vector": spec["failure_out"],
                "input_vector_dtype": "float32",
                "input_vector_length": 3,
                "prompt_last_token_input_vector": spec["failure_in"],
                "prompt_mean_pool_input_vector": spec["failure_in"],
            }
        )
        rows.append(
            {
                "probe_id": probe_id,
                "side": "correction",
                "target_module": "model.layers.0.mlp.down_proj.weight",
                "target_layer": "0",
                "target_module_family": "mlp_projection",
                "capture_mode": "prompt_forward",
                "vector_dtype": "float32",
                "vector_length": 2,
                "prompt_last_token_vector": spec["correction_out"],
                "prompt_mean_pool_vector": spec["correction_out"],
                "input_vector_dtype": "float32",
                "input_vector_length": 3,
                "prompt_last_token_input_vector": spec["failure_in"],
                "prompt_mean_pool_input_vector": spec["failure_in"],
            }
        )
    return rows


def run_orthogonal(
    tmp_path: Path,
    *,
    rows: list[dict] | None = None,
    extra_args: list[str] | None = None,
    run_id: str = "delta_orthogonal",
) -> subprocess.CompletedProcess[str]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    capture, direction, coherence, compact = prepare_inputs(tmp_path)
    compact.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in (rows or orthogonal_rows())) + "\n",
        encoding="utf-8",
    )
    out_root = tmp_path / "out"
    args = [
        "--run-id", run_id,
        "--out-root", out_root,
        "--compact-vectors", compact,
        "--direction-packet", direction,
        "--direction-coherence-report", coherence,
        "--source-activation-capture-record", capture,
        "--direction-basis-mode", "target_control_orthogonal",
    ]
    if extra_args:
        args.extend(extra_args)
    args.append("--authorize-larql-delta-design-packet")
    return run_script(*args)


def run_script(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_help_works():
    result = run_script("--help")
    assert result.returncode == 0
    assert "usage:" in result.stdout.lower()


def test_missing_authorization_exits_nonzero_and_writes_no_packet(tmp_path):
    capture, direction, coherence, compact = prepare_inputs(tmp_path)
    out_root = tmp_path / "out"
    result = run_script(
        "--run-id", "delta_001",
        "--out-root", out_root,
        "--compact-vectors", compact,
        "--direction-packet", direction,
        "--direction-coherence-report", coherence,
        "--source-activation-capture-record", capture,
    )
    assert result.returncode != 0
    assert "requires explicit opt-in authorization" in result.stdout
    assert not (out_root / "delta_001/larql_delta_design_packet.json").exists()


def test_valid_fixture_writes_all_packet_files(tmp_path):
    capture, direction, coherence, compact = prepare_inputs(tmp_path)
    out_root = tmp_path / "out"
    result = run_script(
        "--run-id", "delta_002",
        "--out-root", out_root,
        "--compact-vectors", compact,
        "--direction-packet", direction,
        "--direction-coherence-report", coherence,
        "--source-activation-capture-record", capture,
        "--authorize-larql-delta-design-packet",
    )
    assert result.returncode == 0
    out_dir = out_root / "delta_002"
    for name in [
        "larql_delta_design_packet.json",
        "rank1_delta_design.json",
        "delta_design_risk_register.md",
        "delta_design_review_packet.md",
    ]:
        assert (out_dir / name).exists()


def test_packet_computes_rank1_design_shape_and_keeps_boundaries_false(tmp_path):
    capture, direction, coherence, compact = prepare_inputs(tmp_path)
    out_root = tmp_path / "out"
    run_script(
        "--run-id", "delta_003",
        "--out-root", out_root,
        "--compact-vectors", compact,
        "--direction-packet", direction,
        "--direction-coherence-report", coherence,
        "--source-activation-capture-record", capture,
        "--authorize-larql-delta-design-packet",
    )
    payload = json.loads((out_root / "delta_003/larql_delta_design_packet.json").read_text(encoding="utf-8"))
    design = json.loads((out_root / "delta_003/rank1_delta_design.json").read_text(encoding="utf-8"))
    assert payload["report_type"] == "larql_delta_design_packet.v0"
    assert payload["selected_vector_source"] == "prompt_mean_pool"
    assert payload["vector_source_override_used"] is False
    assert payload["original_recommended_vector_source"] == "prompt_mean_pool"
    assert payload["target_module_override_used"] is False
    assert payload["target_module"] == "model.layers.0.mlp.down_proj.weight"
    assert payload["target_layer"] == "0"
    assert payload["target_module_family"] == "mlp_projection"
    assert payload["original_target_module"] == "model.layers.0.mlp.down_proj.weight"
    assert payload["original_target_layer"] == "0"
    assert payload["original_target_module_family"] == "mlp_projection"
    assert payload["source_vector_target_module"] == "model.layers.0.mlp.down_proj.weight"
    assert payload["source_vector_target_layer"] == "0"
    assert payload["source_vector_target_module_family"] == "mlp_projection"
    assert payload["proposed_delta_shape"] == [2, 3]
    assert payload["delta_design_status"] == "delta_design_reviewable"
    assert payload["model_inference_performed"] is False
    assert payload["weight_edit_performed"] is False
    assert payload["delta_artifact_written"] is False
    assert payload["patched_model_materialized"] is False
    assert payload["training_performed"] is False
    assert payload["adapter_baseline_path"] is False
    assert payload["promotion_authorized"] is False
    assert payload["automatic_failure_to_curriculum_capture_authorized"] is False
    assert payload["delta_artifact_recommended"] is False
    assert design["rank"] == 1
    assert design["writes_tensor_artifact"] is False
    assert design["target_module"] == "model.layers.0.mlp.down_proj.weight"


def test_valid_override_selects_prompt_last_token_and_records_provenance(tmp_path):
    capture, direction, coherence, compact = prepare_inputs(tmp_path)
    out_root = tmp_path / "out"
    result = run_script(
        "--run-id", "delta_003_override",
        "--out-root", out_root,
        "--compact-vectors", compact,
        "--direction-packet", direction,
        "--direction-coherence-report", coherence,
        "--source-activation-capture-record", capture,
        "--vector-source-override", "prompt_last_token",
        "--authorize-larql-delta-design-packet",
    )
    assert result.returncode == 0
    payload = json.loads((out_root / "delta_003_override/larql_delta_design_packet.json").read_text(encoding="utf-8"))
    design = json.loads((out_root / "delta_003_override/rank1_delta_design.json").read_text(encoding="utf-8"))
    assert payload["selected_vector_source"] == "prompt_last_token"
    assert payload["vector_source_override_used"] is True
    assert payload["original_recommended_vector_source"] == "prompt_mean_pool"
    assert payload["proposed_delta_shape"] == [2, 3]
    assert design["selected_vector_source"] == "prompt_last_token"
    assert design["vector_source_override_used"] is True
    assert design["original_recommended_vector_source"] == "prompt_mean_pool"
    assert design["writes_tensor_artifact"] is False


def test_invalid_override_fails_closed(tmp_path):
    capture, direction, coherence, compact = prepare_inputs(tmp_path)
    out_root = tmp_path / "out"
    result = run_script(
        "--run-id", "delta_003_invalid_override",
        "--out-root", out_root,
        "--compact-vectors", compact,
        "--direction-packet", direction,
        "--direction-coherence-report", coherence,
        "--source-activation-capture-record", capture,
        "--vector-source-override", "bad_source",
        "--authorize-larql-delta-design-packet",
    )
    assert result.returncode != 0
    assert "selected vector source must be prompt_last_token or prompt_mean_pool" in result.stdout
    assert not (out_root / "delta_003_invalid_override/larql_delta_design_packet.json").exists()


def test_valid_target_module_override_selects_new_layer_and_records_provenance(tmp_path):
    capture, direction, coherence, compact = prepare_inputs(tmp_path)
    out_root = tmp_path / "out"
    result = run_script(
        "--run-id", "delta_003_target_override",
        "--out-root", out_root,
        "--compact-vectors", compact,
        "--direction-packet", direction,
        "--direction-coherence-report", coherence,
        "--source-activation-capture-record", capture,
        "--target-module-override", "model.layers.14.mlp.down_proj.weight",
        "--authorize-larql-delta-design-packet",
    )
    assert result.returncode == 0
    payload = json.loads((out_root / "delta_003_target_override/larql_delta_design_packet.json").read_text(encoding="utf-8"))
    design = json.loads((out_root / "delta_003_target_override/rank1_delta_design.json").read_text(encoding="utf-8"))
    assert payload["target_module"] == "model.layers.14.mlp.down_proj.weight"
    assert payload["target_layer"] == "14"
    assert payload["target_module_family"] == "mlp_projection"
    assert payload["target_module_override_used"] is True
    assert payload["original_target_module"] == "model.layers.0.mlp.down_proj.weight"
    assert payload["original_target_layer"] == "0"
    assert payload["original_target_module_family"] == "mlp_projection"
    assert payload["source_vector_target_module"] == "model.layers.0.mlp.down_proj.weight"
    assert payload["source_vector_target_layer"] == "0"
    assert payload["source_vector_target_module_family"] == "mlp_projection"
    assert payload["proposed_delta_shape"] == [2, 3]
    assert design["target_module"] == "model.layers.14.mlp.down_proj.weight"
    assert design["target_layer"] == "14"
    assert design["target_module_override_used"] is True
    assert design["source_vector_target_module"] == "model.layers.0.mlp.down_proj.weight"
    assert design["writes_tensor_artifact"] is False


def test_invalid_target_module_override_fails_closed(tmp_path):
    capture, direction, coherence, compact = prepare_inputs(tmp_path)
    out_root = tmp_path / "out"
    result = run_script(
        "--run-id", "delta_003_invalid_target_override",
        "--out-root", out_root,
        "--compact-vectors", compact,
        "--direction-packet", direction,
        "--direction-coherence-report", coherence,
        "--source-activation-capture-record", capture,
        "--target-module-override", "model.layers.14.mlp.up_proj.weight",
        "--authorize-larql-delta-design-packet",
    )
    assert result.returncode != 0
    assert "target module override must match model.layers.<integer>.mlp.down_proj.weight" in result.stdout
    assert not (out_root / "delta_003_invalid_target_override/larql_delta_design_packet.json").exists()


def test_target_control_orthogonal_mode_records_required_fields(tmp_path):
    out_root = tmp_path / "out"
    result = run_orthogonal(tmp_path, run_id="delta_003_orthogonal")
    assert result.returncode == 0
    payload = json.loads((out_root / "delta_003_orthogonal/larql_delta_design_packet.json").read_text(encoding="utf-8"))
    design = json.loads((out_root / "delta_003_orthogonal/rank1_delta_design.json").read_text(encoding="utf-8"))
    assert payload["direction_basis_mode"] == "target_control_orthogonal"
    assert payload["target_probe_ids"] == ["original_larql_behavior_replay", "adjacent_file_anti_overfit"]
    assert payload["control_probe_ids"] == ["all_files_authorized_control", "unrelated_task_regression"]
    assert payload["control_probe_subset"] == ["all_files_authorized_control", "unrelated_task_regression"]
    assert payload["orthogonalization_applied"] is True
    assert payload["orthogonalization_strength"] == 1.0
    assert payload["orthogonalization_side"] == "output_and_input"
    assert isinstance(payload["output_control_projection_removed_norm"], float)
    assert isinstance(payload["input_control_projection_removed_norm"], float)
    assert isinstance(payload["output_control_projection_applied_norm"], float)
    assert isinstance(payload["input_control_projection_applied_norm"], float)
    assert isinstance(payload["output_target_control_cosine_before_projection"], float)
    assert isinstance(payload["input_target_control_cosine_before_projection"], float)
    assert payload["orthogonal_output_direction_norm"] > 0.0
    assert payload["orthogonal_input_basis_norm"] > 0.0
    assert payload["proposed_delta_shape"] == [2, 3]
    assert design["direction_basis_mode"] == "target_control_orthogonal"
    assert design["writes_tensor_artifact"] is False


def test_invalid_direction_basis_mode_fails_closed(tmp_path):
    capture, direction, coherence, compact = prepare_inputs(tmp_path)
    out_root = tmp_path / "out"
    result = run_script(
        "--run-id", "delta_003_bad_basis",
        "--out-root", out_root,
        "--compact-vectors", compact,
        "--direction-packet", direction,
        "--direction-coherence-report", coherence,
        "--source-activation-capture-record", capture,
        "--direction-basis-mode", "bad_basis",
        "--authorize-larql-delta-design-packet",
    )
    assert result.returncode != 0
    assert "direction basis mode must be file_scope_mean or target_control_orthogonal" in result.stdout
    assert not (out_root / "delta_003_bad_basis/larql_delta_design_packet.json").exists()


def test_orthogonalization_args_without_orthogonal_mode_fail_closed(tmp_path):
    capture, direction, coherence, compact = prepare_inputs(tmp_path)
    out_root = tmp_path / "out"
    result = run_script(
        "--run-id", "delta_args_bad_mode",
        "--out-root", out_root,
        "--compact-vectors", compact,
        "--direction-packet", direction,
        "--direction-coherence-report", coherence,
        "--source-activation-capture-record", capture,
        "--orthogonalization-strength", "0.5",
        "--authorize-larql-delta-design-packet",
    )
    assert result.returncode != 0
    assert "orthogonalization parameters require direction basis mode target_control_orthogonal" in result.stdout


def test_strength_half_records_correct_strength(tmp_path):
    out_root = tmp_path / "out"
    result = run_orthogonal(
        tmp_path,
        extra_args=["--orthogonalization-strength", "0.5"],
        run_id="delta_strength_half",
    )
    assert result.returncode == 0
    payload = json.loads((out_root / "delta_strength_half/larql_delta_design_packet.json").read_text(encoding="utf-8"))
    assert payload["orthogonalization_strength"] == 0.5


def test_strength_zero_is_accepted_and_records_zero_applied_norms(tmp_path):
    out_root = tmp_path / "out"
    result = run_orthogonal(
        tmp_path,
        extra_args=["--orthogonalization-strength", "0.0"],
        run_id="delta_strength_zero",
    )
    assert result.returncode == 0
    payload = json.loads((out_root / "delta_strength_zero/larql_delta_design_packet.json").read_text(encoding="utf-8"))
    assert payload["orthogonalization_strength"] == 0.0
    assert payload["output_control_projection_applied_norm"] == 0.0
    assert payload["input_control_projection_applied_norm"] == 0.0


def test_invalid_strengths_fail_closed(tmp_path):
    for bad in ["-0.1", "1.1", "abc"]:
        result = run_orthogonal(
            tmp_path / bad.replace(".", "_").replace("-", "n"),
            extra_args=["--orthogonalization-strength", bad],
            run_id="delta_bad_strength",
        )
        assert result.returncode != 0


def test_output_only_records_input_projection_not_applied(tmp_path):
    out_root = tmp_path / "out"
    result = run_orthogonal(
        tmp_path,
        extra_args=["--orthogonalization-side", "output_only"],
        run_id="delta_output_only",
    )
    assert result.returncode == 0
    payload = json.loads((out_root / "delta_output_only/larql_delta_design_packet.json").read_text(encoding="utf-8"))
    assert payload["orthogonalization_side"] == "output_only"
    assert payload["output_control_projection_applied_norm"] > 0.0
    assert payload["input_control_projection_applied_norm"] == 0.0


def test_input_only_records_output_projection_not_applied(tmp_path):
    out_root = tmp_path / "out"
    result = run_orthogonal(
        tmp_path,
        extra_args=["--orthogonalization-side", "input_only"],
        run_id="delta_input_only",
    )
    assert result.returncode == 0
    payload = json.loads((out_root / "delta_input_only/larql_delta_design_packet.json").read_text(encoding="utf-8"))
    assert payload["orthogonalization_side"] == "input_only"
    assert payload["output_control_projection_applied_norm"] == 0.0
    assert payload["input_control_projection_applied_norm"] > 0.0


def test_valid_single_control_subsets(tmp_path):
    out_root = tmp_path / "out"
    result_a = run_orthogonal(
        tmp_path / "a",
        extra_args=["--control-probe-subset", "all_files_authorized_control"],
        run_id="delta_subset_a",
    )
    assert result_a.returncode == 0
    payload_a = json.loads(((tmp_path / "a") / "out/delta_subset_a/larql_delta_design_packet.json").read_text(encoding="utf-8"))
    assert payload_a["control_probe_subset"] == ["all_files_authorized_control"]
    result_b = run_orthogonal(
        tmp_path / "b",
        extra_args=["--control-probe-subset", "unrelated_task_regression"],
        run_id="delta_subset_b",
    )
    assert result_b.returncode == 0
    payload_b = json.loads(((tmp_path / "b") / "out/delta_subset_b/larql_delta_design_packet.json").read_text(encoding="utf-8"))
    assert payload_b["control_probe_subset"] == ["unrelated_task_regression"]


def test_invalid_control_probe_subsets_fail_closed(tmp_path):
    for subset in [
        "all_files_authorized_control,all_files_authorized_control",
        "unknown_probe",
        "",
    ]:
        result = run_orthogonal(
            tmp_path / (subset or "empty"),
            extra_args=["--control-probe-subset", subset],
            run_id="delta_bad_subset",
        )
        assert result.returncode != 0


def test_missing_required_control_probe_fails_closed(tmp_path):
    capture, direction, coherence, compact = prepare_inputs(tmp_path)
    compact.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in orthogonal_rows(missing_control_probe=True)) + "\n",
        encoding="utf-8",
    )
    out_root = tmp_path / "out"
    result = run_script(
        "--run-id", "delta_003_missing_control",
        "--out-root", out_root,
        "--compact-vectors", compact,
        "--direction-packet", direction,
        "--direction-coherence-report", coherence,
        "--source-activation-capture-record", capture,
        "--direction-basis-mode", "target_control_orthogonal",
        "--authorize-larql-delta-design-packet",
    )
    assert result.returncode != 0
    assert "required control probes were missing for target_control_orthogonal mode" in result.stdout
    assert not (out_root / "delta_003_missing_control/larql_delta_design_packet.json").exists()


def test_zero_orthogonalized_output_direction_fails_closed(tmp_path):
    capture, direction, coherence, compact = prepare_inputs(tmp_path)
    compact.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in orthogonal_rows(zero_output=True)) + "\n",
        encoding="utf-8",
    )
    out_root = tmp_path / "out"
    result = run_script(
        "--run-id", "delta_003_zero_output",
        "--out-root", out_root,
        "--compact-vectors", compact,
        "--direction-packet", direction,
        "--direction-coherence-report", coherence,
        "--source-activation-capture-record", capture,
        "--direction-basis-mode", "target_control_orthogonal",
        "--authorize-larql-delta-design-packet",
    )
    assert result.returncode != 0
    assert "orthogonalized output direction norm must be positive" in result.stdout
    assert not (out_root / "delta_003_zero_output/larql_delta_design_packet.json").exists()


def test_zero_orthogonalized_input_basis_fails_closed(tmp_path):
    capture, direction, coherence, compact = prepare_inputs(tmp_path)
    compact.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in orthogonal_rows(zero_input=True)) + "\n",
        encoding="utf-8",
    )
    out_root = tmp_path / "out"
    result = run_script(
        "--run-id", "delta_003_zero_input",
        "--out-root", out_root,
        "--compact-vectors", compact,
        "--direction-packet", direction,
        "--direction-coherence-report", coherence,
        "--source-activation-capture-record", capture,
        "--direction-basis-mode", "target_control_orthogonal",
        "--authorize-larql-delta-design-packet",
    )
    assert result.returncode != 0
    assert "orthogonalized input basis norm must be positive" in result.stdout
    assert not (out_root / "delta_003_zero_input/larql_delta_design_packet.json").exists()


def test_real_style_direction_packet_without_target_fields_resolves_from_source_capture_record(tmp_path):
    capture, direction, coherence, compact = prepare_inputs(
        tmp_path,
        include_direction_target_metadata=False,
    )
    out_root = tmp_path / "out"
    run_script(
        "--run-id", "delta_003b",
        "--out-root", out_root,
        "--compact-vectors", compact,
        "--direction-packet", direction,
        "--direction-coherence-report", coherence,
        "--source-activation-capture-record", capture,
        "--authorize-larql-delta-design-packet",
    )
    payload = json.loads((out_root / "delta_003b/larql_delta_design_packet.json").read_text(encoding="utf-8"))
    assert payload["target_module"] == "model.layers.0.mlp.down_proj.weight"
    assert payload["target_layer"] == "0"
    assert payload["target_module_family"] == "mlp_projection"


def test_direction_source_target_mismatch_fails_closed(tmp_path):
    capture, direction, coherence, compact = prepare_inputs(
        tmp_path,
        direction_target_module="model.layers.1.mlp.down_proj.weight",
    )
    out_root = tmp_path / "out"
    result = run_script(
        "--run-id", "delta_003c",
        "--out-root", out_root,
        "--compact-vectors", compact,
        "--direction-packet", direction,
        "--direction-coherence-report", coherence,
        "--source-activation-capture-record", capture,
        "--authorize-larql-delta-design-packet",
    )
    assert result.returncode != 0
    assert "target_module provenance mismatch" in result.stdout
    assert not (out_root / "delta_003c/larql_delta_design_packet.json").exists()


def test_compact_rows_can_resolve_target_metadata_when_other_sources_lack_it(tmp_path):
    capture, direction, coherence, compact = prepare_inputs(
        tmp_path,
        include_direction_target_metadata=False,
        capture_has_target_metadata=False,
    )
    out_root = tmp_path / "out"
    run_script(
        "--run-id", "delta_003d",
        "--out-root", out_root,
        "--compact-vectors", compact,
        "--direction-packet", direction,
        "--direction-coherence-report", coherence,
        "--source-activation-capture-record", capture,
        "--authorize-larql-delta-design-packet",
    )
    payload = json.loads((out_root / "delta_003d/larql_delta_design_packet.json").read_text(encoding="utf-8"))
    assert payload["target_module"] == "model.layers.0.mlp.down_proj.weight"
    assert payload["target_layer"] == "0"
    assert payload["target_module_family"] == "mlp_projection"


def test_no_target_metadata_anywhere_fails_closed(tmp_path):
    capture, direction, coherence, compact = prepare_inputs(
        tmp_path,
        include_direction_target_metadata=False,
        capture_has_target_metadata=False,
        compact_has_target_metadata=False,
    )
    out_root = tmp_path / "out"
    result = run_script(
        "--run-id", "delta_003e",
        "--out-root", out_root,
        "--compact-vectors", compact,
        "--direction-packet", direction,
        "--direction-coherence-report", coherence,
        "--source-activation-capture-record", capture,
        "--authorize-larql-delta-design-packet",
    )
    assert result.returncode != 0
    assert "unable to resolve target_module" in result.stdout
    assert not (out_root / "delta_003e/larql_delta_design_packet.json").exists()


def test_missing_input_vectors_is_rejected_or_unclear(tmp_path):
    capture, direction, coherence, compact = prepare_inputs(tmp_path, missing_input=True)
    out_root = tmp_path / "out"
    run_script(
        "--run-id", "delta_004",
        "--out-root", out_root,
        "--compact-vectors", compact,
        "--direction-packet", direction,
        "--direction-coherence-report", coherence,
        "--source-activation-capture-record", capture,
        "--authorize-larql-delta-design-packet",
    )
    payload = json.loads((out_root / "delta_004/larql_delta_design_packet.json").read_text(encoding="utf-8"))
    assert payload["delta_design_status"] in {"delta_design_rejected", "delta_design_unclear"}


def test_selected_source_none_is_rejected(tmp_path):
    capture, direction, coherence, compact = prepare_inputs(tmp_path, selected_source="none")
    out_root = tmp_path / "out"
    run_script(
        "--run-id", "delta_005",
        "--out-root", out_root,
        "--compact-vectors", compact,
        "--direction-packet", direction,
        "--direction-coherence-report", coherence,
        "--source-activation-capture-record", capture,
        "--authorize-larql-delta-design-packet",
    )
    payload = json.loads((out_root / "delta_005/larql_delta_design_packet.json").read_text(encoding="utf-8"))
    assert payload["delta_design_status"] == "delta_design_rejected"


def test_non_reviewable_direction_packet_is_rejected_or_unclear(tmp_path):
    capture, direction, coherence, compact = prepare_inputs(tmp_path, status="direction_candidate_unclear")
    out_root = tmp_path / "out"
    run_script(
        "--run-id", "delta_006",
        "--out-root", out_root,
        "--compact-vectors", compact,
        "--direction-packet", direction,
        "--direction-coherence-report", coherence,
        "--source-activation-capture-record", capture,
        "--authorize-larql-delta-design-packet",
    )
    payload = json.loads((out_root / "delta_006/larql_delta_design_packet.json").read_text(encoding="utf-8"))
    assert payload["delta_design_status"] in {"delta_design_rejected", "delta_design_unclear"}


def test_no_real_inference_or_model_artifacts_are_written():
    script_text = SCRIPT.read_text(encoding="utf-8")
    assert "transformers" not in script_text
    assert "torch" not in script_text
    assert "safetensors" not in script_text
