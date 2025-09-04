from src.runtime.run_context import RunContext

# NOTE: Hot reload behavior depends on underlying filesystem mtime resolution and is covered
# indirectly by existing integration patterns; this test focuses on the new ensure=False path.


def test_run_context_artifact_dir_ensure_false(monkeypatch):
    """Ensure ensure=False returns path without creating directory (Issue #91 helper)."""
    monkeypatch.setenv("BYKILT_RUN_ID", "ENSUREFALSE91")
    RunContext.reset()
    rc = RunContext.get()
    p = rc.artifact_dir("flags", ensure=False)
    assert not p.exists(), "Directory should not be created when ensure=False"
    p2 = rc.artifact_dir("flags", ensure=True)
    assert p2.exists() and p2 == p
