import asyncio
import functools
import inspect
import os
import shutil
import sys
import threading
from pathlib import Path

import pytest
from _pytest.outcomes import OutcomeException


def _patch_pytest_asyncio_wrap_in_sync():
    """Ensure pytest-asyncio wrap_in_sync tolerates sync wrappers."""

    try:
        import pytest_asyncio.plugin as pytest_asyncio_plugin
    except ImportError:  # pragma: no cover - plugin optional in some envs
        return

    if getattr(pytest_asyncio_plugin, "_wrap_in_sync_patched", False):
        return

    _get_event_loop_no_warn = pytest_asyncio_plugin._get_event_loop_no_warn

    def wrap_in_sync_safe(func):
        raw_func = getattr(func, "_raw_test_func", None)
        if raw_func is not None:
            func = raw_func

        @functools.wraps(func)
        def inner(*args, **kwargs):
            result = func(*args, **kwargs)
            if not inspect.isawaitable(result):
                return result

            coro = result
            _loop = _get_event_loop_no_warn()
            task = asyncio.ensure_future(coro, loop=_loop)
            try:
                _loop.run_until_complete(task)
            except BaseException:
                if task.done() and not task.cancelled():
                    task.exception()
                raise

        inner._raw_test_func = func  # type: ignore[attr-defined]
        return inner

    pytest_asyncio_plugin.wrap_in_sync = wrap_in_sync_safe
    pytest_asyncio_plugin._wrap_in_sync_patched = True


def _run_coroutine_in_thread(coro_fn):
    result = {}

    def worker():
        try:
            result["value"] = asyncio.run(coro_fn())
        except (Exception, OutcomeException) as exc:  # pragma: no cover - passthrough to main thread
            result["error"] = exc

    thread = threading.Thread(target=worker, name="pytest-async-wrapper", daemon=True)
    thread.start()
    thread.join()

    if "error" in result:
        raise result["error"]

    return result.get("value")


def _threaded_async_wrapper(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        return _run_coroutine_in_thread(lambda: fn(*args, **kwargs))

    return wrapper


def _promote_coroutine_item(item) -> bool:
    func = getattr(item, "obj", None)
    if not (func and inspect.iscoroutinefunction(func)):
        return False

    wrapped = _threaded_async_wrapper(func)
    item.obj = wrapped
    if hasattr(item, "_obj"):
        item._obj = wrapped

    if hasattr(item, "own_markers"):
        item.own_markers = [m for m in item.own_markers if m.name != "asyncio"]

    if hasattr(item, "keywords") and isinstance(item.keywords, dict):
        item.keywords.pop("asyncio", None)

    if hasattr(item, "fixturenames"):
        item.fixturenames = [name for name in item.fixturenames if name != "event_loop"]

    fixtureinfo = getattr(item, "_fixtureinfo", None)
    if fixtureinfo is not None:
        if hasattr(fixtureinfo, "names_closure"):
            filtered = [name for name in fixtureinfo.names_closure if name != "event_loop"]
            object.__setattr__(fixtureinfo, "names_closure", filtered)
        if hasattr(fixtureinfo, "name2fixturedefs"):
            fixtureinfo.name2fixturedefs.pop("event_loop", None)

    return True


def _detect_project_root(start: Path) -> Path:
    markers = {"pyproject.toml", "README.md", ".git", "artifacts"}
    current = start.resolve()
    for parent in [current] + list(current.parents):
        try:
            entries = {p.name for p in parent.iterdir()}
        except OSError:
            continue
        if markers & entries:
            return parent
    return start


def _ensure_sys_path(path: Path) -> None:
    p = str(path)
    if p not in sys.path:
        sys.path.insert(0, p)


def pytest_configure(config):
    # Register commonly used markers to avoid pytest warnings
    config.addinivalue_line("markers", "integration: mark test as integration-heavy (requires network/browser)")
    config.addinivalue_line("markers", "local_only: mark test that should only run on a developer machine")

    # 1) Allow explicit override for project root
    root_env = os.environ.get("BYKILT_ROOT")
    if root_env:
        root_path = Path(root_env).expanduser().resolve()
    else:
        this_file = Path(__file__).resolve()
        root_path = _detect_project_root(this_file.parent)

    # Prefer src/ if it exists; else add repo root
    src_path = root_path / "src"
    if src_path.exists():
        _ensure_sys_path(src_path)
    _ensure_sys_path(root_path)

    # Optional: expose for tests that may need it
    os.environ.setdefault("BYKILT_ROOT_EFFECTIVE", str(root_path))

    _patch_pytest_asyncio_wrap_in_sync()


def pytest_collection_modifyitems(config, items):
    """
    Skip integration / local_only tests by default unless corresponding
    environment variables are set. This centralizes the previous per-file
    env guards and makes CI configuration simpler.

    Environment variables:
      RUN_LOCAL_INTEGRATION=1  -> run @pytest.mark.integration tests
      RUN_LOCAL_FINAL_VERIFICATION=1 -> run @pytest.mark.local_only tests
    """
    run_integration = os.environ.get("RUN_LOCAL_INTEGRATION")
    run_final = os.environ.get("RUN_LOCAL_FINAL_VERIFICATION")

    skip_integration = pytest.mark.skip(reason="Integration tests skipped by default. Set RUN_LOCAL_INTEGRATION=1 to enable")
    skip_final = pytest.mark.skip(reason="Local-only tests skipped by default. Set RUN_LOCAL_FINAL_VERIFICATION=1 to enable")

    for item in items:
        if "integration" in item.keywords and not run_integration:
            item.add_marker(skip_integration)
        if "local_only" in item.keywords and not run_final:
            item.add_marker(skip_final)

        _promote_coroutine_item(item)


@pytest.fixture(scope="function")
def cleanup_singletons():
    """
    Fixture to reset singletons before and after each test.
    
    This fixture should be explicitly used by tests that need clean singleton state.
    Use this instead of autouse to avoid conflicts with monkeypatch.chdir(tmp_path).
    
    Usage:
        def test_something(tmp_path, monkeypatch, cleanup_singletons):
            monkeypatch.chdir(tmp_path)
            # test code here
    """
    # Import here to avoid circular dependencies
    from src.core.artifact_manager import reset_artifact_manager_singleton
    from src.config.feature_flags import FeatureFlags
    from src.runtime.run_context import RunContext
    
    # Pre-test cleanup: reset singletons
    RunContext.reset()
    reset_artifact_manager_singleton()
    FeatureFlags.clear_all_overrides()
    
    # Run the test
    yield
    
    # Post-test cleanup: reset singletons again
    RunContext.reset()
    reset_artifact_manager_singleton()
    FeatureFlags.clear_all_overrides()


