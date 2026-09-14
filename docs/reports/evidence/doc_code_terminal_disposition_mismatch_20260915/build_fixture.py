#!/usr/bin/env python3
"""Build the inline-evidence fixture for the terminal-disposition dogfood task.

The prompt inlines verbatim excerpts from the two current artifacts so a
tool-less worker can answer purely from the inlined text. The hidden
expected_output (the mismatch itself) is NOT inlined.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path("/home/navigator/agent-workspace/zaphods-third-hand")
sys.path.insert(0, str(ROOT))
DOC = ROOT / "docs" / "SUPERVISED_CAPABILITY_LOOP.md"  # noqa
PY = ROOT / "local_harness" / "supervised_capability_loop.py"

doc_lines = DOC.read_text(encoding="utf-8").splitlines()
py_lines = PY.read_text(encoding="utf-8").splitlines()


def doc_slice(a: int, b: int) -> str:
    return "\n".join(doc_lines[a - 1 : b])


def py_slice(a: int, b: int) -> str:
    return "\n".join(py_lines[a - 1 : b])


# EXCERPT A -- the doc terminal-state contract (prose idempotency + terminal
# states + transition diagram).
exA = doc_slice(24, 44)
# EXCERPT A2 -- the doc "External teacher boundary" paragraph (fail-closed line).
exA2 = doc_slice(52, 58)

# EXCERPT B -- TERMINAL_DISPOSITIONS constant.
exB = py_slice(40, 40)

# EXCERPT C -- restart idempotency check.
exC = py_slice(714, 717)

# EXCERPT D -- binding preflight terminal return.
exD = py_slice(741, 755)

# EXCERPT E -- final_pass, the external_infrastructure availability check, and
# the final disposition ternary (lines 989-1009).
exE = py_slice(989, 1009)

prompt = f"""You are checking whether two current artifacts in the ZTH repository agree about
which terminal dispositions a supervised capability-loop run can end in.
Answer ONLY from the inlined excerpts below. Do not use any outside knowledge
about the repository, its deployment, or any other file.

EXCERPT A -- docs/SUPERVISED_CAPABILITY_LOOP.md, lines 24-44 (terminal-state
prose and the durable-transition diagram):
--- BEGIN EXCERPT A ---
{exA}
--- END EXCERPT A ---

EXCERPT B -- docs/SUPERVISED_CAPABILITY_LOOP.md, lines 52-58 (the "External
teacher boundary" paragraph):
--- BEGIN EXCERPT B ---
{exA2}
--- END EXCERPT B ---

EXCERPT C -- local_harness/supervised_capability_loop.py, line 40:
--- BEGIN EXCERPT C ---
{exB}
--- END EXCERPT C ---

EXCERPT D -- local_harness/supervised_capability_loop.py, lines 714-717
(the restart idempotency check at the top of run_capability_loop):
--- BEGIN EXCERPT D ---
{exC}
--- END EXCERPT D ---

EXCERPT E -- local_harness/supervised_capability_loop.py, lines 741-755
(the binding preflight terminal return):
--- BEGIN EXCERPT E ---
{exD}
--- END EXCERPT E ---

EXCERPT F -- local_harness/supervised_capability_loop.py, lines 989-1009
(final_pass, the external_infrastructure availability check, and the final
disposition ternary):
--- BEGIN EXCERPT F ---
{exE}
--- END EXCERPT F ---

Note on EXCERPT D: it is inside a function whose first line is
"def run_capability_loop(...)" and whose body begins with
"if max_worker_attempts < 1 or max_teacher_passes < 0:". The check on line
716 tests whether a pre-existing summary is terminal and, if so, returns it.

Answer these eight questions using only the excerpts:

1. doc_terminal_dispositions (array of strings): list every distinct
   disposition string that EXCERPT A explicitly names as a terminal state of a
   run, in the order they are named across the prose and the diagram.
2. code_terminal_dispositions (array of strings): list every distinct
   disposition string that the code in EXCERPTS C through F assigns to a run's
   terminal "disposition" field, sorted alphabetically.
3. code_value_absent_from_doc (string): the single disposition string that
   appears in the code's terminal dispositions (question 2) but is NOT named as
   a terminal state in EXCERPT A.
4. in_terminal_set (true or false): is the string from question 3 a member of
   the set literal in EXCERPT C (TERMINAL_DISPOSITIONS)?
5. idempotent_return_on_infrastructure_error (true or false): suppose the
   summary file exists and its "disposition" value is the string from question
   3. Does the check in EXCERPT D return the existing summary early (i.e. is the
   run treated as terminal and skipped)?
6. external_infra_disposition (string): per EXCERPT F, what is the exact
   "disposition" string assigned when final_pass is false and
   external_infrastructure is truthy (a non-None value)?
7. doc_external_failure_close_matches_code (true or false): EXCERPT B says a
   missing, empty, timed-out, or non-zero external teacher command "fails closed
   to" a particular disposition. Does that disposition match what EXCERPT F
   actually assigns for that same situation (an external-teacher
   infrastructure failure)?
8. mismatch_summary (string, one sentence): in one sentence, state the specific
   mismatch between the terminal dispositions the document (EXCERPT A) says a run
   can end in and the terminal dispositions the code (EXCERPTS C-F) can actually
   produce, and the concrete operational consequence that follows for a run
   ending in that disposition on restart.

Output exactly one JSON object and nothing else, with exactly these keys:
doc_terminal_dispositions, code_terminal_dispositions,
code_value_absent_from_doc, in_terminal_set,
idempotent_return_on_infrastructure_error, external_infra_disposition,
doc_external_failure_close_matches_code, mismatch_summary.
"""

task = {
    "task_id": "doc_code_terminal_disposition_mismatch_20260915",
    "task_family": "doc_code_reconciliation",
    "prompt": prompt,
    "output_contract": {
        "format": "json",
        "required_fields": [
            "doc_terminal_dispositions",
            "code_terminal_dispositions",
            "code_value_absent_from_doc",
            "in_terminal_set",
            "idempotent_return_on_infrastructure_error",
            "external_infra_disposition",
            "doc_external_failure_close_matches_code",
            "mismatch_summary",
        ],
    },
    "expected_output": {
        "doc_terminal_dispositions": ["ready_for_review", "unresolved"],
        "code_terminal_dispositions": ["infrastructure_error", "ready_for_review", "unresolved"],
        "code_value_absent_from_doc": "infrastructure_error",
        "in_terminal_set": False,
        "idempotent_return_on_infrastructure_error": False,
        "external_infra_disposition": "infrastructure_error",
        "doc_external_failure_close_matches_code": False,
        "mismatch_summary": "The document names only ready_for_review and unresolved as terminal dispositions, but the code can also end a run in infrastructure_error, which is absent from the TERMINAL_DISPOSITIONS set, so a run ending in infrastructure_error is not treated as terminal on restart and is re-executed instead of skipped.",
    },
    "validator": {"kind": "exact_json"},
}

out = pathlib.Path("/tmp/zth_terminal_disposition_20260915/fixture.json")
out.write_text(json.dumps(task, indent=2, sort_keys=False) + "\n", encoding="utf-8")

# sanity: exact_json validator round-trips
import local_harness.supervised_capability_loop as s
loaded = s.load_task_fixture(out)
assert loaded["validator"]["kind"] == "exact_json"
assert "expected_output" in loaded
print("fixture written:", out)
print("prompt chars:", len(prompt))
print("required fields:", len(task["output_contract"]["required_fields"]))
