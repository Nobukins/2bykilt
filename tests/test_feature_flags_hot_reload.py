from src.runtime.run_context import RunContext
from src.config.feature_flags import FeatureFlags, _reset_feature_flags_for_tests


def test_feature_flags_mtime_reload(monkeypatch, caplog):
    """Trigger the mtime-based reload path by forcing _flags_mtime to an old value.

    Ensures the informational log (event flag.file.modified.reload) is emitted.
    """
    _reset_feature_flags_for_tests()
    flags_file = FeatureFlags._flags_file  # type: ignore[attr-defined]
    assert flags_file and flags_file.exists()
    # Prime once
    FeatureFlags.is_enabled("enable_llm")
    # Force old mtime sentinel
    FeatureFlags._flags_mtime = 0  # type: ignore[attr-defined]
    caplog.set_level("INFO")
    FeatureFlags.is_enabled("enable_llm")
    msgs = [r.message for r in caplog.records if "Feature flags file modified on disk; reloading" in r.message]
    assert msgs, "Expected mtime reload log message"


## NOTE: Artifact rewrite branch relies on working directory transitions; covered indirectly in existing tests.

# NOTE: Hot reload behavior depends on underlying filesystem mtime resolution and is covered
# indirectly by existing integration patterns; this test focuses on the new ensure=False path.


def test_run_context_artifact_dir_ensure_false(monkeypatch):
    """Ensure ensure=False returns path without creating directory (Issue #91 helper)."""
    monkeypatch.setenv("BYKILT_RUN_ID", "ENSUREFALSE91")
    RunContext.reset()
    rc = RunContext.get()
    p = rc.artifact_dir("flags", ensure=False)
    # If directory already exists from prior side effects, remove it to validate behavior deterministically
    if p.exists():
        import shutil
        shutil.rmtree(p)
    # Recompute path (should be same) and ensure still absent
    p = rc.artifact_dir("flags", ensure=False)
    assert not p.exists(), "Directory should not be created when ensure=False"
    # Now create
    p_created = rc.artifact_dir("flags", ensure=True)
    assert p_created.exists() and p_created == p
