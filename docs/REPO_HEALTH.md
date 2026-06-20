# Repository Health Checklist

Start here: [`README.md`](../README.md) ->
[`docs/README.md`](README.md).

Use this checklist before opening a PR, sharing a branch, publishing a report,
or tagging a release. Run commands from the repository root and review every
match; clean command output is evidence, not a substitute for human review.

## 1. Inspect the Working Tree

```bash
git status --short
git diff --stat
git diff
git diff --cached
git diff --check
```

Confirm:

- every changed and untracked file is intentional;
- generated/private files are not staged;
- unrelated user changes are preserved;
- the diff contains no whitespace errors.

## 2. Check Tracked Files for Private Material

Use tracked-file-safe checks:

```bash
git grep -nI -E '(/h[o]me/[[:alnum:]_.-]+|/Users/[[:alnum:]_.-]+|[A-Za-z]:\\Users\\[[:alnum:]_.-]+)' -- . || true
git grep -nI -E '(10[.][0-9]{1,3}[.][0-9]{1,3}[.][0-9]{1,3}|172[.](1[6-9]|2[0-9]|3[01])[.][0-9]{1,3}[.][0-9]{1,3}|192[.]168[.][0-9]{1,3}[.][0-9]{1,3})' -- . ':!local_harness/tests/**' || true
git grep -nI -E '(sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|BEGIN ([A-Z]+ )?PRIVATE KEY)' -- . || true
git ls-files | grep -E '(^|/)(__pycache__|[.]pytest_cache)(/|$)|[.]py[co]$' || true
```

Review legitimate matches as well as suspicious ones. Literal RFC1918 values
may exist as inert test data, but public docs, examples, operator configs, and
reports should use `<LAN_HOST>`.

Do not replace these commands with a broad recursive grep over the repository.
Routine recursive scans can traverse ignored `.work/`, `outputs/`, `sources/`,
private exports, caches, and logs, exposing private material in terminal or CI
output. Inspect an ignored/generated directory separately only when its
contents are intentionally being selected for publication.

See [`SANITIZATION_NOTES.md`](SANITIZATION_NOTES.md) for the complete policy.

## 3. Check Markdown Links

No dedicated Markdown link-check script is currently tracked. For local
relative links, run this Python standard-library check:

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

This checks local targets only. It does not validate external URLs or Markdown
anchor names. Include newly created untracked Markdown files manually or stage
them before relying on `git ls-files`.

## 4. Run Relevant Verification

Choose checks proportionate to the changed files. Useful lightweight checks
include:

```bash
bash -n scripts/run_context_distiller_head.sh
python3 -m py_compile local_harness/icm_call.py
python3 local_harness/report_distiller_metrics.py \
  --runs-dir examples \
  --limit 3
```

For Python changes, run the focused pytest file first, then the relevant
regression subset:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider \
  local_harness/tests/<focused_test_file>.py
```

For docs-only changes, run `git diff --check`, the link check above, the
tracked-file sanitization checks, and any smoke command whose documented
behavior changed.

Endpoint smoke tests are optional and should run only when an authorized
OpenAI-compatible endpoint is already configured:

```bash
python3 local_harness/icm_call.py handoff \
  --api openai-chat \
  --base-url "$ZTH_BASE_URL" \
  --model "$ZTH_MODEL" \
  --max-tokens 16 \
  --timeout 60 \
  --final-only \
  "Reply with exactly: ok"
```

Endpoint connectivity does not establish production readiness or model
suitability.

## 5. Review Reports and Generated Evidence

Before committing a report:

- follow [`reports/README.md`](reports/README.md);
- preserve only durable, sanitized evidence;
- keep routine `.work/` and `outputs/` material disposable/private;
- confirm the report does not accept context, promote or assign a model,
  authorize lifecycle movement, or claim production readiness.

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
- ignored/generated evidence was reviewed separately if it is being published;
- human-supervised and evidence-only boundaries remain explicit;
- publication, lifecycle, and acceptance decisions were made by a human.
