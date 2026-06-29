# LARQL Rule Registry Status

Registry id: `larql_rule_registry.v0`

## Lifecycle status

| Rule id | Status | Current step | Next step | Transport repair required | Failed probe preserved | Closeout |
| --- | --- | --- | --- | --- | --- | --- |
| absence_of_evidence_file_authority_v0 | passed | closeout_recorded | document_absence_of_evidence_json_model_context_pass_closeout | false | false | [link](docs/reports/affordance_larql/ABSENCE_OF_EVIDENCE_JSON_MODEL_CONTEXT_PASS_CLOSEOUT_2026-06-28.md) |
| unsupported_certainty_scope_claim_v0 | passed | closeout_recorded | record_unsupported_certainty_json_model_context_probe_pass | false | false | [link](docs/reports/affordance_larql/UNSUPPORTED_CERTAINTY_JSON_MODEL_CONTEXT_PASS_CLOSEOUT_2026-06-29.md) |
| unsupported_file_target_authority_v0 | passed_after_transport_repair | closeout_recorded | document_unsupported_file_target_authority_json_model_context_pass_closeout | true | true | [link](docs/reports/affordance_larql/UNSUPPORTED_FILE_TARGET_AUTHORITY_JSON_MODEL_CONTEXT_PASS_CLOSEOUT_2026-06-29.md) |

## Notes

- The registry is model-free metadata.
- It summarizes the completed hand-built rule trials.
- The unsupported-file-target authority entry records that the first probe was preserved and a transport repair was required.
- The unsupported-file-target authority entry includes `failed_probe_preserved: true` and `transport_repair_required: true`.
- It does not add a new rule or authorize runtime modification.

## Next machinery step

Implement a one-command evidence packet collector.

## Checks

- `registry_docs_closeout_links_exist`: `True`
- `registry_has_all_required_entries`: `True`
- `registry_has_required_rule_ids`: `True`
- `registry_has_three_rules`: `True`
- `registry_has_unique_rule_ids`: `True`
- `registry_has_valid_json_contracts`: `True`
