You are evaluating a model audition case.

Return JSON only. Do not include Markdown fences.

Task:
Analyze the coding issue and produce a small patch plan. Do not write a full application.

Case ID:
{{case_id}}

Input:
{{input}}

Metadata:
{{metadata_json}}

Return:
{
  "diagnosis": "short diagnosis",
  "patch_summary": "short patch summary",
  "risk": "low|medium|high"
}
