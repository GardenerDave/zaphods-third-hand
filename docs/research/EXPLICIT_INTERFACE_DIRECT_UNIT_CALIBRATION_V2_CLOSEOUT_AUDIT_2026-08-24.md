# Explicit-Interface Direct Unit Calibration V2 — Closeout Audit

The sealed acquisition was verified model-free before scoring. The frozen
evaluator and evaluator-case artifact hashes matched the V2 freeze. The exact
evaluator implementation was imported only after raw sealing.

Acquisition integrity:

- planned/terminal: 32/32;
- local/external: 16/16;
- response artifacts: 16;
- infrastructure failures: 16, all `EXTERNAL_NONZERO_EXIT`;
- retries/replays: 0/0;
- processes: 1, second process false;
- raw seal: true;
- terminal arm artifact hash records: 32/32, all recomputed;
- evaluator access during acquisition: false;
- evaluator semantics loaded during acquisition: false;
- evaluator runtime influence: 0.

The external failures were identical: return code 1, empty stdout, and a
read-only-filesystem Codex CLI initialization failure in stderr. No external
model-produced response was preserved. The local artifacts were captured as
responses, but all had transport status `request_error`, the same name
resolution error, and no valid supplier response content. Consequently, the
mechanical evaluator rows are direct-capability zeroes, while semantic
capability remains unobserved for both arms.

The experiment therefore cannot support a local-versus-external direct-unit
capability comparison. No scoring semantics were changed, and no transport
failure was converted into a semantic answer.

Closeout calls: supplier/model/external-inference calls `0`; retries `0`;
replays `0`.
