You are evaluating a model audition case.

Return JSON only. Do not include Markdown fences.

Task:
Classify the input into exactly one label.

Allowed labels are listed in metadata.

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
