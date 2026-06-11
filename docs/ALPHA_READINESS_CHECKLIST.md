# Alpha Readiness Checklist

Use this checklist before tagging or announcing an early Zaphod's Third Hand release.

This is not a promise that the toolkit is production-ready. It is a checkpoint for a supervised, source-available, noncommercial alpha.

## Core Toolkit

- [ ] README explains what the toolkit is, who it is for, and what it does not do yet.
- [ ] QUICKSTART gives a new user a short path from configuration to a toy run.
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
- [ ] Any endpoint, model, source, and path examples use placeholders or clearly marked local examples.
- [ ] `docs/SHARING_CHECKLIST.md` has been reviewed.
- [ ] `docs/SANITIZATION_NOTES.md` reflects the current extracted package.

## Suggested Verification

Run these from the repository root:

```bash
git status --short
grep -RniE 'JARVICE|Vision Planner|/home/|192\.168\.|api[_-]?key|secret|token|password|@[A-Za-z0-9._%+-]+\.[A-Za-z]{2,}' . --exclude-dir=.git --exclude-dir=outputs || true
bash -n scripts/run_context_distiller_head.sh
python3 -m py_compile local_harness/icm_call.py
python3 local_harness/report_distiller_metrics.py --runs-dir examples --limit 3
```

## Tagging Guidance

Only tag an alpha after the checklist is reviewed and the working tree contains only intentional changes.

Suggested tag shape:

```bash
git tag -a v0.1.0-alpha -m "Zaphod's Third Hand v0.1.0 alpha"
git push origin v0.1.0-alpha
```

Do not tag if private data is present, tests fail, or the current docs imply unattended or batched role execution is approved.
