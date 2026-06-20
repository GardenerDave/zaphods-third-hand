# Alpha Readiness Checklist

Start here: [`README.md`](../README.md) -> [`docs/FIRST_SUCCESS.md`](FIRST_SUCCESS.md).

Use this checklist before tagging or announcing an early Zaphod's Third Hand release.

This is not a promise that the toolkit is production-ready. It is a checkpoint for a supervised, source-available, noncommercial alpha.

## Core Toolkit

- [ ] README explains what the toolkit is, who it is for, and what it does not do yet.
- [ ] `docs/FIRST_SUCCESS.md` gives a new user a model-free smoke test and an optional endpoint connectivity smoke.
- [ ] QUICKSTART gives an operator the normal private-source Context Distiller workflow.
- [ ] `config.example.env` uses placeholders or safe local defaults only.
- [ ] `.gitignore` excludes private config, generated outputs, caches, logs, and local source material.
- [ ] License docs state that noncommercial use is allowed and commercial use requires explicit written permission.

## Context Distiller

- [ ] `scripts/run_context_distiller_head.sh` passes a shell syntax check.
- [ ] `local_harness/icm_call.py` passes Python compilation.
- [ ] The distiller can run a tiny compact-mode smoke test against a configured OpenAI-compatible endpoint.
- [ ] Generated sessions, review patches, and run records are written under `outputs/`.
- [ ] Metrics reporting works against a real run.
- [ ] Metrics reporting works against `examples/sample_metrics_run/` without requiring a model endpoint.

## Management-Team Workflow

- [ ] All five role prompts exist under `prompts/`.
- [ ] Role prompts are documented as supervised-only by default.
- [ ] Job packets remain the control surface for role use and lifecycle movement.
- [ ] Unattended execution is not described as approved.
- [ ] Batched execution is not described as approved.
- [ ] Generated review patches are not described as canonical until human acceptance.

## Sanitization

- [ ] No private transcripts, source exports, generated runs, review queues, local logs, or cache files are included.
- [ ] No private LAN IPs, local usernames, private repo paths, API keys, tokens, emails, phone numbers, or private machine names are included.
- [ ] Public endpoint, model, source, and path examples use placeholders such as `<LAN_HOST>` and `<MODEL_ROOT>`.
- [ ] Any literal RFC1918 values are confined to inert synthetic tests or fixtures and do not identify or contact real infrastructure.
- [ ] Published reports normalize operator-specific paths and hosts without changing factual model observations.
- [ ] [`docs/SHARING_CHECKLIST.md`](SHARING_CHECKLIST.md) has been reviewed.
- [ ] [`docs/SANITIZATION_NOTES.md`](SANITIZATION_NOTES.md) reflects the current extracted package.

## Suggested Verification

Run these from the repository root:

```bash
git status --short
git grep -nI -E '(/h[o]me/[[:alnum:]_.-]+|/Users/[[:alnum:]_.-]+|[A-Za-z]:\\Users\\[[:alnum:]_.-]+)' -- . || true
git grep -nI -E '(10[.][0-9]{1,3}[.][0-9]{1,3}[.][0-9]{1,3}|172[.](1[6-9]|2[0-9]|3[01])[.][0-9]{1,3}[.][0-9]{1,3}|192[.]168[.][0-9]{1,3}[.][0-9]{1,3})' -- . ':!local_harness/tests/**' || true
git grep -nI -E '(JAR[V]ICE|Vision[[:space:]]+Planner|sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|BEGIN ([A-Z]+ )?PRIVATE KEY)' -- . || true
git ls-files | grep -E '(^|/)(__pycache__|[.]pytest_cache)(/|$)|[.]py[co]$' || true
bash -n scripts/run_context_distiller_head.sh
python3 -m py_compile local_harness/icm_call.py
python3 local_harness/report_distiller_metrics.py --runs-dir examples --limit 3
```

These commands scan tracked files. Review ignored/generated evidence separately
before publishing it; do not make routine release checks recursively print
private `.work/`, `outputs/`, or `sources/` content.

## Tagging Guidance

Only tag an alpha after the checklist is reviewed and the working tree contains only intentional changes.

Suggested tag shape:

```bash
git tag -a v0.1.0-alpha -m "Zaphod's Third Hand v0.1.0 alpha"
git push origin v0.1.0-alpha
```

Do not tag if private data is present, tests fail, or the current docs imply unattended or batched role execution is approved.
