You are evaluating a model audition case.

Return JSON only. Do not include Markdown fences.

Task:
Classify the input into exactly one label.

Allowed labels are listed in metadata.

Label meanings:
- local_model_ops: local inference runtime, endpoints, timeouts, model serving, throughput, context limits, llama.cpp operation.
- repo_code: repository source code, tests, docs, GitHub workflow, implementation patches.
- hardware: physical machines, servers, cables, GPUs, JBODs, power, compatibility.
- personal_memory: prior conversation context, remembered project decisions, user-specific history, or “what did we use last time” questions.

Case ID:
{{case_id}}

Input:
{{input}}

Metadata:
{{metadata_json}}

Return:
{
  "label": "one allowed label",
  "confidence": 0.0,
  "rationale": "short rationale"
}
