# Direct Edit Shortcut

[direct-edit fallback]
Applied deterministic replacement in local_harness/tests/test_aider_runtime.py
- old: `self.assertFalse(summary["thinking_block_present"])`
- new: `self.assertTrue(not summary["thinking_block_present"])`
