"""Pytest bootstrap for the ZTH test suite.

This file scopes the *test process* PATH so that the preserved external
teacher mechanism resolves the qualified Codex CLI 0.146.0, while the
operator's interactive shell and the global ``@openai/codex`` npm package are
left untouched (they remain free to run the operator's current version).

Background
----------
The preserved external teacher is a hash-bound wrapper
(``/home/navigator/bin/zth-codex-teacher``) plus the hash-frozen V2 execution
harness. Neither may be modified. Both resolve the Codex CLI by bare ``codex``
PATH lookup:

* the harness calls ``shutil.which("codex")`` and requires ``codex --version``
  to report exactly ``codex-cli 0.146.0``;
* the wrapper shells out to a bare ``codex exec ...``.

To keep the global npm package free for the operator's current version, the
qualified 0.146.0 CLI is installed into an isolated user-local prefix instead
of being pinned globally. This conftest puts that isolated bin directory at the
front of the test process ``PATH`` so the teacher resolves 0.146.0 during test
runs. The interactive login shell is not modified, so ``codex`` there still
resolves to the global package.

The isolated prefix is created by::

    npm install --prefix /home/navigator/.local/share/zaphods-third-hand/codex-0.146.0 \
        @openai/codex@0.146.0

This mechanism does not weaken any validation: the harness still resolves
``codex`` itself and still verifies the reported version string. It only makes
PATH point at the isolated, version-qualified executable.
"""

from __future__ import annotations

import os

# Isolated, version-qualified Codex CLI bin directory.
#
# This is a user-local path outside the repository; it is intentionally NOT
# added to the operator's interactive PATH. It only needs to be on PATH for the
# test process (and for any operator-invoked teacher driver that needs the
# qualified CLI).
ISOLATED_CODEX_BIN = "/home/navigator/.local/share/zaphods-third-hand/codex-0.146.0/bin"


def pytest_configure(config) -> None:  # noqa: ANN001
    """Prepend the isolated qualified Codex bin dir to the test process PATH.

    Idempotent: if the directory is already the first PATH entry it is left in
    place. No-op if the isolated prefix has not been created yet.
    """
    if not os.path.isdir(ISOLATED_CODEX_BIN):
        return
    path_entries = os.environ.get("PATH", "").split(os.pathsep)
    if path_entries and path_entries[0] == ISOLATED_CODEX_BIN:
        return
    new_path = os.pathsep.join([ISOLATED_CODEX_BIN] + path_entries)
    os.environ["PATH"] = new_path
