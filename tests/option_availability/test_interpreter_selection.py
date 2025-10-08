import asyncio
import os
import sys
import threading
import pytest
from _pytest.outcomes import OutcomeException


pytestmark = pytest.mark.ci_safe


def test_replace_python_with_sys_executable(monkeypatch, tmp_path):
    """Ensure script_manager replaces leading 'python' with sys.executable in CI-safe path.

    Avoid manual event loop control to prevent 'This event loop is already running'
    under coverage/pytest-asyncio. This aligns with the CI-safe testing policy.
    """
    from src.script import script_manager as sm

    captured = {}

    async def fake_process_execution(parts, env=None, cwd=None):
        captured['parts'] = parts
        class P:
            returncode = 0
            async def communicate(self):
                await asyncio.sleep(0)
                return b"", b""
        await asyncio.sleep(0)
        return P(), []

    monkeypatch.setattr(sm, 'process_execution', fake_process_execution)

    # Prepare isolated working directory and dummy script
    workdir = tmp_path / 'myscript'
    workdir.mkdir(parents=True, exist_ok=True)
    (workdir / 'dummy.py').write_text('print("ok")', encoding='utf-8')
    monkeypatch.chdir(tmp_path)

    script_info = {
        'type': 'script',
        'name': 'unit-test',
        'script': 'dummy.py',
        'command': 'python -m pytest ${script_path} --flag',
    }

    # Act
    async def _run():
        await sm.run_script(script_info, params={}, headless=True)

    result_container: dict[str, object | None] = {}

    def _runner():
        try:
            asyncio.run(_run())
            result_container['done'] = True
        except (Exception, OutcomeException) as exc:  # pragma: no cover - surfaced below
            result_container['error'] = exc

    thread = threading.Thread(target=_runner, name="script-manager-runner")
    thread.start()
    thread.join()

    if 'error' in result_container:
        raise result_container['error']  # type: ignore[misc]

    # Assert the interpreter was normalized
    assert captured['parts'][0] == sys.executable
