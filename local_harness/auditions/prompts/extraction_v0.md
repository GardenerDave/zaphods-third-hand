You are evaluating a model audition case.

Return JSON only. Do not include Markdown fences.

Task:
Extract grounded signals from the input. Do not infer unsupported facts.

Case ID:
{{case_id}}

Input:
{{input}}

Metadata:
{{metadata_json}}

Return:
{
  "signals": [
    {
      "type": "project|tool|hardware|constraint|preference|risk",
      "text": "verbatim or near-verbatim grounded signal"
    }
  ]
}
