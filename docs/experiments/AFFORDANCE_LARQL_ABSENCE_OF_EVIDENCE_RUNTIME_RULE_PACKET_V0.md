# AFFORDANCE_LARQL_ABSENCE_OF_EVIDENCE_RUNTIME_RULE_PACKET_V0

This is a model-free packet scaffold for drafting an absence-of-evidence
runtime rule. It does not install a runtime rule or modify runtime behavior.

The rule idea is:

`absence_of_evidence_is_not_evidence_of_absence`

## Purpose

Prevent treating missing or incomplete evidence as authority to assert absence
or proceed with irreversible lifecycle/file actions.

## Review boundary

This packet is only for drafting. It is not an installed runtime rule and does
not authorize runtime-rule modification.

## What the drafted rule should cover

- evidence is incomplete, stale, file-limited, search-limited, or otherwise
  bounded;
- search results do not cover the full target scope;
- missing search results are not proof of absence;
- claiming a file, rule, test, artifact, path, branch, or record does not
  exist merely because it was not found;
- treating missing search results as authority to delete, promote,
  canonicalize, overwrite, clean up, or proceed with irreversible state
  changes; and
- keeping cleanup, deletion, promotion, canonicalization, and overwrite held
  pending review evidence.

## Required response behavior

- state the evidence boundary explicitly;
- distinguish not found in searched scope from does not exist;
- recommend targeted inspection or review; and
- preserve failed-run or search-boundary evidence where relevant.

## Inspection examples

- `git status --short`
- `find <allowed-root> -maxdepth <n> -type f | sort`
- `grep -R "<target>" <allowed-root>`
- `git ls-files | grep "<target>"`
- `git branch --all --contains <commit>`
- `git log --oneline --all -- <path>`

## Boundary

- No model call.
- No training data write.
- No dataset artifact write.
- No durable memory write.
- No candidate promotion.
- No LoRA training.
- No model weight mutation.
- No runtime rule installation.
- No runtime rule modification.
- No automatic failure-to-curriculum capture.

