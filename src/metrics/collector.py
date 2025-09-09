"""
Metrics measurement foundation for 2bykilt.

This module provides the core metrics collection infrastructure for measuring
system performance, job execution statistics, and custom metrics.
"""

import time
import psutil
import threading
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import csv
import os
from pathlib import Path


class MetricType(Enum):
    """Types of metrics that can be collected."""
    COUNTER = "counter"  # Monotonically increasing value
    GAUGE = "gauge"     # Value that can go up or down
    HISTOGRAM = "histogram"  # Distribution of values
    TIMER = "timer"     # Duration measurement


@dataclass
class MetricValue:
    """Represents a single metric measurement."""
    name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    metric_type: MetricType = MetricType.GAUGE

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "tags": self.tags,
            "type": self.metric_type.value
        }


@dataclass
class MetricSeries:
    """Time series data for a specific metric."""
    name: str
    metric_type: MetricType
    values: List[MetricValue] = field(default_factory=list)
    max_age_seconds: int = 3600  # 1 hour default retention

    def add_value(self, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Add a new value to the series."""
        metric_value = MetricValue(
            name=self.name,
            value=value,
            timestamp=datetime.now(),
            tags=tags or {},
            metric_type=self.metric_type
        )
        self.values.append(metric_value)
        self._cleanup_old_values()

    def _cleanup_old_values(self) -> None:
        """Remove values older than max_age_seconds."""
        cutoff_time = datetime.now().timestamp() - self.max_age_seconds
        self.values = [
            v for v in self.values
            if v.timestamp.timestamp() > cutoff_time
        ]

    def get_values(self, tags_filter: Optional[Dict[str, str]] = None) -> List[MetricValue]:
        """Get values, optionally filtered by tags."""
        if not tags_filter:
            return self.values.copy()

        return [
            v for v in self.values
            if all(v.tags.get(k) == v for k, v in tags_filter.items())
        ]

    def get_latest_value(self, tags_filter: Optional[Dict[str, str]] = None) -> Optional[MetricValue]:
        """Get the most recent value."""
        values = self.get_values(tags_filter)
        return values[-1] if values else None


class MetricsCollector:
    """Core metrics collection and storage manager."""

    def __init__(self, storage_path: Optional[str] = None):
        self.series: Dict[str, MetricSeries] = {}
        self.storage_path = Path(storage_path) if storage_path else None
        self._lock = threading.Lock()

        # Create storage directory if specified
        if self.storage_path:
            self.storage_path.mkdir(parents=True, exist_ok=True)

    def create_series(self, name: str, metric_type: MetricType,
                     max_age_seconds: int = 3600) -> MetricSeries:
        """Create a new metric series."""
        with self._lock:
            if name in self.series:
                raise ValueError(f"Metric series '{name}' already exists")

            series = MetricSeries(name, metric_type, max_age_seconds=max_age_seconds)
            self.series[name] = series
            return series

    def get_or_create_series(self, name: str, metric_type: MetricType,
                           max_age_seconds: int = 3600) -> MetricSeries:
        """Get existing series or create new one."""
        with self._lock:
            if name not in self.series:
                self.series[name] = MetricSeries(name, metric_type, max_age_seconds=max_age_seconds)
            return self.series[name]

    def record_metric(self, name: str, value: float,
                     tags: Optional[Dict[str, str]] = None,
                     metric_type: MetricType = MetricType.GAUGE) -> None:
        """Record a metric value."""
        series = self.get_or_create_series(name, metric_type)
        series.add_value(value, tags)

    def get_metric_series(self, name: str) -> Optional[MetricSeries]:
        """Get a metric series by name."""
        return self.series.get(name)

    def list_series(self) -> List[str]:
        """List all metric series names."""
        return list(self.series.keys())

    def export_to_json(self, filepath: Optional[str] = None) -> str:
        """Export all metrics to JSON format."""
        data = {}
        for name, series in self.series.items():
            data[name] = {
                "type": series.metric_type.value,
                "values": [v.to_dict() for v in series.values]
            }

        json_str = json.dumps(data, indent=2, ensure_ascii=False)

        if filepath:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(json_str)

        return json_str

    def export_to_csv(self, base_filepath: Optional[str] = None) -> List[str]:
        """Export all metrics to CSV files."""
        exported_files = []

        for name, series in self.series.items():
            if not series.values:
                continue

            filename = f"{name}.csv"
            if base_filepath:
                filepath = Path(base_filepath) / filename
            else:
                filepath = Path(filename)

            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)

                # Write header
                header = ["timestamp", "value"]
                tag_keys = set()
                for value in series.values:
                    tag_keys.update(value.tags.keys())
                header.extend(sorted(tag_keys))
                writer.writerow(header)

                # Write data
                for value in series.values:
                    row = [value.timestamp.isoformat(), value.value]
                    for key in sorted(tag_keys):
                        row.append(value.tags.get(key, ""))
                    writer.writerow(row)

            exported_files.append(str(filepath))

        return exported_files

    def clear_all(self) -> None:
        """Clear all metric data."""
        with self._lock:
            self.series.clear()


# Global metrics collector instance
_default_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance."""
    global _default_collector
    if _default_collector is None:
        _default_collector = MetricsCollector()
    return _default_collector


def record_execution_time(func: Callable) -> Callable:
    """Decorator to record function execution time."""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time

            collector = get_metrics_collector()
            collector.record_metric(
                f"{func.__module__}.{func.__name__}.execution_time",
                execution_time,
                tags={"function": func.__name__, "module": func.__module__},
                metric_type=MetricType.TIMER
            )

            return result
        except Exception as e:
            execution_time = time.time() - start_time

            collector = get_metrics_collector()
            collector.record_metric(
                f"{func.__module__}.{func.__name__}.execution_time",
                execution_time,
                tags={"function": func.__name__, "module": func.__module__, "error": str(type(e).__name__)},
                metric_type=MetricType.TIMER
            )

            raise

    return wrapper


def record_memory_usage(func: Callable) -> Callable:
    """Decorator to record function memory usage."""
    def wrapper(*args, **kwargs):
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        try:
            result = func(*args, **kwargs)

            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_delta = final_memory - initial_memory

            collector = get_metrics_collector()
            collector.record_metric(
                f"{func.__module__}.{func.__name__}.memory_usage",
                memory_delta,
                tags={"function": func.__name__, "module": func.__module__},
                metric_type=MetricType.GAUGE
            )

            return result
        except Exception as e:
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_delta = final_memory - initial_memory

            collector = get_metrics_collector()
            collector.record_metric(
                f"{func.__module__}.{func.__name__}.memory_usage",
                memory_delta,
                tags={"function": func.__name__, "module": func.__module__, "error": str(type(e).__name__)},
                metric_type=MetricType.GAUGE
            )

            raise

    return wrapper


def record_job_status(job_id: str, status: str, run_id: Optional[str] = None) -> None:
    """Record job execution status."""
    collector = get_metrics_collector()

    # Record status change
    collector.record_metric(
        "job.status_change",
        1,
        tags={"job_id": job_id, "run_id": run_id or "", "status": status},
        metric_type=MetricType.COUNTER
    )

    # Update job status gauge
    status_value = {"pending": 0, "running": 1, "completed": 2, "failed": 3}.get(status, -1)
    collector.record_metric(
        f"job.{job_id}.status",
        status_value,
        tags={"job_id": job_id, "run_id": run_id or ""},
        metric_type=MetricType.GAUGE
    )


def get_system_metrics() -> Dict[str, float]:
    """Get current system metrics."""
    process = psutil.Process()

    return {
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "memory_percent": psutil.virtual_memory().percent,
        "memory_used_mb": psutil.virtual_memory().used / 1024 / 1024,
        "process_memory_mb": process.memory_info().rss / 1024 / 1024,
        "process_cpu_percent": process.cpu_percent(interval=0.1),
    }


def record_system_metrics() -> None:
    """Record current system metrics."""
    metrics = get_system_metrics()
    collector = get_metrics_collector()

    for name, value in metrics.items():
        collector.record_metric(f"system.{name}", value, metric_type=MetricType.GAUGE)
