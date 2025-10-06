"""Browser engine telemetry helpers.

This module bridges browser engine execution to the metrics foundation
(`src.metrics`). It records launch outcomes, action-level telemetry, and
session summaries so that CDP/Playwright parity and rollout metrics can be
observed, as required by the modernization plan (section 5.5).
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple, TYPE_CHECKING

from .browser_engine import ActionResult, EngineMetrics, LaunchContext

if TYPE_CHECKING:  # pragma: no cover - used only for typing
    from src.metrics.collector import MetricsCollector


class EngineTelemetryRecorder:
    """Record browser engine telemetry into the metrics pipeline."""

    ACTION_DURATION_MS = "browser_engine.action.duration_ms"
    ACTION_SUCCESS_TOTAL = "browser_engine.action.success_total"
    ACTION_FAILURE_TOTAL = "browser_engine.action.failure_total"
    ACTION_ARTIFACT_COUNT = "browser_engine.action.artifact_count"

    LAUNCH_SUCCESS_TOTAL = "browser_engine.launch.total"
    LAUNCH_FAILURE_TOTAL = "browser_engine.launch.failure_total"

    SESSION_TOTAL_ACTIONS = "browser_engine.session.total_actions"
    SESSION_FAILED_ACTIONS = "browser_engine.session.failed_actions"
    SESSION_DURATION_MS = "browser_engine.session.duration_ms"
    SESSION_AVG_LATENCY_MS = "browser_engine.session.avg_latency_ms"
    SESSION_ARTIFACT_TOTAL = "browser_engine.session.artifacts_captured"

    @classmethod
    def record_launch_success(cls, engine_type: str, context: LaunchContext) -> None:
        metrics = cls._get_metrics()
        if not metrics:
            return

        collector, metric_type = metrics
        tags = {
            "engine": engine_type,
            "browser_type": context.browser_type,
            "headless": cls._bool_tag(context.headless),
            "trace_enabled": cls._bool_tag(context.trace_enabled),
            "sandbox_mode": cls._bool_tag(context.sandbox_mode),
        }

        collector.record_metric(
            name=cls.LAUNCH_SUCCESS_TOTAL,
            value=1,
            metric_type=metric_type.COUNTER,
            tags=tags,
        )

    @classmethod
    def record_launch_failure(cls, engine_type: str, error: Exception) -> None:
        metrics = cls._get_metrics()
        if not metrics:
            return

        collector, metric_type = metrics
        tags = {
            "engine": engine_type,
            "error_kind": cls._derive_error_kind(error),
        }

        collector.record_metric(
            name=cls.LAUNCH_FAILURE_TOTAL,
            value=1,
            metric_type=metric_type.COUNTER,
            tags=tags,
        )

    @classmethod
    def record_action(cls, engine_type: str, result: ActionResult) -> None:
        metrics = cls._get_metrics()
        if not metrics:
            return

        collector, metric_type = metrics
        base_tags = {
            "engine": engine_type,
            "action": result.action_type,
            "success": cls._bool_tag(result.success),
        }

        collector.record_metric(
            name=cls.ACTION_DURATION_MS,
            value=result.duration_ms,
            metric_type=metric_type.HISTOGRAM,
            tags=base_tags,
        )

        if result.success:
            collector.record_metric(
                name=cls.ACTION_SUCCESS_TOTAL,
                value=1,
                metric_type=metric_type.COUNTER,
                tags={k: v for k, v in base_tags.items() if k != "success"},
            )
        else:
            failure_tags = {k: v for k, v in base_tags.items() if k != "success"}
            failure_tags["error_kind"] = cls._derive_error_string(result.error)
            collector.record_metric(
                name=cls.ACTION_FAILURE_TOTAL,
                value=1,
                metric_type=metric_type.COUNTER,
                tags=failure_tags,
            )

        if result.artifacts:
            collector.record_metric(
                name=cls.ACTION_ARTIFACT_COUNT,
                value=float(len(result.artifacts)),
                metric_type=metric_type.GAUGE,
                tags={k: v for k, v in base_tags.items() if k != "success"},
            )

    @classmethod
    def record_session_summary(cls, engine_type: str, metrics_snapshot: EngineMetrics) -> None:
        metrics = cls._get_metrics()
        if not metrics:
            return

        collector, metric_type = metrics
        tags = {"engine": engine_type}

        collector.record_metric(
            name=cls.SESSION_TOTAL_ACTIONS,
            value=float(metrics_snapshot.total_actions),
            metric_type=metric_type.GAUGE,
            tags=tags,
        )
        collector.record_metric(
            name=cls.SESSION_FAILED_ACTIONS,
            value=float(metrics_snapshot.failed_actions),
            metric_type=metric_type.GAUGE,
            tags=tags,
        )

        if metrics_snapshot.avg_latency_ms:
            collector.record_metric(
                name=cls.SESSION_AVG_LATENCY_MS,
                value=metrics_snapshot.avg_latency_ms,
                metric_type=metric_type.GAUGE,
                tags=tags,
            )

        collector.record_metric(
            name=cls.SESSION_ARTIFACT_TOTAL,
            value=float(metrics_snapshot.artifacts_captured),
            metric_type=metric_type.GAUGE,
            tags=tags,
        )

        duration_ms = cls._compute_duration_ms(metrics_snapshot)
        if duration_ms is not None:
            collector.record_metric(
                name=cls.SESSION_DURATION_MS,
                value=duration_ms,
                metric_type=metric_type.GAUGE,
                tags=tags,
            )

    @classmethod
    def _compute_duration_ms(cls, metrics_snapshot: EngineMetrics) -> Optional[float]:
        if not metrics_snapshot.started_at:
            return None

        end_time = metrics_snapshot.shutdown_at or datetime.now(timezone.utc)
        delta = end_time - metrics_snapshot.started_at
        return max(delta.total_seconds() * 1000, 0.0)

    @classmethod
    def _get_metrics(cls) -> Optional[Tuple["MetricsCollector", Any]]:
        try:
            from src.metrics import get_metrics_collector, get_metrics_manager, MetricType
        except Exception:
            return None

        manager = get_metrics_manager()
        if manager is None or not manager.is_enabled():
            return None

        collector = get_metrics_collector()
        if collector is None:
            return None

        return collector, MetricType

    @staticmethod
    def _bool_tag(value: bool) -> str:
        return "true" if value else "false"

    @staticmethod
    def _derive_error_kind(error: Exception) -> str:
        if not error:
            return "unknown"
        name = type(error).__name__
        return EngineTelemetryRecorder._normalize_tag(name)

    @staticmethod
    def _derive_error_string(message: Optional[str]) -> str:
        if not message:
            return "unknown"
        # Take only the first segment to avoid excessive cardinality
        normalized = message.splitlines()[0][:64]
        return EngineTelemetryRecorder._normalize_tag(normalized or "unknown")

    @staticmethod
    def _normalize_tag(raw: str) -> str:
        normalized = raw.strip().lower().replace(" ", "_")
        allowed = "abcdefghijklmnopqrstuvwxyz0123456789_-"
        normalized = "".join(ch for ch in normalized if ch in allowed)
        return normalized[:64] or "unknown"

    @classmethod
    def snapshot_to_dict(cls, metrics_snapshot: EngineMetrics) -> Dict[str, Any]:
        """Expose metrics snapshot values for debugging or future exports."""
        return asdict(metrics_snapshot)
