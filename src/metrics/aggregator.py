"""
Metrics aggregation helpers (Issue #59: Run Metrics API)

Provides basic summaries for numeric metric series, including percentiles.
"""
from __future__ import annotations

from typing import Dict, Optional, List

import math

from .collector import MetricSeries, MetricValue, MetricType


def _filtered_values(series: MetricSeries, since_seconds: Optional[int] = None,
                     tags_filter: Optional[Dict[str, str]] = None) -> List[MetricValue]:
    values = series.get_values(tags_filter)
    if since_seconds is not None and since_seconds > 0:
        if series.values:
            cutoff = max(v.timestamp.timestamp() for v in series.values) - since_seconds
        else:
            cutoff = 0
        values = [v for v in values if v.timestamp.timestamp() >= cutoff]
    return values


def compute_summary(series: MetricSeries, *, since_seconds: Optional[int] = None,
                    tags_filter: Optional[Dict[str, str]] = None) -> Dict[str, float]:
    """Compute summary statistics for a metric series.

    For TIMER/HISTOGRAM/GAUGE metrics, returns min/max/avg and percentiles.
    For COUNTER, treats each value as a unit event and reports count only.
    """
    vals = _filtered_values(series, since_seconds, tags_filter)
    numeric = [float(v.value) for v in vals]

    if not numeric:
        return {
            "count": 0,
            "min": 0.0,
            "max": 0.0,
            "avg": 0.0,
            "p50": 0.0,
            "p90": 0.0,
            "p95": 0.0,
            "p99": 0.0,
            "type": series.metric_type.value,
        }

    n = len(numeric)
    s_min = min(numeric)
    s_max = max(numeric)
    s_avg = sum(numeric) / n

    sorted_vals = sorted(numeric)

    def pct(p: float) -> float:
        if n == 1:
            return sorted_vals[0]
        # nearest-rank method
        k = max(1, int(math.ceil(p / 100 * n)))
        return sorted_vals[k - 1]

    return {
        "count": float(n) if series.metric_type == MetricType.COUNTER else n,
        "min": s_min,
        "max": s_max,
        "avg": s_avg,
        "p50": pct(50),
        "p90": pct(90),
        "p95": pct(95),
        "p99": pct(99),
        "type": series.metric_type.value,
    }


__all__ = ["compute_summary"]
