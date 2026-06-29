# LARQL Lifecycle Status

Registry id: `larql_rule_registry.v0`

## Lifecycle status table

| Rule id | Status | Current step | Allowed next step | Closeout exists | Installed artifact exists | Transport repair required | Failed probe preserved |
| --- | --- | --- | --- | --- | --- | --- | --- |
| absence_of_evidence_file_authority_v0 | passed | closeout_recorded | document_absence_of_evidence_json_model_context_pass_closeout | true | true | false | false |
| unsupported_certainty_scope_claim_v0 | passed | closeout_recorded | record_unsupported_certainty_json_model_context_probe_pass | true | true | false | false |
| unsupported_file_target_authority_v0 | passed_after_transport_repair | closeout_recorded | document_unsupported_file_target_authority_json_model_context_pass_closeout | true | true | true | true |

## Evidence packet status table

| Rule id | Packet present | Evidence items | Missing items |
| --- | --- | --- | --- |
| absence_of_evidence_file_authority_v0 | false |  |  |
| unsupported_certainty_scope_claim_v0 | false |  |  |
| unsupported_file_target_authority_v0 | true | 11 | 0 |

## Held / not-authorized reminder

- no model call is made by this driver
- no training data is written
- no dataset artifact is written
- no durable memory is written
- no candidate is promoted
- no model weights are mutated
- no runtime rules are installed or modified
- no automatic failure-to-curriculum capture is performed

## Next machinery step

Package a reusable status/navigation cleanup layer on top of the registry and packet outputs, without adding another hand-built LARQL rule.
