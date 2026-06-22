# Real LLM-Probe Preflight Smoke Run

Date: 2026-06-21 (local operator date)

## Summary

Status: **blocked by missing LLM-probe tooling**.

The already-running local OpenAI-compatible endpoint was reachable and exposed
the expected configured model. However, no LLM-probe executable, Python
module, installed package, local checkout, or genuine
`verified/<provider>.yaml` output was available.

No synthetic fixture was substituted. Because genuine source evidence could
not be generated, the ZTH preflight importer, operator planner, gate, and
audition were not run for this attempt.

## Scope

The intended supervised chain was:

```text
already-running local OpenAI-compatible endpoint
→ genuine LLM-probe verified output
→ ZTH preflight capability manifest
→ operator planner
→ unwaived gated audition if permitted
```

This attempt stopped at the LLM-probe tooling boundary. Stopping there
preserved the distinction between genuine upstream probe evidence and the
checked-in synthetic adapter fixture.

## Inputs

- Endpoint configuration source: private `config.env` variables
  `ICM_ROUTER_BASE_URL` and `ICM_ROUTER_MODEL`
- Intended genuine source path:
  `.work/llm_probe_real_smoke_2026-06-21/verified/<provider>.yaml`
- Intended preflight manifest:
  `.work/llm_probe_preflight/real_llm_probe_smoke_2026-06-21/preflight_capability_manifest.json`
- Intended private model config:
  `.work/preflight_smoke/private_model_real_llm_probe.json`
- Intended suite:
  `local_harness/auditions/suites/baseline_micro_v0.json`
- Intended audition output:
  `.work/model_auditions/real_llm_probe_preflight_smoke_2026-06-21/`
- Intended plan:
  `.work/preflight_audition_plans/real_llm_probe_preflight_smoke_2026-06-21.md`

The intended source, manifest, model config, audition output, and plan were not
created during this blocked attempt.

## Commands Run

Operator-specific home paths are normalized to `$HOME` below.

Private configuration was inspected with redaction:

```bash
rg -n 'ICM_ROUTER_BASE_URL|ICM_ROUTER_MODEL|ZTH_BASE_URL|ZTH_MODEL' \
  config.env config.example.env .env 2>/dev/null |
  sed -E 's#(https?://)[^/ ]+#\1<REDACTED_HOST>#g; s#=.*MODEL.*$#=<REDACTED_MODEL>#'
```

Endpoint availability was checked without committing or reporting its private
URL:

```bash
source config.env
python3 local_harness/icm_call.py router \
  --base-url "$ICM_ROUTER_BASE_URL" \
  --timeout 10 \
  --list-models
```

LLM-probe executable and package discovery:

```bash
command -v llm-probe || true
command -v llm_probe || true
python3 -m pip show llm-probe 2>/dev/null || true
python3 -m pip show llm_probe 2>/dev/null || true
```

Local checkout and genuine-output discovery:

```bash
find . "$HOME" -maxdepth 6 -type f 2>/dev/null |
  rg 'llm[-_]?probe|verified/.+\.(yaml|yml)|provider\.ya?ml|results\.ya?ml|results\.json' |
  head -200
```

User-tool and virtual-environment storage was also inspected directly:

```bash
find "$HOME/.local/share/pipx/venvs" \
     "$HOME/.local/pipx/venvs" \
     "$HOME/.local/share/uv/tools" \
  -maxdepth 4 -type f 2>/dev/null |
  rg 'llm[-_]?probe|entry_points|METADATA' |
  head -200
```

Candidate help commands:

```bash
llm-probe --help
llm_probe --help
python3 -m llm_probe --help
```

`pipx list` and `uv tool list` were attempted, but their normal state/cache
writes were blocked by the restricted execution environment. Direct
inspection of their tool directories still found no LLM-probe installation.

## Results

### Endpoint discovery

- The configured endpoint's `/models` request succeeded.
- The expected configured router model was listed.
- No endpoint was started, stopped, or reconfigured.
- No model prompt was sent.

### LLM-probe discovery

- `llm-probe`: command not found.
- `llm_probe`: command not found.
- `python3 -m llm_probe`: `No module named llm_probe`.
- `pip show` found neither `llm-probe` nor `llm_probe`.
- No local checkout matching LLM-probe was found.
- No genuine local `verified/<provider>.yaml` was found.
- The only matching YAML evidence was the checked-in synthetic fixture and its
  preserved copy from the previous partial smoke.

The public source search performed during diagnosis did not identify an
authoritative project matching ZTH's expected verified-YAML fields. No package
or repository was installed or cloned because doing so without an approved
source and confirmed CLI contract would risk testing the wrong tool.

### Downstream chain

- Genuine LLM-probe output: not produced.
- ZTH preflight import: not run.
- Preflight capability manifest: not produced.
- Operator planner: not run.
- Gate status: unavailable.
- Audition: not run.
- Synthetic fixture substitution: not performed.

### Validation

- Focused planner tests: 11 passed.
- Full `local_harness/tests` suite: 457 passed.
- Tracked Markdown link check: 64 files checked, no missing targets.
- Public-surface privacy check: passed.
- Boundary-language check: passed.
- `git diff --check`: passed.
- Importer, planner, and audition-runner `--help` checks: passed.
- A separate grep of preflight-smoke reports, the roadmap, and the report index
  found no private RFC1918 address, username, absolute home path, expanded
  endpoint URL, or endpoint-variable assignment containing a URL.

The repository-health privacy check excludes durable reports by design. The
separate report-specific grep was therefore required before committing this
summary.

## Blocker

The repository documents the expected LLM-probe verified-YAML shape but does
not identify the upstream source, installation procedure, executable name, or
endpoint-configuration flags for the LLM-probe implementation that produces
that shape.

Without that contract, generating a file that merely resembles
`verified/<provider>.yaml` would not constitute genuine LLM-probe evidence.

## Retry Condition

An authorized operator must provide one of:

1. an existing genuine `verified/<provider>.yaml` generated against this
   endpoint; or
2. the approved LLM-probe repository/package source plus its documented
   installation and local OpenAI-compatible endpoint command.

After the tool is available, retry in this order:

```bash
command -v <approved-llm-probe-executable>
<approved-llm-probe-executable> --help
```

Then run the documented probe command using
`"$ICM_ROUTER_BASE_URL"` and `"$ICM_ROUTER_MODEL"`, writing only to:

```text
.work/llm_probe_real_smoke_2026-06-21/
```

Do not proceed to import until a genuine file exists under:

```text
.work/llm_probe_real_smoke_2026-06-21/verified/<provider>.yaml
```

At that point, resume with the importer, inspect the generated manifest, run
the planner, and attempt the unwaived audition only if the real manifest
permits it.

## Safety Boundaries

- No model was promoted.
- No model was ranked.
- No model was routed.
- No model was assigned or approved for a production role.
- No upload occurred.
- No `.work` cleanup or deletion occurred.
- No endpoint lifecycle action occurred.
- No synthetic output was represented as genuine evidence.
- No waiver was used.
- Passing endpoint discovery is evidence, not authority.

## Historical Follow-up

1. Add or privately provide an authoritative producer source and exact local
   endpoint invocation contract.
2. Re-run this packet from genuine verified output without changing the ZTH
   importer, planner, or gate semantics.

## Resolution Note

The implementation blocker described above was addressed later by the
ZTH-owned `local_harness/llm_probe_smoke_probe.py` producer and
[`LLM_PROBE_PRODUCER_CONTRACT.md`](../../LLM_PROBE_PRODUCER_CONTRACT.md).

That producer is not the missing external upstream tool. It establishes a
project-owned, versioned way to generate the verified-YAML input shape from an
operator-supplied endpoint. This historical smoke remains blocked as recorded;
the first historical follow-up is superseded by the ZTH producer contract. A
new live run is still required before the roadmap's real endpoint smoke item
can be marked complete.
