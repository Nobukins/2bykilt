# Ensure project root and src/ are importable when running pytest from tests/
import sys
from pathlib import Path
import asyncio
import pytest

# Mitigate widespread 'event loop is already running' failures in full test runs
# by allowing nested loop usage (some code paths start an event loop internally)
# and by providing a fresh loop per test. (#91 stabilization)
try:
    import nest_asyncio  # type: ignore
    nest_asyncio.apply()
except Exception:
    # If nest_asyncio is unavailable, continue; tests that don't nest loops still pass.
    pass

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture(scope="function")
def event_loop():
    """Provide a fresh asyncio event loop per test.

    The default pytest-asyncio behavior under auto mode occasionally collides
    with nested loop starts inside application code (e.g., utilities launching
    temporary async tasks). Creating an isolated loop here prevents cross-test
    contamination and eliminates re-entrancy errors.
    """
    loop = asyncio.new_event_loop()
    try:
        yield loop
    finally:
        loop.close()
