# Deterministic-first semantic fallback slice

## Purpose

This bounded experiment tests whether Zaphod's Third Hand can derive an
operation without a model when its frozen request grammar is sufficient, and
invoke the demonstrated old `action` + `object_expression` supplier only when
the operation expression is genuinely unresolved.

The hierarchy is:

```text
request
  -> deterministic operation preflight
  -> model fallback only for missing operation semantics
  -> deterministic context-gated normalization
  -> independent authority validation
  -> bounded read-only observation when required
  -> deterministic terminal validation
```

The model never decides whether it is needed, selects a capability or tool,
grants authority, or decides success. The runtime task contains only the
request and legitimate authority facts. Evaluator expectations are physically
separate.

## Frozen deterministic boundary

Resolved deterministic families are presence observation and direct
`inspect`/`amend`/`index`/`dispatch`. Coordinated requests are ambiguous;
archive/delete are unsupported. Polite wrappers such as “Could you check …”
are deterministically recognized as presence context but remain
`SEMANTIC_INTERPRETATION_REQUIRED` because their leading operation is not a
frozen deterministic operation lead. This allows the old semantic interface to
provide the missing operation expression without expanding canonical grammar.

## Supplier responsibilities

| responsibility | supplier |
|---|---|
| request grammar classification | deterministic code |
| operation preflight | deterministic code |
| missing operation expression | Qwen3 1.7B old action interface |
| operation normalization | deterministic code |
| target extraction/equality | deterministic code |
| authority membership | deterministic code + environment authority record |
| repository metadata observation | bounded read-only TOOL |
| observation policy and terminal validation | deterministic code |

The old action interface remains a bounded fallback candidate from the paired
attribution result; no qualification or production promotion occurs here.

## Frozen matrix and budgets

The fresh 12-task matrix contains six deterministic-sufficient tasks, four
semantic-fallback tasks, and two fail-closed tasks. The frozen plan budget is
four model calls and six bounded read-only observations. Six model calls are
avoided by deterministic derivation, defined as the six deterministic tasks
that would otherwise enter the semantic operation path—not as a universal
energy estimate.

The only live model calls are the four fallback routes. The tool returns only
repository-relative path, existence, regular-file status, size, and SHA-256.
No file contents, mutation, shell, network, or process control is available.
