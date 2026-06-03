# Example Distiller Command

Configure the model endpoint:

```bash
export ZTH_BASE_URL="http://<LLAMA_CPP_BASE_URL>/v1"
export ZTH_MODEL="<MODEL_NAME>"
```

Run compact plus chunked mode:

```bash
cd <REPO_ROOT>/zaphods-third-hand
./scripts/run_context_distiller_head.sh <SOURCE_ID> <SOURCE_FILE> <SHORT_TITLE> --compact --chunked
```

Review the generated files under:

```text
outputs/sessions/
outputs/review_patches/
outputs/run_records/
```
