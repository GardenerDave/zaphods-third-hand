# Operation-membership lexical counterbalance probe design

This is a fresh exploratory operation-only probe for the Qwen3 1.7B-labeled /
2,031,739,904-operative supplier. It follows the additive projection
interpretation correction and does not rerun or alter prior inference.

The completed projected operation arm was all TRUE. It also confounded
membership with operation-token identity: inspect/update were always members,
while archive/delete were always non-members. This design uses inspect, update,
archive, and delete twice as members and twice as non-members.

Sixteen tasks form eight matched pairs. Each pair has the same requested token,
constant two-item allowed-set length, and identical projected prompt shape; the
membership state changes through the allowed set. Each operation token occurs
twice in each expected branch and exactly eight times in allowed sets overall.

Prompts expose only allowed operations and the requested operation. No target,
distractor, scope, authority, factor, expected label, or worked boolean is
present. The output is the existing structure-only `operation_allowed` boolean
schema. Execution is 16 calls, with no teacher, retry, escalation, or
adaptation.
