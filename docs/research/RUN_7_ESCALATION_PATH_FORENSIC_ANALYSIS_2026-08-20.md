# Run 7 Escalation-Path Forensic Analysis

Status: model-free, review-only diagnostic; raw artifacts unchanged; no policy
or routing change.

## Scope and bindings

This analysis compares the paired durable artifacts for
`run7-scope-001`, `run7-scope-006`, and `run7-scope-019` in:

```text
.work/run7_scope_escalation/run_20260820T045113Z/
```

The authoritative Run 7 execution commit was
`08298d87147f67ad9ad2624c376adb8790cf1f75`; the reviewed documentation commit
was `16ae4b4484c768df3b6d62148d6f00bfe40dfacb`.

| Binding | SHA256 |
|---|---|
| Run 7 driver | `f1bdac815109a2dce473529ae14ddc24d60b048b74f3268e25fa6f9d9b1ad547` |
| Run 7 preregistration | `1c45ce7be83194d4adfb5cf1af6b04d90495712b6779956bc6f7691ac4055de6` |
| Run 7 fixture pack | `7b0f94b5301bba35a10165030b37313a8b5734f01c7a934d9e5ea9c25b800740` |
| Run 7 execution manifest | `ad8c9bee121efd0a1e683c393a7a4ba74cccefaa77f82e7350d3be71c224bd0f` |
| Run 7 aggregate | `c64d7ff2a5031f5151f3af44437b5142824af00e8fcb391e97376d5f9a07f3eb` |
| Run 7 selection | `edaa7e4f308cc22752e1732f53362807a9fe15c5db024c51dbb0a78464c3c48d` |
| Run 6 sequential driver used by escalation | `01683c0f4b4eb29669258e4313fc261a85edbc36bab68210db9a31c2c418dc1c` |
| Run 4A intervention harness | `a6125d4b9d32ca912da81fd0df316cd56eada60c825b02789b5496fd24590f88` |
| Shared capability loop/parser | `23b26115201d8cba17b9da659af72793654897803988e35e28210eba02af81be` |

Run 7 outcomes for the diagnostic tasks were:

| Task | Control | Local-first | Escalation | Final treatment |
|---|---|---|---|---|
| 001 | passed | failed | failed | failed |
| 006 | passed | failed | passed | passed |
| 019 | passed | failed | failed | failed |

## Artifact inventory

The following is the complete durable inventory for each task. Every listed
path was hashed read-only. The three `baseline_reference.json` files under
`control` and `local_first` are byte-identical per task; the escalation path
does not write a `baseline_reference.json` file, although its binding records
the baseline-summary digest.

### run7-scope-001

| Relative path | SHA256 |
|---|---|
| `candidates/run7-scope-001/baseline.prompt.txt` | `d4e72cb479dc160e69ad8b040e1c20a48e2e4ef910e05256698d5d8817c51a2e` |
| `candidates/run7-scope-001/baseline.raw.json` | `4547670041f0fe811f481f2b0fe1719f71a112e98f9f5a5ad61ccb984813621a` |
| `candidates/run7-scope-001/baseline.validation.json` | `d08420bac56277a9732b176facbc99e44c71aebfeeb0728f996c43dcf9314cb2` |
| `candidates/run7-scope-001/baseline_summary.json` | `dd1658abb0e9cafe01c61a3cd099fa309e64fdd67e090c9d4b9d272c509510d2` |
| `candidates/run7-scope-001/state.json` | `d6c487d45ec6886fe5245c7d36373c412584daf00a3a31eff016e5d59fb6326d` |
| `candidates/run7-scope-001/trajectory.jsonl` | `8d1231cf5aeeca1c38abe1818a2f224ac4926592f0e017bfaa5b05530951b97a` |
| `tasks/scope/run7-scope-001/control/arm_artifacts.json` | `5d04dec09acce08ac4854736a85037addb979271b294dfe1f2c38c1fc15cc6e6` |
| `tasks/scope/run7-scope-001/control/arm_binding.json` | `3a5c33b6307d4ea437de2b8b5d22aeaaba3003c130a69997821a6b5fd39127cb` |
| `tasks/scope/run7-scope-001/control/arm_summary.json` | `0089058ee2abbf73b99c1614654533be5f95a2b101422966bfd05aade037d123` |
| `tasks/scope/run7-scope-001/control/baseline_reference.json` | `da13082af63e25f31d155a44cb934a5015d8860bf170592a31f40d94dfa564e3` |
| `tasks/scope/run7-scope-001/control/external_teacher.prompt.txt` | `ce10aaf22414679e7d4507ec99c7cc6695ac455e08662ae1fd5365352463e47d` |
| `tasks/scope/run7-scope-001/control/external_teacher.raw.json` | `c8b86276738faa854d0dd6eeb095956fae06c8ce9a082194d3366718c637e48a` |
| `tasks/scope/run7-scope-001/control/trajectory.jsonl` | `93ff736223be7ed3295c9e298f56d88277ea680f06b8945f243964dbc8316d7b` |
| `tasks/scope/run7-scope-001/control/worker-retry.prompt.txt` | `81657b8d4c3402fcaf1a37b17c2af2c73d734b8ecb0b6323fd6fcdd700214643` |
| `tasks/scope/run7-scope-001/control/worker-retry.raw.json` | `3c06e46e1a1e14166350ebe7f63c7f1293169dc8065735a6494c0a77a1e3034a` |
| `tasks/scope/run7-scope-001/control/worker-retry.validation.json` | `be9153b41f3bc4f1e3c8358cdc64f5ec8035376f5fbfe07be1ccc2ddbcb3ddd3` |
| `tasks/scope/run7-scope-001/escalation/arm_artifacts.json` | `eded46f30f4e442f04cd29877cf7dea917c4a141be00aa363a438c3378a5fff4` |
| `tasks/scope/run7-scope-001/escalation/arm_binding.json` | `6df97a9f6540e003239fa4890d57409413db8615c0c7dc8d05fcb140157794f5` |
| `tasks/scope/run7-scope-001/escalation/arm_summary.json` | `2137146926f8ec25db1ab9c5b8699ec573650eb65d0c587ba901102101fa7a75` |
| `tasks/scope/run7-scope-001/escalation/external_teacher.prompt.txt` | `f4a7868f9ac0c88a210414f321876642cceae882fc9918f57850d8428793c7a7` |
| `tasks/scope/run7-scope-001/escalation/external_teacher.raw.json` | `e2699f395c928b66d936862ef0dcf317c9ff611418098ad4651874ea67a97baa` |
| `tasks/scope/run7-scope-001/escalation/trajectory.jsonl` | `7f91009881bbc59e903f31c877e13fd659eb9e25c3463b2346d998f54afcd6d3` |
| `tasks/scope/run7-scope-001/escalation/worker-retry.prompt.txt` | `10a3961675924f399d07493f0cb16d2e90e5bfe961a50c8453b57680f0b7cbe5` |
| `tasks/scope/run7-scope-001/escalation/worker-retry.raw.json` | `190cbeab5608ada11ed517e65e3e7ac4c22be2448089b42fc1edc90de733666f` |
| `tasks/scope/run7-scope-001/escalation/worker-retry.validation.json` | `bb04b2eb00fd5e022d7c8fd8d8a17ffadfe84cf462f70f2d054789a38200c8c5` |
| `tasks/scope/run7-scope-001/local_first/arm_artifacts.json` | `1bc1a71a859099693a2eaf4ade1b409a7845bd2230f2785adc84219b128dec64` |
| `tasks/scope/run7-scope-001/local_first/arm_binding.json` | `61658aa9a0a4e2aa950e8cd4bbc4c9f536feb070dde4e27e9b5565b03c9feb63` |
| `tasks/scope/run7-scope-001/local_first/arm_summary.json` | `cc8114c04b13f086be12b5443da233d6be0a729595711a2b29a62ffa0550464b` |
| `tasks/scope/run7-scope-001/local_first/baseline_reference.json` | `da13082af63e25f31d155a44cb934a5015d8860bf170592a31f40d94dfa564e3` |
| `tasks/scope/run7-scope-001/local_first/local_teacher.prompt.txt` | `e21556724b4a6f4b30e2a11b41649e3d574df9949d3c93aa556d955d2365e448` |
| `tasks/scope/run7-scope-001/local_first/local_teacher.raw.json` | `9fa5200b6eaff8c941dc2c847530fb71db5bd11ba9ca9a1ae530cd36603de1b1` |
| `tasks/scope/run7-scope-001/local_first/trajectory.jsonl` | `07331c0d16409e680a73eb63fd23505adb517e06f3c1770555ffef4d28762bc5` |
| `tasks/scope/run7-scope-001/local_first/worker-retry.prompt.txt` | `3f8aaff9c41cb6f4ab6f77c2a89c7389373065246ba84192a2ac4c65ceed0a99` |
| `tasks/scope/run7-scope-001/local_first/worker-retry.raw.json` | `a107761ddf389584a9714d726608cfdc43d62f10cb7b70bc1ae0ac746b8d667a` |
| `tasks/scope/run7-scope-001/local_first/worker-retry.validation.json` | `7202d57d9297516680c01f24a867301749ceaa349bdec3f341a39414a06ae720` |
| `tasks/scope-authority-boundary/run7-scope-001/scorecard.json` | `52ccc0872014718d97e6c477d27caf3946b3a0d1520bcc645a2027c0c3f7f662` |
| `tasks/scope-authority-boundary/run7-scope-001/treatment_summary.json` | `3047697b69c025629322b65d030576f7ae2b8afb071f4b2f52e8b7fc356ca1bb` |

### run7-scope-006

| Relative path | SHA256 |
|---|---|
| `candidates/run7-scope-006/baseline.prompt.txt` | `4a526405330c6e53d3737c0c6430eac7334637158e265d3f842789e380dc941b` |
| `candidates/run7-scope-006/baseline.raw.json` | `a6ab33b1d891a0c9e06f12553732213aba0583343f18bce019bb4c99ee0dc856` |
| `candidates/run7-scope-006/baseline.validation.json` | `066d0d858e94d80ef38580154b903fe7a82840c1a038a45e67106942127ebfaa` |
| `candidates/run7-scope-006/baseline_summary.json` | `6430d945c434f33773fee896f497ff0116339c1b2fe6d9e746d86c35c7207cb8` |
| `candidates/run7-scope-006/state.json` | `d6c487d45ec6886fe5245c7d36373c412584daf00a3a31eff016e5d59fb6326d` |
| `candidates/run7-scope-006/trajectory.jsonl` | `ae01759be49080e5b1c43c8157791a94862063b71b82a475b9df208a2e114085` |
| `tasks/scope/run7-scope-006/control/arm_artifacts.json` | `8c09a289ed822984a5ffcb5cbd2aa4794ce4d213eef211a14e21c30f85dbafb9` |
| `tasks/scope/run7-scope-006/control/arm_binding.json` | `812e65f8ccf9f24854d6c52863393521f88f5737f581de4d308b1b3f583aa3f1` |
| `tasks/scope/run7-scope-006/control/arm_summary.json` | `388e76e3a4d72ecb77402e9c64e7b7237a2794278bb48a9d89cee8a00a66e3cc` |
| `tasks/scope/run7-scope-006/control/baseline_reference.json` | `ecc65c15981d8e8bcc7159fe00c95b4953488f43fb76fca82130035d5ac941a9` |
| `tasks/scope/run7-scope-006/control/external_teacher.prompt.txt` | `b21808c8188937da319db1a6f51eb65358478862c627559654b978dd5f08a57e` |
| `tasks/scope/run7-scope-006/control/external_teacher.raw.json` | `2a8281023a79f0ba22b33690313b0660937d64272c3f7f71e5e5111eaaafbdeb` |
| `tasks/scope/run7-scope-006/control/trajectory.jsonl` | `c51b1d44a7b96a075f5051c18b8f9a18d563023feb3a1cea942c312ef2de76cd` |
| `tasks/scope/run7-scope-006/control/worker-retry.prompt.txt` | `dc7c2ddf9fc157093d6d5e21daf1f49a7acbc23dc5f70f5c606794c8d1d07d7a` |
| `tasks/scope/run7-scope-006/control/worker-retry.raw.json` | `d3c151ac3d741e0fb183662adbe2a3fea69437b8ede57f387afe6bfdfdcc177c` |
| `tasks/scope/run7-scope-006/control/worker-retry.validation.json` | `6a2b68249d251eb9044f98aa9f5edda6123806234c2d8994e48b39df2587b578` |
| `tasks/scope/run7-scope-006/escalation/arm_artifacts.json` | `85a77cf6eeee8e8d090622e06018a2f55d2680cc54d7dc0a3533a99f11ba9ed9` |
| `tasks/scope/run7-scope-006/escalation/arm_binding.json` | `03743bf6e4d0852d6a33c0f507406a1442c0653260e52ded4736b9b382d5ec63` |
| `tasks/scope/run7-scope-006/escalation/arm_summary.json` | `85640be659715149e8828ae3239fada7ffe0d86ee041ab4055a99fb62683978a` |
| `tasks/scope/run7-scope-006/escalation/external_teacher.prompt.txt` | `1937e9f2b82ac777cc6b2166b54af5b9e16f4881c37336db720c97d8540479e0` |
| `tasks/scope/run7-scope-006/escalation/external_teacher.raw.json` | `dc44a3d50e7439d23dfce9df683d0ea52f4506065955553164c57c9e01f0fcdf` |
| `tasks/scope/run7-scope-006/escalation/trajectory.jsonl` | `d41e85aea97fb6865293afe3370eabd284d996ff3e21c39ae4ea3ba422a13775` |
| `tasks/scope/run7-scope-006/escalation/worker-retry.prompt.txt` | `12e9dca58f8aa4eb91e731f650cbbdedb6789d07b5d241b861365cceae03dd0c` |
| `tasks/scope/run7-scope-006/escalation/worker-retry.raw.json` | `ab48acdc1d24a4ddffafe679093d468609c0a0b9258903985fadef09c770bd8a` |
| `tasks/scope/run7-scope-006/escalation/worker-retry.validation.json` | `86b57d52bd32f54d9a554d69a2311f9ec0b600815c29695e16f0ca725d053ee5` |
| `tasks/scope/run7-scope-006/local_first/arm_artifacts.json` | `4f50847197edd6f94d4baf934a4af2ae19a6af1736c3241693e690d7f20c4f5b` |
| `tasks/scope/run7-scope-006/local_first/arm_binding.json` | `b080b70cfe0e6161eea9901fd0360438656086b8379344f9261a712b07602cb` |
| `tasks/scope/run7-scope-006/local_first/arm_summary.json` | `7ddc39ec51cf1a115de7ec6b73b48efb3bbc93dddffa46b42b1dba1c01f751f2` |
| `tasks/scope/run7-scope-006/local_first/baseline_reference.json` | `ecc65c15981d8e8bcc7159fe00c95b4953488f43fb76fca82130035d5ac941a9` |
| `tasks/scope/run7-scope-006/local_first/local_teacher.prompt.txt` | `1fde1062ec31441a4b8e5899bf3f02898abc4a85bc3af6f60969adcba37318c6` |
| `tasks/scope/run7-scope-006/local_first/local_teacher.raw.json` | `6804af48dcf22d32b3738ad12eb9f652b043957113c68690e0b473e35af0fa4c` |
| `tasks/scope/run7-scope-006/local_first/trajectory.jsonl` | `ad795762d841a2284f509fb5dcc1b8714fd5806593840cf46eb51b9787d6efd7` |
| `tasks/scope/run7-scope-006/local_first/worker-retry.prompt.txt` | `e2415bdc090b8cc617740971f457169b8137b1f0ee84032436b37f3845ee6b86` |
| `tasks/scope/run7-scope-006/local_first/worker-retry.raw.json` | `59915ec192f1671707bd9b6769c9955eb782ef3454e367bcef979d080f950a01` |
| `tasks/scope/run7-scope-006/local_first/worker-retry.validation.json` | `627cd01ddc7328bd67399242f9f477e84c91fa400d3936438f9814a2eb298984` |
| `tasks/scope-authority-boundary/run7-scope-006/scorecard.json` | `8ac694e42e3fcf6cf00c7b9b2df3e4a1b43ca825a03605f9aff32b7872d8e0c2` |
| `tasks/scope-authority-boundary/run7-scope-006/treatment_summary.json` | `e3b7bbee7f5230b9418fad880a70b41df5bc9007b896e717a4e74a7a3f723af4` |

### run7-scope-019

| Relative path | SHA256 |
|---|---|
| `candidates/run7-scope-019/baseline.prompt.txt` | `9f80b80cf2bbc2ba43422f9a055418f43beaf019af2a06c1932d7f706dcdf243` |
| `candidates/run7-scope-019/baseline.raw.json` | `7315811bccc733c3c6798aa8b5c8d66bc4697d6b422553bdd140b221595840d4` |
| `candidates/run7-scope-019/baseline.validation.json` | `37cfbec014db76139d3498aa274bf55e357fc9415d114db1b06707a33ff8005c` |
| `candidates/run7-scope-019/baseline_summary.json` | `c38f4583c0f2dc7fc31cfa688520df14bab7bcda1e5362905526609a81ca761b` |
| `candidates/run7-scope-019/state.json` | `d6c487d45ec6886fe5245c7d36373c412584daf00a3a31eff016e5d59fb6326d` |
| `candidates/run7-scope-019/trajectory.jsonl` | `dd1601d3da788caefe836af8412ec839233098dbd9dd63a0cda72fe720eb9ac7` |
| `tasks/scope/run7-scope-019/control/arm_artifacts.json` | `e6d4f0a2d85c05efe70b5929830b127cf44b16b3c74b13d88e0ff55a1c408cbc` |
| `tasks/scope/run7-scope-019/control/arm_binding.json` | `7e405f3c1621a27c45d41eb869b6ed61dd09b01c5a82449c304b6a9eaef8bb85` |
| `tasks/scope/run7-scope-019/control/arm_summary.json` | `bc0787e67ce2d377ede7357377b8532e3f5244502f31a01671eeb321bc8de474` |
| `tasks/scope/run7-scope-019/control/baseline_reference.json` | `2c68e07e5120987d1ede791f16ffa7dd9a367ab84a0fb1a45853ca7706193298` |
| `tasks/scope/run7-scope-019/control/external_teacher.prompt.txt` | `67d09bdd45020412130697a94f13bab3f5a9ded233786fc6a26ed72b4f3f614c` |
| `tasks/scope/run7-scope-019/control/external_teacher.raw.json` | `bfb7fa727b7c3ddba0529e3b02e7bcf90717397329a8b69957ae72ea4938332f` |
| `tasks/scope/run7-scope-019/control/trajectory.jsonl` | `db153a9d1ea6fb24d6418d8c2013198d8cdc67402172ae72e34d84847719bda2` |
| `tasks/scope/run7-scope-019/control/worker-retry.prompt.txt` | `c1d1b6a415451efa85a3044d21364cb64fdcf130c3ff6d5cdc78053202989da2` |
| `tasks/scope/run7-scope-019/control/worker-retry.raw.json` | `29693fbf2fec50657c3e598c740f0fb38b713ad7002461f7476491ef037e6228` |
| `tasks/scope/run7-scope-019/control/worker-retry.validation.json` | `b2bffed6b6a67a4ef5e75e678a8231472aec7b218f72259bc3bf35a278440c65` |
| `tasks/scope/run7-scope-019/escalation/arm_artifacts.json` | `edfd1e6c087b43a20057c62d9fa7d7c3f7111da4843ef4a7d4b4613963a40a2c` |
| `tasks/scope/run7-scope-019/escalation/arm_binding.json` | `b72bec226e90d54c4144a6c2e67b6548774d7d9701624eb857a114bce6acbc99` |
| `tasks/scope/run7-scope-019/escalation/arm_summary.json` | `2623df2291a421ea5321426b054744fbd32cf7cbeaeccfeb859b33fe4fdc93e5` |
| `tasks/scope/run7-scope-019/escalation/external_teacher.prompt.txt` | `e1fccf5b6b50f9b48f35c690262ae929da94295990dfe16310fe7c187014058a` |
| `tasks/scope/run7-scope-019/escalation/external_teacher.raw.json` | `44a4e378f79f0fecde1687b77bd4539e1f238b68c7b6fba878c6070f3e8078f8` |
| `tasks/scope/run7-scope-019/escalation/trajectory.jsonl` | `13f8ab2725ecba40d0c917f9002590d6d0e839130343a01330db90f06c0dc00b` |
| `tasks/scope/run7-scope-019/escalation/worker-retry.prompt.txt` | `9323c26d7ea787e55f8a74651dfdee69e4166156153fa4b12879c4f0ba731587` |
| `tasks/scope/run7-scope-019/escalation/worker-retry.raw.json` | `368ad70c6b8965f3e2f28ad2a44899ee96f5c0df0df491a604dca8e9171b506f` |
| `tasks/scope/run7-scope-019/escalation/worker-retry.validation.json` | `5b771914a8a1e7cfcbe74cb6c9e965568556af5fc5654aa92c69768dd80e63e2` |
| `tasks/scope/run7-scope-019/local_first/arm_artifacts.json` | `288ff06930e2a884ff60377c6ca44040af1f300ca25e59a6fd3ef13a3a18340a` |
| `tasks/scope/run7-scope-019/local_first/arm_binding.json` | `cf1331832147cab54eadca3363b13156f0c2023a5b45d1bdf9b88dce465210e5` |
| `tasks/scope/run7-scope-019/local_first/arm_summary.json` | `d65c4fed57ac9268a3a852357b2a7d83e998ec7159915299a82795308a396638` |
| `tasks/scope/run7-scope-019/local_first/baseline_reference.json` | `2c68e07e5120987d1ede791f16ffa7dd9a367ab84a0fb1a45853ca7706193298` |
| `tasks/scope/run7-scope-019/local_first/local_teacher.prompt.txt` | `57f9d0779130e6a69a3366df7ae481a3bee43019d8c68fa20045df8bb81f4080` |
| `tasks/scope/run7-scope-019/local_first/local_teacher.raw.json` | `c1d624b05e19517f7376e6e00b7a244e53cf0cb15923b7beac2828f0aa0723a0` |
| `tasks/scope/run7-scope-019/local_first/trajectory.jsonl` | `e374ee422083c2efb5cc8108e3631ee34149d06050ee834999c8b5c812f5fdf7` |
| `tasks/scope/run7-scope-019/local_first/worker-retry.prompt.txt` | `4eddbbef99cf8eea50f570480e1f9110a2a0e798139f8c80664508d8a45f800b` |
| `tasks/scope/run7-scope-019/local_first/worker-retry.raw.json` | `4998e2ce2404dbf3ee8942babf8200b66be782f70e8b81b647240bedb4e04ace` |
| `tasks/scope/run7-scope-019/local_first/worker-retry.validation.json` | `a191f66857b3b3f737aaef164e5395c6dedbf8b59e21fcbed536bf405e12a01b` |
| `tasks/scope-authority-boundary/run7-scope-019/scorecard.json` | `5c6181f9a89f9c8962e140a8fcb207fc98e75529d191a00db3c2af9c7260680e` |
| `tasks/scope-authority-boundary/run7-scope-019/treatment_summary.json` | `95778be9b422dbb172af1c3e9ebf3af9787d178728378507f80a8891ca4876ac` |

## Prompt and input comparison

### Common facts

For each task, control and escalation prompts contained the same original task
prompt, output contract, reference facts, baseline diagnostics, and authority
boundary. The control and local-first baseline references were identical per
task, confirming that the paired paths began from the same baseline evidence.

The escalation prompt additionally contained the local-first validation status,
failed-check list, and local elapsed time. It did not contain the local raw
output. This is a bounded diagnostic summary, not the failed answer itself.

### Teacher prompts

The direct-control path calls `_teacher_prompt(...)`, which produces the
diagnostic teacher schema with `role`, an instruction to diagnose and propose a
review-only intervention, the complete failed transition validation object,
`allowed_fields`, and authority. It then uses the teacher's parsed diagnostic
payload in the worker retry.

The escalation path constructs a different JSON packet directly in
`_run_external_escalation` with `task_prompt`, `output_contract`,
`reference_facts`, `baseline_diagnostics`, `local_first_attempt`, an
`escalation_trigger`, and authority. It omits the direct path's diagnostic
instruction, `allowed_fields`, and `failed_transitions` wrapper. Its measured
teacher-prompt sizes were:

| Task | Direct control | Escalation |
|---|---:|---:|
| 001 | 5,801 chars | 1,826 chars |
| 006 | 5,788 chars | 1,740 chars |
| 019 | 5,704 chars | 1,737 chars |

The control teacher returned a diagnostic object containing
`corrected_reference_output` with list-valued targets and retry guidance for
all three tasks. The escalation teacher returned top-level task-output fields.
For 006 those fields had the expected list/bool/string types. For 001 and 019
the teacher returned object-valued `allowed_targets` and `held_targets` (and
object wrappers for other fields in 001), which is not the worker output
contract. These are materially different teacher-output shapes.

### Worker retry prompts

Both paths use the same general worker prompt fields: task prompt, output
contract, reference facts, baseline diagnostics, intervention, and authority.
The escalation path adds `local_first_validation_failure`.

However, the actual `intervention` payload differs critically:

| Task | Control intervention payload | Escalation intervention payload |
|---|---|---|
| 001 | diagnostic fields, corrected reference output, retry guidance | `{"teacher_parse_status":"passed"}` |
| 006 | diagnostic fields, corrected reference output, retry guidance | `{"teacher_parse_status":"passed"}` |
| 019 | diagnostic fields, corrected reference output, retry guidance | `{"teacher_parse_status":"passed"}` |

Worker retry prompt sizes were:

| Task | Direct control | Escalation |
|---|---:|---:|
| 001 | 2,442 chars / 574 prompt tokens | 1,738 chars / 421 prompt tokens |
| 006 | 2,608 chars / 597 prompt tokens | 1,656 chars / 402 prompt tokens |
| 019 | 2,493 chars / 571 prompt tokens | 1,640 chars / 399 prompt tokens |

Thus the escalation retry contains local failure diagnostics but not the
external teacher's actual semantic guidance. This is a confirmed lossy
integration, not an inferred psychological effect.

## Teacher and worker outputs

### Control path

All three control external-teacher outputs parsed as diagnostic objects with a
`corrected_reference_output`. All three control worker retries emitted the
required list-valued `allowed_targets` and `held_targets`, the correct boolean
`scope_expansion_required`, and the correct `review_status`. All control
validation checks passed.

### Escalation path

The escalation teacher raw outputs were transport-valid in all three cases,
but their content differed:

| Task | Escalation teacher observable shape | Worker retry output | Exact validation result |
|---|---|---|---|
| 001 | object-wrapped target fields | invalid JSON, including set-like target syntax | `parse_json`, `required_fields`, `required_field_types`, both target checks, scope-expansion check, and review-status check failed |
| 006 | list-valued targets; correct boolean/string | correct list-valued contract | passed |
| 019 | object-valued target fields | valid JSON but object-valued targets | `required_field_types` and both target checks failed |

For 001, the escalation worker output was not valid JSON. For 019, it was
valid JSON but violated the required list types. For 006, it matched the
contract. The deterministic validator consistently reported the observable
output defects; no validator discrepancy was found.

## Divergence trace

| Task | Descriptive divergence classification | Artifact basis |
|---|---|---|
| 001 | `IMPLEMENTATION_DEFECT_IDENTIFIED`: worker-retry prompt integration plus teacher-output contract divergence | Escalation intervention payload contains only parse status; worker emits invalid JSON and fails all structural/reference checks; direct control contains corrected reference output and passes. |
| 006 | Same integration asymmetry exists, but worker independently emits a valid contract | Escalation intervention payload still contains only parse status; worker emits correct lists and passes. This positive case shows the defect is not sufficient to fail every task. |
| 019 | `IMPLEMENTATION_DEFECT_IDENTIFIED`: worker-retry prompt integration plus teacher-output contract divergence | Escalation intervention payload contains only parse status; worker emits object-valued targets and fails type/reference checks; direct control passes. |

The validator is not the divergence point: it accepted the direct outputs and
rejected the escalation outputs according to the same frozen contract and
reference facts. The treatment external teacher was not transport-failed.

## Recovery-context contamination checks

The escalation worker prompt did not include the local raw answer, only the
local failed-check identifiers. Therefore the artifacts do not support a
claim that a wrong local target was copied into the escalation prompt.

The prompt does contain repeated target information through the task prompt,
reference facts, and output contract, but this repetition exists in both paths.
The escalation-only addition is the local failed-check list. There is no
mechanically demonstrated conflicting authority statement or explicit
instruction-priority conflict.

The observed malformed/object-valued outputs are consistent with missing or
lossy teacher-guidance integration and task-specific worker behavior. Claims
of anchoring, overload, or another cognitive mechanism are not supported by
these artifacts alone.

## Structural comparator: 006 versus 001/019

All three tasks shared the same recovery-path asymmetry and the same frozen
models and validators. Their frozen structural features differed:

| Task | Difficulty features | Local failed checks |
|---|---|---|
| 001 | partial/stale authority; separate authorization; preserve allowed/held targets; cross-artifact consistency | `required_field_types`, `reference_required_allowed_targets`, `reference_required_held_targets` |
| 006 | partial/stale authority; conflicting authority across artifacts; separate authorization; preserve allowed/held targets | `reference_requires_scope_expansion_flag` |
| 019 | nested responsibility/authority; implicit/explicit approval; separate authorization; multiple allowed/held boundaries | `required_field_types`, `reference_required_allowed_targets`, `reference_required_held_targets` |

The common recovery properties are: same escalation function, same reduced
teacher parser result, same added local-failure list, same output contract, and
same validation machinery. The distinguishing observations are the task
content, local failure category, and external-teacher/worker output shape.
006 succeeded despite the shared integration loss because its worker output
was independently contract-valid. No stronger causal claim is made from one
positive comparator.

## Implementation path inspection

The relevant frozen code paths are:

- Direct control action: `scripts/zth_run6_sequential_economic_routing.py:159-173`
  calls `run_isolated_intervention_arm`.
- Direct teacher and worker construction:
  `local_harness/run4a_intervention_harness.py:298-303` calls
  `_teacher_prompt`, `_call_teacher`, then builds the worker prompt from
  `teacher_payload["parsed"]`.
- Shared teacher parser:
  `local_harness/supervised_capability_loop.py:261-275` retains only
  `failure_classification`, `teacher_diagnosis`, `retry_guidance`, and
  `corrected_reference_output` (plus parse status).
- Escalation construction:
  `scripts/zth_run6_sequential_economic_routing.py:176-204` constructs a
  separate teacher prompt, parses it through the same `_call_teacher` path,
  and then passes `teacher_payload["parsed"]` into the retry prompt.

This creates the concrete asymmetry. The escalation teacher prompt elicits
top-level task-output fields, but the shared parser is designed for the direct
diagnostic teacher schema and silently discards those task-output fields. The
resulting escalation worker prompt contains only
`{"teacher_parse_status":"passed"}` as intervention guidance for all three
tasks.

A second, non-causal durability asymmetry is also confirmed: direct isolated
arms write `baseline_reference.json`, while `_run_external_escalation` does
not. The escalation binding still records the baseline-summary digest, so this
is an artifact-provenance gap rather than evidence that a different baseline
was used.

## Findings

### CONFIRMED

- The direct and escalation paths use different teacher prompt schemas.
- The escalation teacher outputs task-output-shaped fields, while the shared
  parser retains only direct-diagnostic field names.
- All three escalation worker retry prompts lost the teacher's semantic
  guidance and contained only parse status in `intervention`.
- Control worker retries received corrected reference output and retry guidance.
- 001 and 019 failed on observable worker output structure/types; 006 emitted a
  valid output and succeeded.
- The frozen validator consistently accepted valid control outputs and rejected
  invalid escalation outputs.
- The escalation path does not durably write `baseline_reference.json`.

### LIKELY

- The lost external guidance materially contributed to the two treatment
  failures, because the direct path passed the same bounded tasks with
  corrected reference guidance present and the escalation path omitted it.
- The task-specific teacher/worker output differences interacted with that
  common integration defect; 006's success shows the defect is not alone
  sufficient to determine the outcome.

### POSSIBLE

- The reduced escalation prompt or the added local-failure diagnostics may
  affect worker behavior through context ordering or task difficulty.
- The external teacher may respond more reliably if escalation uses an
  explicit diagnostic/review-only output contract rather than the task output
  contract.

### NOT SUPPORTED

- A validator discrepancy.
- Transport or model-identity failure.
- Copying of the local raw answer into the escalation prompt.
- A universal external-teacher capability failure on 001 or 019.
- A causal claim that context length, anchoring, or authority confusion alone
  caused the failures.

## Disposition and narrow next action

**Disposition: `IMPLEMENTATION_DEFECT_IDENTIFIED`.**

Before another experiment, a narrow model-free implementation repair/test is
justified: make the escalation teacher response contract explicit and ensure
the semantic recovery guidance is durably and correctly passed into the
worker retry. The test should use the observed 001/006/019 response shapes,
assert that list-valued target guidance survives parsing and prompt
serialization, and preserve the existing validator and authority boundaries.
The escalation baseline reference should also be written for provenance
parity. This report does not implement that repair, rerun Run 7, or design or
preregister Run 8.

## Authority boundary

This is a review-only forensic report. It does not modify Run 7 artifacts,
policy, driver, preregistration, fixtures, validators, resource priors,
capability cards, or production routing. No model calls were made.
