# Sanitization Report

Source archive: original uploaded project ZIP

Original archive characteristics observed during inspection:

- Total ZIP entries: 13,241
- Uncompressed size: approximately 531.5 MB
- Contained large dependency/vendor content, including Electron and `node_modules`.
- Contained `.git` history and nested project ZIP archives.
- Contained raw source/export folders and local agent run artifacts.

## Whitelist strategy

The sanitized deliverable uses a positive whitelist. Only workflow docs, prompt templates, and lightweight workflow utilities were copied. Everything else was excluded by default.

## Included files

- `ICM_Workflow_Optimization_Handoff/03_workflows/LOCAL_AGENT_ORCHESTRATION_WORKFLOW.md`
- `ICM_Workflow_Optimization_Handoff/03_workflows/CONVERSATION_TO_CONTEXT_WORKFLOW.md`
- `ICM_Workflow_Optimization_Handoff/03_workflows/SHARED_LINK_SNAPSHOT_WORKFLOW.md`
- `ICM_Workflow_Optimization_Handoff/03_workflows/DEV_AGENT_WORKFLOW.md`
- `ICM_Workflow_Optimization_Handoff/03_workflows/CONTEXT_DISTILLER_WORKFLOW.md`
- `ICM_Workflow_Optimization_Handoff/08_import_tools/prompts/ICM_EXTRACTION_PROMPT.md`
- `ICM_Workflow_Optimization_Handoff/08_import_tools/prompts/LOCAL_AGENT_TASK_PROMPT.md`
- `ICM_Workflow_Optimization_Handoff/08_import_tools/prompts/LOCAL_AGENT_REPORT_TEMPLATE.md`
- `ICM_Workflow_Optimization_Handoff/08_import_tools/prompts/LOCAL_AGENT_RESOURCE_REPORT.md`
- `ICM_Workflow_Optimization_Handoff/README.md`
- `ICM_Workflow_Optimization_Handoff/10_agent_runs/README.md`
- `ICM_Workflow_Optimization_Handoff/XX_backend/tests/test_validate_agent_run.py`
- `ICM_Workflow_Optimization_Handoff/XX_backend/validate_agent_run.py`
- `ICM_Workflow_Optimization_Handoff/XX_backend/README.md`
- `ICM_Workflow_Optimization_Handoff/local_harness/icm_call.py`

## Excluded file counts by category

- agent_run_artifacts: 192
- app_source_or_build: 147
- archives_nested_zips: 64
- git_history: 6598
- node_modules: 4720
- other: 84
- raw_sources_exports: 64
- session_summaries: 43

## Automated replacements applied

- Personal names and author lines → redacted placeholders.
- Email addresses → `[REDACTED_EMAIL]`.
- Private LAN IPs and LAN URLs → `<LAN_HOST>` placeholders while preserving ports where possible.
- Local Windows/macOS/Linux paths → generic user/path placeholders.
- Product names were generalized to `ProjectName` / `InternalCodename` where practical.
- Obvious key/token/password assignment patterns were redacted.

## Residual-risk note

This was sanitized by static inspection and regex-based transformation without executing project code. I found no reason to include the original full archive for an outside AI rig; the sanitized package is the safer handoff artifact.
