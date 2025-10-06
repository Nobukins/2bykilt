import pytest

from src.browser.engine.browser_engine import (
    BrowserEngine,
    EngineType,
    LaunchContext,
    ActionResult,
)
from src.metrics import (
    MetricsConfig,
    initialize_metrics,
    get_metrics_collector,
    shutdown_metrics,
)


class DummyEngine(BrowserEngine):
    """Minimal BrowserEngine implementation for telemetry tests."""

    def __init__(self):
        super().__init__(EngineType.PLAYWRIGHT)

    async def launch(self, context: LaunchContext) -> None:
        self._on_launch_success(context)

    async def navigate(self, url: str, wait_until: str = "domcontentloaded") -> ActionResult:
        raise NotImplementedError("DummyEngine does not implement navigate")

    async def dispatch(self, action):
        raise NotImplementedError("DummyEngine does not implement dispatch")

    async def capture_artifacts(self, artifact_types):
        return {}

    async def shutdown(self, capture_final_state: bool = True) -> None:
        self._on_shutdown()


@pytest.mark.asyncio
async def test_engine_telemetry_records_metrics(tmp_path):
    config = MetricsConfig(enabled=True, storage_path=str(tmp_path / "metrics"))
    initialize_metrics(config)

    try:
        engine = DummyEngine()
        await engine.launch(LaunchContext())

        success_result = ActionResult(
            success=True,
            action_type="navigate",
            duration_ms=120.0,
            artifacts={"trace": "path"},
        )
        engine._update_metrics(success_result)

        failure_result = ActionResult(
            success=False,
            action_type="click",
            duration_ms=80.0,
            error="Timeout reached",
        )
        engine._update_metrics(failure_result)

        await engine.shutdown()

        collector = get_metrics_collector()

        duration_series = collector.get_metric_series("browser_engine.action.duration_ms")
        assert duration_series is not None
        assert duration_series.get_values({
            "engine": "playwright",
            "action": "navigate",
            "success": "true",
        })

        success_series = collector.get_metric_series("browser_engine.action.success_total")
        assert success_series is not None
        success_value = success_series.get_latest_value({
            "engine": "playwright",
            "action": "navigate",
        })
        assert success_value is not None and success_value.value == 1

        failure_series = collector.get_metric_series("browser_engine.action.failure_total")
        assert failure_series is not None
        failure_value = failure_series.get_latest_value({
            "engine": "playwright",
            "action": "click",
        })
        assert failure_value is not None and failure_value.value == 1

        session_total = collector.get_metric_series("browser_engine.session.total_actions")
        assert session_total is not None
        total_value = session_total.get_latest_value({"engine": "playwright"})
        assert total_value is not None and total_value.value == 2

        avg_latency = collector.get_metric_series("browser_engine.session.avg_latency_ms")
        assert avg_latency is not None
        avg_value = avg_latency.get_latest_value({"engine": "playwright"})
        assert avg_value is not None and avg_value.value == pytest.approx(100.0)

        session_duration = collector.get_metric_series("browser_engine.session.duration_ms")
        assert session_duration is not None
        duration_value = session_duration.get_latest_value({"engine": "playwright"})
        assert duration_value is not None and duration_value.value >= 0

    finally:
        shutdown_metrics()
