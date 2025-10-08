import asyncio
import threading
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

import pytest

from src.runtime.run_context import RunContext
from src.core.artifact_manager import reset_artifact_manager_singleton
from myscript.bin.demo_artifact_capture import run_demo
from src.modules.direct_browser_control import execute_direct_browser_control
import src.utils.git_script_automator as git_script_automator
import src.utils.profile_manager as profile_manager


pytestmark = pytest.mark.integration


class StaticSiteServer:
    def __init__(self, directory: Path):
        handler = partial(SimpleHTTPRequestHandler, directory=str(directory))
        self._httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()

    @property
    def port(self) -> int:
        return self._httpd.server_address[1]

    def url(self, path: str = "index.html") -> str:
        return f"http://127.0.0.1:{self.port}/{path}"

    def close(self) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()
        self._thread.join(timeout=5)


@pytest.fixture
def static_site(tmp_path):
    site_dir = tmp_path / "site"
    site_dir.mkdir()
    html = """<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <title>Artifact Demo</title>
</head>
<body>
  <main>
    <h1 id=\"message\">Hello From Test Suite</h1>
    <p class=\"info\">Captured content for verification.</p>
  </main>
</body>
</html>
"""
    (site_dir / "index.html").write_text(html, encoding="utf-8")
    server = StaticSiteServer(site_dir)
    try:
        yield server
    finally:
        server.close()


def _prepare_artifact_environment(monkeypatch, base_dir: Path) -> None:
    from src.runtime import run_context as run_context_module

    base_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("ARTIFACTS_BASE_DIR", str(base_dir))
    monkeypatch.delenv("BYKILT_RUN_ID", raising=False)
    monkeypatch.delenv("RECORDING_PATH", raising=False)
    monkeypatch.setattr(run_context_module, "_ARTIFACT_ROOT", base_dir.resolve() / "runs")
    RunContext.reset()
    reset_artifact_manager_singleton()


def _assert_artifacts_created(artifact_base: Path) -> Path:
    runs_root = artifact_base / "runs"
    run_dirs = sorted(runs_root.glob("*-art"))
    assert run_dirs, "No artifact run directories were created"
    run_dir = run_dirs[-1]

    screenshots = list((run_dir / "screenshots").glob("*.png"))
    assert screenshots, "Screenshot artifacts were not captured"

    element_txt = list((run_dir / "elements").glob("*.txt"))
    element_json = list((run_dir / "elements").glob("*.json"))
    assert element_txt, "Element text captures were not saved"
    assert element_json, "Element metadata JSON was not saved"

    video_dir = run_dir / "videos"
    video_files = list(video_dir.glob("*.webm")) + list(video_dir.glob("*.mp4"))
    assert video_files, "Browser recording was not persisted"

    return run_dir


def test_demo_artifact_capture_script_creates_artifacts(static_site, tmp_path, monkeypatch):
    artifact_base = tmp_path / "artifacts_script"
    _prepare_artifact_environment(monkeypatch, artifact_base)

    asyncio.run(
        run_demo(
            url=static_site.url(),
            selector="#message",
            prefix="script_demo",
            browser="chromium",
            headless=True,
            fields=["text", "html"],
        )
    )

    run_dir = _assert_artifacts_created(artifact_base)
    manifest = run_dir / "manifest_v2.json"
    assert manifest.exists(), "Manifest file was not created for script run"


def _fake_profile_manager_class(base_dir: Path):
    class _FakeProfileManager(profile_manager.ProfileManager):
        def __init__(self, source_profile_dir: str | None = None):
            super().__init__(str(base_dir))

    return _FakeProfileManager


def _create_fake_profile(base_dir: Path) -> Path:
    base_dir.mkdir(parents=True, exist_ok=True)
    for relative in profile_manager.ProfileManager.ESSENTIAL_FILES:
        target = base_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("placeholder", encoding="utf-8")
    return base_dir


def test_browser_control_flow_captures_artifacts(static_site, tmp_path, monkeypatch):
    artifact_base = tmp_path / "artifacts_browser"
    _prepare_artifact_environment(monkeypatch, artifact_base)

    fake_profile_root = tmp_path / "fake_chrome_profile"
    _create_fake_profile(fake_profile_root)

    fake_profile_manager_cls = _fake_profile_manager_class(fake_profile_root)
    monkeypatch.setattr(git_script_automator, "ChromeProfileManager", fake_profile_manager_cls)
    monkeypatch.setattr(git_script_automator, "EdgeProfileManager", fake_profile_manager_cls)
    monkeypatch.setattr(git_script_automator.BrowserLauncher, "is_using_builtin_chromium", lambda self: True)

    action = {
        "name": "browser-control-demo",
        "type": "browser-control",
        "slowmo": 0,
        "flow": [
            {"action": "command", "url": static_site.url()},
            {"action": "screenshot", "prefix": "browser_demo", "full_page": True},
            {
                "action": "extract_content",
                "selectors": [
                    {"selector": "#message", "label": "message", "fields": ["text", "html"]},
                ],
            },
        ],
    }

    result = asyncio.run(
        execute_direct_browser_control(
            action,
            browser_type="chrome",
            headless=True,
            enable_recording=True,
        )
    )
    assert result, "Browser-control action did not complete successfully"

    run_dir = _assert_artifacts_created(artifact_base)
    manifest = run_dir / "manifest_v2.json"
    assert manifest.exists(), "Manifest file was not created for browser-control run"

    recorded = list((run_dir / "videos").glob("*.webm")) + list((run_dir / "videos").glob("*.mp4"))
    assert recorded, "No recorded video found for browser-control run"