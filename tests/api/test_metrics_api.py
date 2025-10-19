from fastapi.testclient import TestClient
import pytest

from src.api.app import create_fastapi_app
from src.api.app import create_ui
from src.metrics import get_metrics_collector, MetricType


def _make_app():
    demo = create_ui()

    class _Args:
        ip = "127.0.0.1"
        port = 7788

    return create_fastapi_app(demo, _Args())


@pytest.mark.ci_safe
def test_metrics_series_endpoints():
    # Arrange: seed some metrics
    collector = get_metrics_collector()
    series = collector.get_or_create_series("test.series.timer", MetricType.TIMER)
    for v in [10, 20, 30, 40, 50]:
        series.add_value(v, tags={"phase": "test"})

    app = _make_app()
    client = TestClient(app)

    # List series
    resp = client.get("/api/metrics/series")
    assert resp.status_code == 200
    data = resp.json()
    assert "test.series.timer" in data.get("series", [])

    # Get raw series values
    resp2 = client.get("/api/metrics/series/test.series.timer")
    assert resp2.status_code == 200
    payload = resp2.json()
    assert payload["name"] == "test.series.timer"
    assert payload["type"] == "timer"
    assert len(payload["values"]) >= 5

    # Summary
    resp3 = client.get("/api/metrics/series/test.series.timer/summary")
    assert resp3.status_code == 200
    summary = resp3.json()
    assert summary["name"] == "test.series.timer"
    assert summary["min"] == 10
    assert summary["max"] == 50
    assert 10 <= summary["p50"] <= 50
    assert 20 <= summary["p90"] <= 50
