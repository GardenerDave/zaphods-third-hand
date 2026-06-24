from local_harness.failure_training.paths import CYCLE_SUBDIRS, cycle_dir, ensure_cycle_tree


def test_cycle_dir_builds_expected_path(tmp_path):
    assert cycle_dir(tmp_path, "cycle_0001") == tmp_path / "cycles" / "cycle_0001"


def test_ensure_cycle_tree_creates_expected_subdirs(tmp_path):
    base = ensure_cycle_tree(tmp_path, "cycle_0001")

    assert base == tmp_path / "cycles" / "cycle_0001"
    assert base.exists()

    for child in CYCLE_SUBDIRS:
        assert (base / child).is_dir()
