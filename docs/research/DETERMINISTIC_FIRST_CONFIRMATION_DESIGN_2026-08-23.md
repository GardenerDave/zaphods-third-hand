# Corrected deterministic-first confirmation

This fresh 8-task confirmation follows the control-plane audit at `7b1071a`.
Runtime cases and evaluator cases are physically separate before preparation.
Runtime authority records are independently authored environment state and are
never synthesized from evaluator expectations.

The confirmation separates:

- `ROUTING_SUCCESS`: requirements resolved, coverage assessed, and authority
  checked;
- `TASK_TERMINAL_SUCCESS`: the required observation/effect was actually
  produced and validated.

The only qualified execution supplier is the existing read-only repository
metadata observer. `inspect`, `amend`, `index`, and `dispatch` do not receive a
new actuator. Amend and dispatch therefore demonstrate correct routing to an
incomplete capability plan and fail closed with
`NO_QUALIFIED_EXECUTION_SUPPLIER`; no operation is performed.

The matrix contains two deterministic presence observations, two old-interface
semantic fallback presence observations, two no-actuator operations, and two
ambiguous/unsupported fail-closed requests. No evaluator field is available to
runtime planning, authority, model prompts, tool authorization, or terminal
validation.
