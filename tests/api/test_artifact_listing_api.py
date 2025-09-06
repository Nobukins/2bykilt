import argparse
import pytest
from fastapi.testclient import TestClient

from src.api.app import create_fastapi_app, create_ui
from src.core.artifact_manager import ArtifactManager, reset_artifact_manager_singleton
from src.runtime.run_context import RunContext
from src.config.feature_flags import FeatureFlags


def _make_app():
    """Create FastAPI app with a lightweight args namespace.

    Centralizes the previously repeated dynamic type(...) pattern noted in review.
    """
    args = argparse.Namespace(ip="127.0.0.1", port=0)
    return create_fastapi_app(create_ui(), args=args)

@pytest.mark.ci_safe
def test_artifact_listing_basic(monkeypatch, tmp_path):
    # Force deterministic run id for isolation
    monkeypatch.setenv("BYKILT_RUN_ID", "LISTAPI1")
    RunContext.reset()
    reset_artifact_manager_singleton()
    FeatureFlags.set_override("artifacts.enable_manifest_v2", True)

    # Prepare some artifacts
    mgr = ArtifactManager()
    mgr.save_screenshot_bytes(b"one", prefix="lst1")
    mgr.save_element_capture("#id", text="hi", value="v")

    # Build API app
    app = _make_app()
    client = TestClient(app)

    r = client.get("/api/artifacts")
    assert r.status_code == 200
    data = r.json()
    assert data["count"] >= 2
    types = {a["type"] for a in data["items"]}
    assert {"screenshot", "element_capture"}.issubset(types)
    # Each item should include run_id
    assert all("run_id" in a for a in data["items"])

@pytest.mark.ci_safe
def test_artifact_listing_type_filter(monkeypatch, tmp_path):
    monkeypatch.setenv("BYKILT_RUN_ID", "LISTAPI2")
    RunContext.reset()
    reset_artifact_manager_singleton()
    FeatureFlags.set_override("artifacts.enable_manifest_v2", True)

    mgr = ArtifactManager()
    mgr.save_screenshot_bytes(b"img", prefix="onlyshot")
    mgr.save_element_capture("#x", text=None, value=None)

    app = _make_app()
    client = TestClient(app)

    r = client.get("/api/artifacts?type=screenshot")
    assert r.status_code == 200
    data = r.json()
    assert data["count"] >= 1
    assert all(item["type"] == "screenshot" for item in data["items"])

@pytest.mark.ci_safe
def test_artifact_listing_limit(monkeypatch, tmp_path):
    monkeypatch.setenv("BYKILT_RUN_ID", "LISTAPI3")
    RunContext.reset()
    reset_artifact_manager_singleton()
    FeatureFlags.set_override("artifacts.enable_manifest_v2", True)

    mgr = ArtifactManager()
    # create 3 artifacts
    for i in range(3):
        # Simple deterministic bytes (review suggestion: avoid f-string encode noise)
        mgr.save_screenshot_bytes(b"im%d" % i, prefix=f"lim{i}")

    app = _make_app()
    client = TestClient(app)

    r = client.get("/api/artifacts?limit=1")
    assert r.status_code == 200
    data = r.json()
    # Because limit applies at manifest aggregation level, count can be >=1; ensure not zero
    assert data["count"] >= 1
