import sys
import os
import pytest


pytestmark = pytest.mark.ci_safe


# Force pytest-anyio to use asyncio backend only in this module to avoid requiring trio
@pytest.fixture
def anyio_backend():
    return 'asyncio'


@pytest.mark.anyio
async def test_replace_python_with_sys_executable(monkeypatch, tmp_path):
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
                return b"", b""
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
    await sm.run_script(script_info, params={}, headless=True)

    # Assert the interpreter was normalized
    assert captured['parts'][0] == sys.executable
