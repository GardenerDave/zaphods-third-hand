# 30B Executable Handoff V2 Postmortem

Experiment ID: `30b_executable_handoff_v2_20260830`

## Verdict

Transport succeeded and the intended 30B answered the generated executable continuation prompt. The response preserved authority boundaries but did not perform the requested downstream objective. It again behaved like a first-task restart / bounded report generation, not a faithful continuation from the accepted prior result.

## What was preserved

- Source transaction ID: `orch_manual_20260707t112634z`
- Source run ID: `manual_supervised_attempt_20260707t112634z`
- Endpoint: `http://192.168.1.16:8080/v1`
- Model: `Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf`
- Objective provenance: `operator_supplied_experiment_objective`
- Frozen downstream objective: `Using the accepted design packet above, produce a bounded downstream recommendation identifying the next supervised action, the evidence from the accepted result supporting it, and any unresolved constraint that must remain held.`

## Acquisition summary

- One successful captured acquisition response was preserved.
- Raw response SHA-256: `dd439cafe48235a29dbd17deea51ddabf453405fca0463f84a5eb0f382bdc7ed`
- Transport metadata SHA-256: `a522163919b30bdc6eb2525a4cdffc4a3c2dcff103bff87ffbf2b609b9582022`
- No intentional retry, fallback, or replay was used.

## Semantic result

The 30B response stated a proposed report in `docs/reports/` and summarized the accepted packet, but it did not produce the requested downstream recommendation about the next supervised action, evidence supporting it, and unresolved constraints. It still leaned toward re-parsing the original task contract rather than continuing from the accepted prior result with the explicit downstream objective.

## V1 vs V2

| Dimension | V1 | V2 |
| --- | --- | --- |
| Correct 30B transport | yes | yes |
| Prior result body visible | no | yes |
| Explicit downstream objective | no | yes |
| Authority preserved | yes | yes |
| Used prior result | no / weak | weak / partial |
| Identified/performed next task | no | no |
| Repeated original task | yes / mostly | partially, still restarted toward report generation |
| Valid downstream continuation | no | no |
| Practical handoff verdict | fail | fail |

## Conclusion

V2 fixed the missing visibility and objective framing, but the continuation contract still did not induce a materially correct downstream continuation. The model answered within scope and with provenance intact, yet it still translated the prompt into a report-generation / task-restate response instead of a concrete next-step recommendation grounded in the accepted result.

This is a failure of continuation semantics, not transport or authority.
