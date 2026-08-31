# Dogfood Round 1/2 Baseline Preservation and Hardening Report

Date: 2026-08-31

This report preserves the empirical baseline from Dogfood Round 1 and Round 2 and records the hardening work that followed. The preserved raw run directories under `.work/` remain unchanged.

## Preservation Scope

The following raw run directories are treated as immutable baseline evidence:

- `.work/dogfood_round1/task1/20260831T030000Z`
- `.work/dogfood_round1/task2/20260831T031500Z`
- `.work/dogfood_round1/task3/20260831T033000Z`
- `.work/dogfood_round2/task1/20260831T050000Z`
- `.work/dogfood_round2/task1b/20260831T053000Z`
- `.work/dogfood_round2/task2/20260831T050500Z`
- `.work/dogfood_round2/task3/20260831T051000Z`
- `.work/dogfood_round2/task3b/20260831T053500Z`

## Round 1 Reconstruction

Round 1 did not project repository evidence into the worker prompt. The worker received orchestration/planning-style contracts instead of a bounded repository-observation contract.

### Round 1 Task Outcomes

| Task | Result | Primary failure class |
| --- | --- | --- |
| Task 1 | Validation passed, but output was a routing/planning object rather than repository findings | Wrong execution contract |
| Task 2 | Validation passed, but output was a docs-planning object rather than repository findings | Wrong execution contract |
| Task 3 | Raw output was malformed JSON and failed validation | Model output failure |

### Round 1 Evidence Interpretation

- The worker did not receive the repository content needed for the requested inspection tasks.
- The projected contract asked for orchestration/planning artifacts, not file-grounded observations.
- Round 1 therefore exposed a contract/context mismatch, not just weak model behavior.

## Round 2 Reconstruction

Round 2 introduced a bounded evidence-projection lane. That fixed the major Round 1 contract problem, but the first packets were still oversized and the output schema was still too weak for robust observation work.

### Round 2 Attempt Classes

| Attempt | Task | Result | Primary failure class |
| --- | --- | --- | --- |
| task1/20260831T050000Z | Roadmap-to-implementation consistency | Transport failed with HTTP 400 | Context overflow |
| task2/20260831T050500Z | Newcomer documentation navigation | Transport succeeded, validation failed | Schema mismatch |
| task3/20260831T051000Z | Provenance/evidence completeness | Transport failed with HTTP 400 | Context overflow |
| task1b/20260831T053000Z | Roadmap-to-implementation consistency | Transport succeeded, validation failed | Schema mismatch / grounding quality |
| task3b/20260831T053500Z | Provenance/evidence completeness | Transport succeeded, validation failed | Schema mismatch / grounding quality |

### Round 2 Failure Details

- `task1/20260831T050000Z` and `task3/20260831T051000Z` exceeded the local endpoint context window before the model could answer. The local endpoint returned HTTP 400 with `n_prompt_tokens: 8440` and `n_ctx: 8192`.
- `task2/20260831T050500Z` returned a valid JSON object but the validator was still expecting the earlier allowed/held-target contract, so it failed mechanical validation.
- `task1b/20260831T053000Z` and `task3b/20260831T053500Z` used the correct observation lane, but the returned objects still failed the observation validator.

### Round 2 Evidence Preservation Notes

- Failed calls were preserved as failed transport evidence where applicable.
- Raw worker outputs were preserved for the successful transports.
- The new evidence projection packet and prompt projection summary were written for each evidence-mode run.

## Hash Inventory

The following SHA-256 values identify key preserved artifacts. Paths are relative to the repository root.

### Round 1

| Artifact | SHA-256 |
| --- | --- |
| `.work/dogfood_round1/task1/20260831T030000Z/local_model_call.json` | `1b87ac437db0b054dc2a17a8d3464c5dbf32fbdd58ba00c5ac8a3146f0f706de` |
| `.work/dogfood_round1/task1/20260831T030000Z/raw_model_output.txt` | `8c0706b31d21db71cd16230989d0c0142f7e68c488c67ed44eace8dc8551445a` |
| `.work/dogfood_round1/task1/20260831T030000Z/output_validation.json` | `e96097fd8695f9f8b405a24383e8ded3cf3e7d15a9f403ed9035b09026a0fba4` |
| `.work/dogfood_round1/task2/20260831T031500Z/local_model_call.json` | `31c057bb75b0ba4b29f53db97e03a706ace74dacc87f7469fb7dbbb8a9d8ad35` |
| `.work/dogfood_round1/task2/20260831T031500Z/raw_model_output.txt` | `9b7ed3717e7eb4ec57fc8f254d8571e826b2d4d5c7eeec054015499438e41feb` |
| `.work/dogfood_round1/task2/20260831T031500Z/output_validation.json` | `4cd971c0508017350b079da2ecf1e6644476d73dfa691d16a552c0c8f4975799` |
| `.work/dogfood_round1/task3/20260831T033000Z/local_model_call.json` | `84801da47d43f372b4d45f5ccdb954b1fcb99c598df2571506f6adf5a25ceb6a` |
| `.work/dogfood_round1/task3/20260831T033000Z/raw_model_output.txt` | `f7ec695a8a69aff12156ff125745c6122255629ec4081e8d013d2f9eadbd386c` |
| `.work/dogfood_round1/task3/20260831T033000Z/output_validation.json` | `770f10f131837c3349c48246a5f9e8e37f88b71ee8f340f2df3ce2770cde3acf` |

### Round 2

| Artifact | SHA-256 |
| --- | --- |
| `.work/dogfood_round2/task1/20260831T050000Z/local_model_call.json` | `fab37ca1bf472f2ec4ec15955ef48557d33745bef19ddde6e5728a8d2056c6bf` |
| `.work/dogfood_round2/task1/20260831T050000Z/raw_model_output.txt` | `0bd57f5c6d20e6809d6ae9561044cba6989cbbb0da59d1f74c09e7bed71a8cf2` |
| `.work/dogfood_round2/task1/20260831T050000Z/evidence_projection.json` | `c1a4e4ca8323c1a26f0d664f9ab67e7a3a88949fad14163f699f884a8b89bc6d` |
| `.work/dogfood_round2/task1/20260831T050000Z/prompt_projection_summary.json` | `5dcc338b7a9514b1a0997a049388ed94490e3daecdcc2f54bc27c18ba3a6999b` |
| `.work/dogfood_round2/task1b/20260831T053000Z/local_model_call.json` | `a6d23223d54cb91d8d8c3e69ea6192a8dd9b05720549afe350adb011910026fc` |
| `.work/dogfood_round2/task1b/20260831T053000Z/raw_model_output.txt` | `a36dac980453a3298245d7f1a1f52be1a43db21f2fb5208fde1e696e9a5a647d` |
| `.work/dogfood_round2/task1b/20260831T053000Z/output_validation.json` | `118ca461aca3df80346fd53beeaa00b089f4eaef1cd1dfd1be4e7c7e64e38562` |
| `.work/dogfood_round2/task1b/20260831T053000Z/evidence_projection.json` | `28101673402cf896f25178e7d6d8f385efd8ec023c87fa363e2e642e537286ff` |
| `.work/dogfood_round2/task1b/20260831T053000Z/prompt_projection_summary.json` | `e95500e770fb1874f7d224c3a23efc1636f559d99ce5c24c96adbd459b9588d2` |
| `.work/dogfood_round2/task2/20260831T050500Z/local_model_call.json` | `8ede58133ef2ceb4d33258fcb492098a1f91c683c93c1683545f23c615af567f` |
| `.work/dogfood_round2/task2/20260831T050500Z/raw_model_output.txt` | `cda29b0ad0e195b30874eed2d0374a40cb4065dd872101be7a7c28c867116b80` |
| `.work/dogfood_round2/task2/20260831T050500Z/output_validation.json` | `36ac477137097847deb27898130ae7b1dc8ebaf5bb5c06100c2000d0f504e32a` |
| `.work/dogfood_round2/task2/20260831T050500Z/evidence_projection.json` | `a1138349d23ecbd0d7eecf840fbca5021ed0bacfa5b89425d8c5d9dac49ba26d` |
| `.work/dogfood_round2/task2/20260831T050500Z/prompt_projection_summary.json` | `5dcc338b7a9514b1a0997a049388ed94490e3daecdcc2f54bc27c18ba3a6999b` |
| `.work/dogfood_round2/task3/20260831T051000Z/local_model_call.failed.json` | `769598c66a5c8077a6b00892c7a2c897948800c8b7ce9c4f3b28c4fcc0a1b5e3` |
| `.work/dogfood_round2/task3/20260831T051000Z/local_model_response.failed.json` | `9cf3e842d7c59cb0ee2950cce78a7b6221c346248017b298dc21a5280b792a7c` |
| `.work/dogfood_round2/task3/20260831T051000Z/evidence_projection.json` | `3fce9bc961e6b4414df0c0d740927051eba7b55a92f797351a03368d538fbe71` |
| `.work/dogfood_round2/task3/20260831T051000Z/prompt_projection_summary.json` | `1e337e27e5237571738eb808c533c4e0e40ae945b817d883b8b28a988b7c5a45` |
| `.work/dogfood_round2/task3b/20260831T053500Z/local_model_call.json` | `2f74b6f4a7e57c5a7cf8aff906ca1f5353db984c58b5195dca4b674551528b82` |
| `.work/dogfood_round2/task3b/20260831T053500Z/raw_model_output.txt` | `3f42ca21918ca3a7c8d8c1d2ac56d285b6d8719c8b7f33311bc8ea8fe2f6fee0` |
| `.work/dogfood_round2/task3b/20260831T053500Z/output_validation.json` | `188263437ef86cc07d009ed1b9d3a69a1f9f5f114adae12ea4f227e17aeb36df` |
| `.work/dogfood_round2/task3b/20260831T053500Z/evidence_projection.json` | `a421771ef05424238f3c619c5800c5c11b67183d71fbe670e18dedb456671e6b` |
| `.work/dogfood_round2/task3b/20260831T053500Z/prompt_projection_summary.json` | `4728619da084d25840a286fe2866a9f4444b70fe7e026f464c5e3a40e8bf80c5` |

## Commit Record

- Preservation/hardening work is tracked in commit `1f88bb8502dddec3659ee793f633c83fa609f6b7`.

## Interpretation

Round 1 showed the worker was not being given the right evidence or contract.

Round 2 showed the bounded evidence lane works, but the initial packets can still overflow context and the worker still needs a mechanically explicit observation schema plus tighter packet budgeting.

This report is a preservation artifact. It does not accept or promote any model output.
