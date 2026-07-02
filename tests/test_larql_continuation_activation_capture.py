from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "local_harness/larql_continuation_activation_capture.py"
SPEC = importlib.util.spec_from_file_location("larql_continuation_activation_capture", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def write_json(path: Path, payload: dict | list) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def packet_fixture(tmp_path: Path, *, mutate: dict | None = None) -> Path:
    payload = {
        "evidence_only": True,
        "model_free_packet": True,
        "recommended_next_step": "continuation_activation_capture",
        "automatic_failure_to_curriculum_capture_authorized": False,
        "promotion_authorized": False,
        "training_performed": False,
        "registry_mutation_authorized": False,
        "install_authorized": False,
        "base_model_overwritten": False,
        "selected_boost_tokens": [
            {
                "probe_id": "original_larql_behavior_replay",
                "continuation_type": "corrected",
                "token_index": 0,
                "token_id": 11,
                "token_text": "boost1",
                "selection_action": "boost_corrected_semantic_token",
                "selection_reason": "target semantic corrected token with positive logprob movement",
                "token_category": "semantic_text",
                "patched_minus_base_logprob": 0.5,
                "absolute_delta": 0.5,
                "contributes_to_margin_direction": True,
            },
        ],
        "selected_suppress_tokens": [
            {
                "probe_id": "adjacent_file_anti_overfit",
                "continuation_type": "failure",
                "token_index": 1,
                "token_id": 12,
                "token_text": "suppress1",
                "selection_action": "suppress_failure_semantic_token",
                "selection_reason": "target semantic failure token with negative logprob movement",
                "token_category": "semantic_text",
                "patched_minus_base_logprob": -0.4,
                "absolute_delta": 0.4,
                "contributes_to_margin_direction": True,
            }
        ],
        "selected_control_protection_tokens": [
            {
                "probe_id": "all_files_authorized_control",
                "continuation_type": "corrected",
                "token_index": 0,
                "token_id": 13,
                "token_text": "ctrl1",
                "selection_action": "protect_control_corrected_token",
                "selection_reason": "control corrected token became less likely",
                "token_category": "semantic_text",
                "patched_minus_base_logprob": -0.6,
                "absolute_delta": 0.6,
                "contributes_to_margin_direction": False,
            },
            {
                "probe_id": "unrelated_task_regression",
                "continuation_type": "failure",
                "token_index": 0,
                "token_id": 14,
                "token_text": "ctrl2",
                "selection_action": "protect_control_failure_token",
                "selection_reason": "control failure token became more likely",
                "token_category": "semantic_text",
                "patched_minus_base_logprob": 0.7,
                "absolute_delta": 0.7,
                "contributes_to_margin_direction": False,
            },
        ],
    }
    if mutate:
        payload.update(mutate)
    return write_json(tmp_path / "multi_token_target_packet.json", payload)


def fake_torch_module():
    mod = types.ModuleType("torch")

    class FakeNoGrad:
        def __enter__(self):
            return None

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeTensor:
        def __init__(self, data):
            self.data = data
            self.shape = self._shape(data)

        @staticmethod
        def _shape(data):
            shape = []
            cur = data
            while isinstance(cur, list):
                shape.append(len(cur))
                cur = cur[0] if cur else []
            return tuple(shape)

        def detach(self):
            return self

        def float(self):
            return self

        def cpu(self):
            return self

        def tolist(self):
            return self.data

        def __getitem__(self, item):
            if not isinstance(item, tuple):
                item = (item,)
            cur = self.data
            for part in item:
                if part == slice(None):
                    continue
                cur = cur[part]
            return FakeTensor(cur) if isinstance(cur, list) else cur

    def cat(tensors, dim=0):
        left, right = tensors
        if dim != 1:
            raise NotImplementedError
        return FakeTensor([left.data[0] + right.data[0]])

    mod.no_grad = lambda: FakeNoGrad()
    mod.cat = cat
    mod.FakeTensor = FakeTensor
    return mod


def fake_transformers_module(tokenizer, model):
    mod = types.ModuleType("transformers")

    class AutoTokenizer:
        @staticmethod
        def from_pretrained(*args, **kwargs):
            return tokenizer

    class AutoModelForCausalLM:
        @staticmethod
        def from_pretrained(*args, **kwargs):
            return model

    mod.AutoTokenizer = AutoTokenizer
    mod.AutoModelForCausalLM = AutoModelForCausalLM
    return mod


class FakeHookHandle:
    def __init__(self, module):
        self.module = module

    def remove(self):
        self.module.hook = None


class FakeTargetModule:
    def __init__(self):
        self.hook = None

    def register_forward_hook(self, hook):
        self.hook = hook
        return FakeHookHandle(self)


class FakeModel:
    def __init__(self, module):
        self.module = module

    def eval(self):
        return self

    def __call__(self, input_ids=None):
        seq_len = input_ids.shape[-1]
        hidden = 3
        torch = sys.modules["torch"]
        input_tensor = torch.FakeTensor([[[float(i + j) for j in range(hidden)] for i in range(seq_len)]])
        output_tensor = torch.FakeTensor([[[float(10 * i + j) for j in range(hidden)] for i in range(seq_len)]])
        if self.module.hook is not None:
            self.module.hook(self.module, (input_tensor,), output_tensor)
        return types.SimpleNamespace()


class FakeTokenizer:
    def __init__(self):
        self.vocab = {
            "prompt0": 100,
            "prompt1": 101,
            "boost1": 11,
            "boost2": 15,
            "suppress1": 12,
            "suppress0": 16,
            "ctrl1": 13,
            "ctrl2": 14,
            "fail1": 17,
            "fail2": 18,
        }
        self.inverse_vocab = {value: key for key, value in self.vocab.items()}
        self.all_special_ids = []

    def __call__(self, text, return_tensors="pt", add_special_tokens=True):
        tokens = [tok for tok in str(text).split() if tok]
        ids = [self.vocab[tok] for tok in tokens]
        torch = sys.modules["torch"]
        return {"input_ids": torch.FakeTensor([ids])}

    def decode(self, token_ids, skip_special_tokens=False, clean_up_tokenization_spaces=False):
        return " ".join(self.inverse_vocab[int(token_id)] for token_id in token_ids)


def run_script(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def patch_runtime(monkeypatch, *, allow_inference=True):
    torch_mod = fake_torch_module()
    tokenizer = FakeTokenizer()
    module = FakeTargetModule()
    model = FakeModel(module)
    transformers_mod = fake_transformers_module(tokenizer, model)
    monkeypatch.setitem(sys.modules, "torch", torch_mod)
    monkeypatch.setitem(sys.modules, "transformers", transformers_mod)
    monkeypatch.setattr(MODULE, "resolve_module", lambda _model, _target_module: module)
    monkeypatch.setattr(MODULE, "build_probe_set", lambda: [
        {"probe_id": "original_larql_behavior_replay", "prompt": "prompt0 prompt1"},
        {"probe_id": "adjacent_file_anti_overfit", "prompt": "prompt0 prompt1"},
        {"probe_id": "all_files_authorized_control", "prompt": "prompt0 prompt1"},
        {"probe_id": "unrelated_task_regression", "prompt": "prompt0 prompt1"},
    ])
    monkeypatch.setattr(
        MODULE,
        "build_candidate_answers",
        lambda: {
            "original_larql_behavior_replay": {"corrected_candidate_json": "boost1 boost2", "failure_candidate_json": "fail1 fail2"},
            "adjacent_file_anti_overfit": {"corrected_candidate_json": "boost1 boost2", "failure_candidate_json": "suppress0 suppress1"},
            "all_files_authorized_control": {"corrected_candidate_json": "ctrl1 ctrl2", "failure_candidate_json": "ctrl2 ctrl1"},
            "unrelated_task_regression": {"corrected_candidate_json": "ctrl2 ctrl1", "failure_candidate_json": "ctrl2 ctrl1"},
        },
    )
    monkeypatch.setattr(MODULE, "build_model_prompt", lambda _tok, probe: probe["prompt"])
    return torch_mod, tokenizer, model, module


def test_authorization_required(tmp_path):
    result = run_script(
        "--run-id", "ca_001",
        "--out-root", tmp_path / "out",
        "--base-model-path", tmp_path / "base",
        "--multi-token-target-packet", packet_fixture(tmp_path),
    )
    assert result.returncode != 0
    assert "requires explicit opt-in authorization" in result.stdout


def test_output_directory_exists_fails_closed(tmp_path):
    (tmp_path / "out" / "ca_002").mkdir(parents=True)
    (tmp_path / "base").mkdir()
    result = run_script(
        "--run-id", "ca_002",
        "--out-root", tmp_path / "out",
        "--base-model-path", tmp_path / "base",
        "--multi-token-target-packet", packet_fixture(tmp_path),
        "--authorize-larql-continuation-activation-capture",
    )
    assert result.returncode != 0
    assert "output directory already exists" in result.stdout


def test_missing_packet_and_validation_failures(tmp_path):
    (tmp_path / "base").mkdir()
    missing = run_script(
        "--run-id", "ca_003",
        "--out-root", tmp_path / "out",
        "--base-model-path", tmp_path / "base",
        "--multi-token-target-packet", tmp_path / "missing.json",
        "--authorize-larql-continuation-activation-capture",
    )
    assert missing.returncode != 0
    assert "required file path does not exist" in missing.stdout


def test_packet_provenance_checks(tmp_path):
    (tmp_path / "base").mkdir()
    for field, expected in [
        ("evidence_only", False),
        ("model_free_packet", False),
        ("recommended_next_step", "something_else"),
        ("automatic_failure_to_curriculum_capture_authorized", True),
        ("promotion_authorized", True),
        ("training_performed", True),
    ]:
        bad = packet_fixture(tmp_path, mutate={field: expected})
        result = run_script(
            "--run-id", f"ca_{field}",
            "--out-root", tmp_path / "out",
            "--base-model-path", tmp_path / "base",
            "--multi-token-target-packet", bad,
            "--authorize-larql-continuation-activation-capture",
        )
        assert result.returncode != 0


def test_missing_selected_token_lists_fail_closed(tmp_path):
    (tmp_path / "base").mkdir()
    bad = packet_fixture(tmp_path, mutate={"selected_boost_tokens": []})
    result = run_script(
        "--run-id", "ca_004",
        "--out-root", tmp_path / "out",
        "--base-model-path", tmp_path / "base",
        "--multi-token-target-packet", bad,
        "--authorize-larql-continuation-activation-capture",
    )
    assert result.returncode != 0
    assert "missing selected_boost_tokens" in result.stdout


def test_prediction_position_and_alignment_helpers(monkeypatch):
    torch_mod, tokenizer, model, module = patch_runtime(monkeypatch)
    prompt = "prompt0 prompt1"
    rows = [
        {"probe_id": "original_larql_behavior_replay", "continuation_type": "corrected", "token_index": 0, "token_id": 11, "token_text": "boost1", "selection_action": "boost_corrected_semantic_token", "selection_reason": "r", "token_category": "semantic_text"},
        {"probe_id": "original_larql_behavior_replay", "continuation_type": "corrected", "token_index": 1, "token_id": 12, "token_text": "suppress1", "selection_action": "boost_corrected_semantic_token", "selection_reason": "r", "token_category": "semantic_text"},
    ]
    vectors = MODULE.capture_selected_vectors(
        model=model,
        tokenizer=tokenizer,
        module_obj=module,
        prompt=prompt,
        candidate_text="boost1 suppress1",
        selected_rows=rows,
    )
    assert vectors[0]["prediction_position"] == 1
    assert vectors[1]["prediction_position"] == 2
    assert vectors[0]["continuation_token_position"] == 2
    assert vectors[1]["continuation_token_position"] == 3
    assert vectors[0]["module_output_vector"] == [10.0, 11.0, 12.0]
    assert vectors[1]["module_input_vector"] == [2.0, 3.0, 4.0]


def test_token_alignment_and_selection_actions(tmp_path, monkeypatch):
    patch_runtime(monkeypatch)
    (tmp_path / "base").mkdir()
    record = MODULE.write_continuation_activation_capture(
        run_id="ca_005",
        out_root=tmp_path / "out",
        base_model_path=tmp_path / "base",
        multi_token_target_packet_path=packet_fixture(tmp_path),
        target_module="model.layers.0.mlp.down_proj",
        device="cpu",
        max_selected_tokens=10,
        authorize_larql_continuation_activation_capture=True,
    )
    out_dir = tmp_path / "out" / "ca_005"
    assert (out_dir / "continuation_activation_vectors.jsonl").exists()
    assert (out_dir / "continuation_activation_capture_summary.json").exists()
    assert (out_dir / "continuation_activation_capture_review_packet.md").exists()
    assert record["model_inference_performed"] is True
    assert record["generation_performed"] is False
    assert record["training_performed"] is False
    assert record["delta_artifact_written"] is False
    assert record["patched_model_materialized"] is False
    assert record["promotion_authorized"] is False
    assert record["automatic_failure_to_curriculum_capture_authorized"] is False
    assert record["captured_boost_count"] == 1
    assert record["captured_suppress_count"] == 1
    assert record["captured_control_protection_count"] == 2
    assert record["vector_source"] == "continuation_prediction_position"


def test_token_id_mismatch_fails_closed(tmp_path, monkeypatch):
    patch_runtime(monkeypatch)
    (tmp_path / "base").mkdir()
    bad_packet = packet_fixture(tmp_path)
    payload = json.loads(bad_packet.read_text(encoding="utf-8"))
    payload["selected_boost_tokens"][0]["token_id"] = 999
    write_json(bad_packet, payload)
    try:
        MODULE.write_continuation_activation_capture(
            run_id="ca_006",
            out_root=tmp_path / "out",
            base_model_path=tmp_path / "base",
            multi_token_target_packet_path=bad_packet,
            target_module="model.layers.0.mlp.down_proj",
            device="cpu",
            max_selected_tokens=None,
            authorize_larql_continuation_activation_capture=True,
        )
    except ValueError as exc:
        assert "tokenization/label alignment is invalid" in str(exc)
    else:
        raise AssertionError("expected validation failure")


def test_unsupported_continuation_type_and_out_of_set_probe_fail_closed(tmp_path, monkeypatch):
    patch_runtime(monkeypatch)
    (tmp_path / "base").mkdir()
    bad_packet = packet_fixture(tmp_path)
    payload = json.loads(bad_packet.read_text(encoding="utf-8"))
    payload["selected_boost_tokens"][0]["continuation_type"] = "other"
    payload["selected_boost_tokens"][0]["probe_id"] = "original_larql_behavior_replay"
    write_json(bad_packet, payload)
    try:
        MODULE.write_continuation_activation_capture(
            run_id="ca_007",
            out_root=tmp_path / "out",
            base_model_path=tmp_path / "base",
            multi_token_target_packet_path=bad_packet,
            target_module="model.layers.0.mlp.down_proj",
            device="cpu",
            max_selected_tokens=None,
            authorize_larql_continuation_activation_capture=True,
        )
    except ValueError as exc:
        assert "selected continuation type is not corrected/failure" in str(exc)
    else:
        raise AssertionError("expected validation failure")


def test_selected_probe_outside_bounded_set_fails_closed(tmp_path, monkeypatch):
    patch_runtime(monkeypatch)
    (tmp_path / "base").mkdir()
    bad_packet = packet_fixture(tmp_path)
    payload = json.loads(bad_packet.read_text(encoding="utf-8"))
    payload["selected_boost_tokens"][0]["probe_id"] = "not_a_probe"
    write_json(bad_packet, payload)
    try:
        MODULE.write_continuation_activation_capture(
            run_id="ca_008",
            out_root=tmp_path / "out",
            base_model_path=tmp_path / "base",
            multi_token_target_packet_path=bad_packet,
            target_module="model.layers.0.mlp.down_proj",
            device="cpu",
            max_selected_tokens=None,
            authorize_larql_continuation_activation_capture=True,
        )
    except ValueError as exc:
        assert "selected probe id is not in the bounded probe set" in str(exc)
    else:
        raise AssertionError("expected validation failure")


def test_max_selected_tokens_limit_respected(tmp_path, monkeypatch):
    patch_runtime(monkeypatch)
    (tmp_path / "base").mkdir()
    record = MODULE.write_continuation_activation_capture(
        run_id="ca_008",
        out_root=tmp_path / "out",
        base_model_path=tmp_path / "base",
        multi_token_target_packet_path=packet_fixture(tmp_path),
        target_module="model.layers.0.mlp.down_proj",
        device="cpu",
        max_selected_tokens=2,
        authorize_larql_continuation_activation_capture=True,
    )
    assert record["selected_token_count"] == 2
    assert record["captured_vector_count"] == 2


def test_target_module_missing_fails_closed(tmp_path, monkeypatch):
    patch_runtime(monkeypatch)
    monkeypatch.setattr(
        MODULE,
        "resolve_module",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("target module cannot be found")),
    )
    (tmp_path / "base").mkdir()
    try:
        MODULE.write_continuation_activation_capture(
            run_id="ca_009",
            out_root=tmp_path / "out",
            base_model_path=tmp_path / "base",
            multi_token_target_packet_path=packet_fixture(tmp_path),
            target_module="model.layers.0.mlp.down_proj",
            device="cpu",
            max_selected_tokens=None,
            authorize_larql_continuation_activation_capture=True,
        )
    except ValueError as exc:
        assert "target module cannot be found" in str(exc)
    else:
        raise AssertionError("expected validation failure")


def test_no_generate_call_in_source():
    script_text = SCRIPT.read_text(encoding="utf-8")
    assert "generate(" not in script_text
