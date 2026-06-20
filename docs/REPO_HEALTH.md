# Repository Health Checklist

Start here: [`README.md`](../README.md) ->
[`docs/README.md`](README.md).

Use this checklist before opening a PR, sharing a branch, publishing a report,
or tagging a release. Run commands from the repository root and review every
match.

## 1. Inspect the Working Tree

```bash
git status --short
git diff --stat
git diff
git diff --cached
git diff --check
```

Confirm that every changed and untracked file is intentional, generated or
private files are not staged, and unrelated user changes remain untouched.

## 2. Check Tracked Files for Private Material

Use tracked-file-safe checks:

```bash
git grep -nI -E '(/h[o]me/[[:alnum:]_.-]+|/Users/[[:alnum:]_.-]+|[A-Za-z]:\\Users\\[[:alnum:]_.-]+)' -- . || true
git grep -nI -E '(10[.][0-9]{1,3}[.][0-9]{1,3}[.][0-9]{1,3}|172[.](1[6-9]|2[0-9]|3[01])[.][0-9]{1,3}[.][0-9]{1,3}|192[.]168[.][0-9]{1,3}[.][0-9]{1,3})' -- . ':!local_harness/tests/**' || true
git grep -nI -E '(sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|BEGIN ([A-Z]+ )?PRIVATE KEY)' -- . || true
git ls-files | grep -E '(^|/)(__pycache__|[.]pytest_cache)(/|$)|[.]py[co]$' || true
```

Review legitimate matches as well as suspicious ones. Public docs, examples,
operator configuration, and reports should use placeholders such as
`<LAN_HOST>` rather than real internal addresses.

Do not replace these checks with a broad recursive grep over the repository.
Routine recursive scans can traverse ignored private `.work/`, `outputs/`,
`sources/`, exports, caches, and logs, exposing their contents in terminal or
CI output. Inspect ignored/generated evidence separately only when it is
intentionally being selected for publication.

See [`SANITIZATION_NOTES.md`](SANITIZATION_NOTES.md) for the full policy.

## 3. Check Relative Markdown Links

No dedicated Markdown link-check script is currently tracked. Use this
standard-library check for local relative targets:

```bash
python3 - <<'PY'
import re
import subprocess
from pathlib import Path

files = [
    Path(path)
    for path in subprocess.check_output(
        ["git", "ls-files", "*.md"],
        text=True,
    ).splitlines()
]
link_re = re.compile(r"(?<!!)\[[^\]\n]+\]\(([^)\n]+)\)")
fence_re = re.compile(r"^\s*```")
missing = []

for source in files:
    in_fence = False
    for line in source.read_text(encoding="utf-8").splitlines():
        if fence_re.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for raw_target in link_re.findall(line):
            target = raw_target.split("#", 1)[0]
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            if not (source.parent / target).resolve().exists():
                missing.append((source, raw_target))

for source, target in missing:
    print(f"MISSING {source}: {target}")
raise SystemExit(1 if missing else 0)
PY
```

This checks local file targets, not external URLs or Markdown anchors.
Untracked Markdown files must be checked separately or staged before relying
on `git ls-files`.

## 4. Run Relevant Verification

Choose checks proportionate to the changed files. Lightweight checks include:

```bash
bash -n scripts/run_context_distiller_head.sh
python3 -m py_compile local_harness/icm_call.py
python3 local_harness/report_distiller_metrics.py \
  --runs-dir examples \
  --limit 3
```

For Python changes, run focused tests and the relevant regression subset:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider \
  local_harness/tests/<focused_test_file>.py
```

For docs-only changes, run `git diff --check`, the relative-link check, the
tracked-file sanitization checks, and any smoke command whose documented
behavior changed.

An endpoint smoke test is optional and should run only when an authorized
OpenAI-compatible endpoint is already configured. Connectivity evidence does
not establish production readiness or model suitability.

## 5. Review Reports and Generated Evidence

Before committing a report:

- follow [`reports/README.md`](reports/README.md);
- preserve only durable, sanitized evidence;
- keep routine `.work/` and `outputs/` material disposable or private;
- confirm the report does not accept context, promote or assign a model,
  authorize lifecycle movement, or establish production readiness.

## 6. Final Pre-Share / Pre-PR Review

```bash
git diff --check
git status --short
```

Confirm:

- only intentional files will be shared;
- relevant tests or smoke checks passed;
- new relative Markdown links resolve;
- private paths, endpoint hosts, credentials, and source material are absent;
- ignored/generated evidence was reviewed separately if being published;
- human-supervised and evidence-only boundaries remain explicit;
- humans made publication, lifecycle, acceptance, and follow-up decisions.
