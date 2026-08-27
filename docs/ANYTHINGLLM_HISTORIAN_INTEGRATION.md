# AnythingLLM + Historian shared-memory integration

Historian remains the read-only source of project memory.
AnythingLLM is the operator cockpit and agent runtime.

The integration uses two local custom agent skills:

- `historian_evidence`: fetches bounded canonical Historian evidence for a question.
- `historian_query`: asks Historian's grounded Qwen reasoner for an answer.

Both skills talk only to the loopback Historian service:

- `GET  http://127.0.0.1:8765/v1/health`
- `POST http://127.0.0.1:8765/v1/evidence`
- `POST http://127.0.0.1:8765/v1/query`

AnythingLLM is configured to reason over the evidence it receives.
Historian does not receive write authority from AnythingLLM.

The local skill sources live in:

- `integrations/anythingllm/skills/historian_evidence/`
- `integrations/anythingllm/skills/historian_query/`

Use `scripts/sync_anythingllm_skills.sh` to copy them into the Desktop storage area:

```bash
scripts/sync_anythingllm_skills.sh ~/.config/anythingllm-desktop/storage/plugins
```

The Desktop storage location on Linux is:

- `~/.config/anythingllm-desktop/storage/`

Historian evidence stays authoritative in Historian; AnythingLLM workspace memory is not canonical project history.
