"""
Option availability verification tests

Ensures the four main options are present and minimally validated:
- script
- action_runner_template
- browser-control
- git-script

Also validates CI-safe aspects: Chrome config wiring, profile args, and recording path.
"""

import asyncio
import os
import sys
import threading
from pathlib import Path
from typing import Dict

import pytest
from _pytest.outcomes import OutcomeException


"""Ensure project root is on sys.path for 'src' imports when run locally."""
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.modules.yaml_parser import InstructionLoader
from src.browser import browser_manager as bm
from src.browser.browser_config import BrowserConfig
from src.browser.browser_manager import get_browser_configs, prepare_recording_path, initialize_browser
from src.modules.automation_manager import BrowserAutomationManager

# All tests in this module are designed to be CI-safe
pytestmark = pytest.mark.ci_safe


@pytest.fixture()
def fake_chrome_env(tmp_path, monkeypatch):
    """Fake Chrome binary and profile, for CI-safe environment"""
    chrome_bin = tmp_path / "chrome"
    chrome_bin.write_text("#!/bin/sh\nexit 0\n")
    user_data = tmp_path / "ChromeUserData"
    (user_data / "Default").mkdir(parents=True, exist_ok=True)
    rec_dir = tmp_path / "recordings"
    rec_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("DEFAULT_BROWSER", "chrome")
    monkeypatch.setenv("CHROME_PATH", str(chrome_bin))
    monkeypatch.setenv("CHROME_USER_DATA", str(user_data))
    monkeypatch.setenv("RECORDING_PATH", str(rec_dir))

    # Reset BrowserConfig singleton and rebind in browser_manager
    BrowserConfig._instance = None  # type: ignore[attr-defined]
    fresh = BrowserConfig()
    bm.browser_config = fresh

    return {"bin": str(chrome_bin), "user_data": str(user_data), "recordings": str(rec_dir)}


@pytest.fixture(autouse=True)
def isolated_actions_file(tmp_path, monkeypatch):
    """Create a minimal llms.txt including all four action types in an isolated CWD."""
    content = "\n".join(
        [
            "actions:",
            "  - name: run-script",
            "    type: script",
            "    script: hello.py",
            "    command: echo \"Hello Script\"",
            "  - name: run-runner",
            "    type: action_runner_template",
            "    action_script: run_action.py",
            "    command: python ${action_script} --opt ${params.opt|default}",
            "  - name: control-site",
            "    type: browser-control",
            "    slowmo: 0",
            "    flow:",
            "      - action: navigate",
            "        url: https://example.com",
            "  - name: run-repo",
            "    type: git-script",
            "    git: https://example.com/repo.git",
            "    script_path: run.py",
            "    command: python ${script_path}",
        ]
    )
    (tmp_path / "llms.txt").write_text(content, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    yield


def _load_actions() -> Dict:
    loader = InstructionLoader(local_path="llms.txt")
    result = loader.load_instructions()
    assert result.success, f"Failed to load instructions: {result.error}"
    by_type: Dict[str, list] = {}
    for action in result.instructions:
        t = action.get("type", "unknown")
        by_type.setdefault(t, []).append(action)
    return by_type


def _run_async(coro):
    result_container: dict[str, object] = {}

    def _runner():
        try:
            result_container["value"] = asyncio.run(coro)
        except (Exception, OutcomeException) as exc:  # pragma: no cover - propagated
            result_container["error"] = exc

    thread = threading.Thread(target=_runner, name="option-availability-async")
    thread.start()
    thread.join()

    if "error" in result_container:
        raise result_container["error"]  # type: ignore[misc]
    return result_container.get("value")


def test_llms_actions_types_available():
    by_type = _load_actions()
    for needed in ("script", "action_runner_template", "browser-control", "git-script"):
        assert needed in by_type and len(by_type[needed]) > 0, f"Missing actions for type: {needed}"


def test_recording_path_creation(fake_chrome_env):
    explicit = Path(fake_chrome_env["recordings"]) / "explicit"
    resolved = prepare_recording_path(True, str(explicit))
    assert resolved is not None and Path(resolved).exists()

    resolved2 = prepare_recording_path(True, None)
    assert resolved2 is not None and Path(resolved2).exists()


def test_profile_args_in_get_browser_configs(fake_chrome_env):
    cfg = get_browser_configs(use_own_browser=True, window_w=1280, window_h=720, browser_type="chrome")
    assert cfg["browser_path"] == fake_chrome_env["bin"]
    assert cfg["browser_type"] == "chrome"
    args = cfg["extra_chromium_args"]
    assert f"--user-data-dir={fake_chrome_env['user_data']}" in args


def test_initialize_browser_calls_new_tab(fake_chrome_env, monkeypatch):
    called = {}

    class StubDebugManager:
        async def initialize_custom_browser(self, use_own_browser, headless, tab_selection_strategy):  # pragma: no cover
            called["use_own_browser"] = use_own_browser
            called["headless"] = headless
            called["tab_selection_strategy"] = tab_selection_strategy
            await asyncio.sleep(0)
            return {"status": "success", "browser": "stub"}

    monkeypatch.setattr(bm, "BrowserDebugManager", lambda: StubDebugManager())

    async def _run():
        return await initialize_browser(
            use_own_browser=True,
            headless=True,
            browser_type="chrome",
            auto_fallback=False,
        )

    result = _run_async(_run())
    assert isinstance(result, dict) and result.get("status") == "success"
    assert called.get("tab_selection_strategy") == "new_tab"


def test_execute_script_action_safe_path(monkeypatch):
    m = BrowserAutomationManager(local_path="llms.txt")
    assert m.initialize() is True
    action = next(a for a in m.actions.values() if a.get("type") == "script")
    name = action["name"]
    ok = _run_async(m.execute_action(name, query="LLMs.txt"))
    assert ok is True


def test_execute_git_script_action_mocked(monkeypatch, tmp_path):
    m = BrowserAutomationManager(local_path="llms.txt")
    assert m.initialize() is True
    m.git_repos_dir = tmp_path / "git_scripts"
    m.git_repos_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr("src.modules.automation_manager.clone_or_pull_repository", lambda url, target_dir: True)
    monkeypatch.setattr("src.modules.automation_manager.checkout_version", lambda target_dir, version: True)

    class R:
        returncode = 0

    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: R())

    action = next(a for a in m.actions.values() if a.get("type") == "git-script")
    name = action["name"]
    ok = _run_async(m.execute_action(name, query="LLMs.txt"))
    assert ok is True


def test_action_runner_template_structure():
    by_type = _load_actions()
    arts = by_type["action_runner_template"]
    assert all("action_script" in a for a in arts)
    assert all("command" in a for a in arts)
    for a in arts:
        assert "${action_script}" in a["command"], "command should reference ${action_script}"
