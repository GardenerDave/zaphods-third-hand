# Example Distiller Command

Try the sample metrics report without a model:

```bash
python3 local_harness/report_distiller_metrics.py --runs-dir examples --limit 3
```

Configure the model endpoint:

```bash
export ZTH_BASE_URL="http://<LLAMA_CPP_BASE_URL>/v1"
export ZTH_MODEL="<MODEL_NAME>"
```

Run compact plus chunked mode:

```bash
cd <REPO_ROOT>/zaphods-third-hand
./scripts/run_context_distiller.sh <SOURCE_ID> <SOURCE_FILE> <SHORT_TITLE>
```

For a slow model server or a quick smoke test, lower output budgets first:

```bash
export ZTH_DISTILLER_CHUNK_MAX_TOKENS="600"
export ZTH_DISTILLER_SESSION_MAX_TOKENS="900"
export ZTH_DISTILLER_PATCH_MAX_TOKENS="700"
export ZTH_DISTILLER_TIMEOUT="600"
```

See `docs/CONTEXT_DISTILLER_WORKFLOW.md` for smoke, normal compact, and chunked profile guidance.
For manifest-driven focused passes, see the manifest addendum in that document.

Review the generated files under:

```text
outputs/sessions/
outputs/review_patches/
outputs/run_records/
```
