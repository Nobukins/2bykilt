"""Tests for browser-control recording behavior."""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from src.script.script_manager import run_script
from src.utils.fs_paths import get_artifacts_base_dir
from src.utils.recording_dir_resolver import create_or_get_recording_dir


class DummyProcess:
    """Minimal async subprocess stub for run_script tests."""

    def __init__(self, stdout: bytes = b"", stderr: bytes = b"", returncode: int = 0):
        self._stdout = stdout
        self._stderr = stderr
        self.returncode = returncode

    async def communicate(self):
        return self._stdout, self._stderr


@pytest.mark.ci_safe
class TestBrowserControlTypeRecording:
    """Validate recording path behavior for browser-control scripts."""

    def setup_method(self):
        self._original_cwd = Path.cwd()
        self.test_dir = Path(tempfile.mkdtemp())
        os.chdir(self.test_dir)

        # Establish isolated directories that mirror runtime expectations
        self.myscript_dir = Path("myscript")
        self.myscript_dir.mkdir(parents=True, exist_ok=True)

        self.artifacts_dir = get_artifacts_base_dir() / "runs" / "test-browser-control"
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    def teardown_method(self):
        os.chdir(self._original_cwd)
        shutil.rmtree(self.test_dir, ignore_errors=True)

    @pytest.mark.asyncio
    @patch("asyncio.create_subprocess_exec", new_callable=AsyncMock)
    async def test_browser_control_type_recording_path(self, mock_subproc_exec: AsyncMock):
        """Browser-control runs should set unified recording path in env."""

        mock_subproc_exec.return_value = DummyProcess(stdout=b"Test output", stderr=b"")

        script_info = {
            "type": "browser-control",
            "name": "test_browser_control",
            "flow": [
                {"action": "navigate", "url": "https://example.com"},
                {"action": "wait_for_selector", "selector": "h1"},
            ],
        }

        params: dict[str, str] = {}
        save_recording_path = str(self.artifacts_dir / "runs" / "browser-control-test-art" / "videos")

        result, script_path = await run_script(
            script_info=script_info,
            params=params,
            headless=True,
            save_recording_path=save_recording_path,
        )

        assert script_path is not None
        assert "Script executed successfully" in result

        call = mock_subproc_exec.await_args
        assert call is not None
        env = call.kwargs["env"]

        expected_recording = str(create_or_get_recording_dir(save_recording_path))
        assert env["RECORDING_PATH"] == expected_recording
        assert "videos" in expected_recording
        assert Path(expected_recording).is_absolute()

    @pytest.mark.asyncio
    @patch("asyncio.create_subprocess_exec", new_callable=AsyncMock)
    async def test_browser_control_script_generation(self, mock_subproc_exec: AsyncMock):
        """Generated script should exist and contain key content."""

        mock_subproc_exec.return_value = DummyProcess(returncode=0)

        script_info = {
            "type": "browser-control",
            "name": "test_generation",
            "flow": [{"action": "navigate", "url": "https://example.com"}],
        }

        result, script_path = await run_script(
            script_info=script_info,
            params={},
            headless=True,
        )

        assert "Script executed successfully" in result
        generated_path = Path(script_path)
        assert generated_path.exists()
        content = generated_path.read_text(encoding="utf-8")
        assert "https://example.com" in content
        assert "RECORDING_PATH" in content

    @pytest.mark.asyncio
    @patch("asyncio.create_subprocess_exec", new_callable=AsyncMock)
    async def test_browser_control_with_custom_recording_path(self, mock_subproc_exec: AsyncMock):
        """Custom recording directories should be resolved consistently."""

        mock_subproc_exec.return_value = DummyProcess(returncode=0)

        custom_path = str(self.artifacts_dir / "custom" / "path" / "videos")

        script_info = {
            "type": "browser-control",
            "name": "test_custom_path",
            "flow": [{"action": "navigate", "url": "https://example.com"}],
        }

        result, _ = await run_script(
            script_info=script_info,
            params={},
            headless=True,
            save_recording_path=custom_path,
        )

        assert "Script executed successfully" in result

        call = mock_subproc_exec.await_args
        env = call.kwargs["env"]
        expected = str(create_or_get_recording_dir(custom_path))
        assert env["RECORDING_PATH"] == expected

    def test_recording_path_unified_behavior(self):
        """Resolver should normalize various recording directory inputs."""

        paths_to_test = [
            str(self.artifacts_dir / "runs" / "test1-art" / "videos"),
            str(self.artifacts_dir / "runs" / "test2-art" / "videos"),
            str(self.artifacts_dir / "custom" / "test3" / "videos"),
        ]

        for candidate in paths_to_test:
            resolved = create_or_get_recording_dir(candidate)
            assert resolved.exists()
            resolved_str = str(resolved)
            assert "artifacts" in resolved_str or "videos" in resolved_str
