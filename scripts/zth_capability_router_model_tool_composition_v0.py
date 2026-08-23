"""Fresh-name adapter over the corrected bounded composition engine.

The engine, authority validator, success-contract evaluator, telemetry path,
and no-replay behavior are reused from the prior exploratory implementation.
Only the frozen task/registry bindings and driver identity are new.
"""

from contextlib import contextmanager

from scripts import zth_capability_router_model_tool_adaptive_composition as engine

TASKS = engine.ROOT / "docs/research/CAPABILITY_ROUTER_MODEL_TOOL_COMPOSITION_V0_TASKS_2026-08-23.json"
REGISTRY = engine.ROOT / "docs/research/CAPABILITY_ROUTER_MODEL_TOOL_COMPOSITION_REGISTRY_V0_2026-08-23.json"
ROOT = engine.ROOT
MAX_REPLANS = engine.MAX_REPLANS


@contextmanager
def _fresh_binding():
    old_tasks, old_registry = engine.TASKS, engine.REGISTRY
    engine.TASKS, engine.REGISTRY = TASKS, REGISTRY
    try:
        yield
    finally:
        engine.TASKS, engine.REGISTRY = old_tasks, old_registry


def model_free_binding():
    with _fresh_binding():
        return engine.model_free_binding()


def load_tasks():
    with _fresh_binding():
        return engine.load_tasks()


def registry_index():
    with _fresh_binding():
        return engine.registry_index()


build_planner_facts = engine.build_planner_facts
plan_capabilities = engine.plan_capabilities
evaluate_success_contract = engine.evaluate_success_contract


def main() -> None:
    with _fresh_binding():
        engine.main()


if __name__ == "__main__":
    main()
