"""
Metrics configuration and initialization for 2bykilt.

This module handles metrics configuration, initialization, and integration
with the main application.
"""

import os
from typing import Dict, Any, Optional
from pathlib import Path
from .collector import MetricsCollector, get_metrics_collector


class MetricsConfig:
    """Configuration for metrics collection."""

    def __init__(self,
                 enabled: bool = True,
                 storage_path: Optional[str] = None,
                 retention_hours: int = 24,
                 export_interval_minutes: int = 60,
                 system_metrics_interval_seconds: int = 60):
        self.enabled = enabled
        self.storage_path = storage_path or "artifacts/metrics"
        self.retention_seconds = retention_hours * 3600
        self.export_interval_seconds = export_interval_minutes * 60
        self.system_metrics_interval_seconds = system_metrics_interval_seconds

    @classmethod
    def from_env(cls) -> 'MetricsConfig':
        """Create configuration from environment variables."""
        return cls(
            enabled=os.getenv("METRICS_ENABLED", "true").lower() == "true",
            storage_path=os.getenv("METRICS_STORAGE_PATH", "artifacts/metrics"),
            retention_hours=int(os.getenv("METRICS_RETENTION_HOURS", "24")),
            export_interval_minutes=int(os.getenv("METRICS_EXPORT_INTERVAL_MINUTES", "60")),
            system_metrics_interval_seconds=int(os.getenv("METRICS_SYSTEM_INTERVAL_SECONDS", "60"))
        )

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'MetricsConfig':
        """Create configuration from dictionary."""
        return cls(
            enabled=config_dict.get("enabled", True),
            storage_path=config_dict.get("storage_path", "artifacts/metrics"),
            retention_hours=config_dict.get("retention_hours", 24),
            export_interval_minutes=config_dict.get("export_interval_minutes", 60),
            system_metrics_interval_seconds=config_dict.get("system_metrics_interval_seconds", 60)
        )


class MetricsManager:
    """Manager for metrics collection and lifecycle."""

    def __init__(self, config: Optional[MetricsConfig] = None):
        self.config = config or MetricsConfig.from_env()
        self.collector: Optional[MetricsCollector] = None
        self._initialized = False

    def initialize(self) -> None:
        """Initialize the metrics system."""
        if not self.config.enabled:
            return

        if self._initialized:
            return

        # Create collector
        self.collector = MetricsCollector(self.config.storage_path)

        # Set as global collector
        global _default_collector
        _default_collector = self.collector

        # Create initial metric series
        self._create_initial_series()

        self._initialized = True

    def _create_initial_series(self) -> None:
        """Create initial metric series."""
        if not self.collector:
            return

        # System metrics
        self.collector.create_series("system.cpu_percent", MetricType.GAUGE, self.config.retention_seconds)
        self.collector.create_series("system.memory_percent", MetricType.GAUGE, self.config.retention_seconds)
        self.collector.create_series("system.memory_used_mb", MetricType.GAUGE, self.config.retention_seconds)
        self.collector.create_series("system.process_memory_mb", MetricType.GAUGE, self.config.retention_seconds)
        self.collector.create_series("system.process_cpu_percent", MetricType.GAUGE, self.config.retention_seconds)

        # Job metrics
        self.collector.create_series("job.status_change", MetricType.COUNTER, self.config.retention_seconds)
        self.collector.create_series("job.total_count", MetricType.COUNTER, self.config.retention_seconds)
        self.collector.create_series("job.success_count", MetricType.COUNTER, self.config.retention_seconds)
        self.collector.create_series("job.failure_count", MetricType.COUNTER, self.config.retention_seconds)

        # Performance metrics
        self.collector.create_series("performance.execution_time", MetricType.TIMER, self.config.retention_seconds)
        self.collector.create_series("performance.memory_usage", MetricType.GAUGE, self.config.retention_seconds)

    def is_enabled(self) -> bool:
        """Check if metrics collection is enabled."""
        return self.config.enabled and self._initialized

    def get_collector(self) -> Optional[MetricsCollector]:
        """Get the metrics collector instance."""
        return self.collector

    def export_metrics(self, format_type: str = "json") -> Optional[str]:
        """Export current metrics."""
        if not self.collector:
            return None

        if format_type == "json":
            filepath = Path(self.config.storage_path) / "metrics_export.json"
            return self.collector.export_to_json(str(filepath))
        elif format_type == "csv":
            base_path = Path(self.config.storage_path) / "csv_export"
            return str(self.collector.export_to_csv(str(base_path)))

        return None

    def shutdown(self) -> None:
        """Shutdown the metrics system and export final data."""
        if not self.collector:
            return

        try:
            # Export final metrics
            self.export_metrics("json")
            self.export_metrics("csv")
        except Exception:
            # Ignore export errors during shutdown
            pass

        self._initialized = False


# Global metrics manager instance
_metrics_manager: Optional[MetricsManager] = None


def initialize_metrics(config: Optional[MetricsConfig] = None) -> MetricsManager:
    """Initialize the global metrics system."""
    global _metrics_manager

    if _metrics_manager is None:
        _metrics_manager = MetricsManager(config)
        _metrics_manager.initialize()

    return _metrics_manager


def get_metrics_manager() -> Optional[MetricsManager]:
    """Get the global metrics manager instance."""
    return _metrics_manager


def shutdown_metrics() -> None:
    """Shutdown the global metrics system."""
    global _metrics_manager

    if _metrics_manager:
        _metrics_manager.shutdown()
        _metrics_manager = None


# Import collector functions for convenience
from .collector import (
    get_metrics_collector,
    record_execution_time,
    record_memory_usage,
    record_job_status,
    get_system_metrics,
    record_system_metrics,
    MetricType,
    MetricValue,
    MetricSeries
)
