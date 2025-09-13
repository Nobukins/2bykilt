"""
FastAPI router for Run Metrics API (Issue #59)

Endpoints
- GET /api/metrics/series            -> list series names
- GET /api/metrics/series/{name}     -> series raw values (JSON)
- GET /api/metrics/series/{name}/summary -> summary stats (min/max/avg/pXX)
"""
from __future__ import annotations

from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Query

from src.metrics.collector import get_metrics_collector, MetricSeries
from src.metrics.aggregator import compute_summary


def _parse_tag_filter(tag: Optional[str]) -> Optional[Dict[str, str]]:
    """Parse tag filter from query parameter (key=value format)."""
    if not tag:
        return None
    if "=" not in tag:
        raise HTTPException(status_code=400, detail="Tag filter must be in key=value format (e.g., phase=test)")
    k, v = tag.split("=", 1)
    return {k: v}


def _get_metric_series_or_404(name: str) -> MetricSeries:
    """Get metric series by name or raise 404."""
    collector = get_metrics_collector()
    series: Optional[MetricSeries] = collector.get_metric_series(name)
    if not series:
        raise HTTPException(status_code=404, detail=f"Series '{name}' not found")
    return series
router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.get("/series")
def list_series() -> Dict[str, Any]:
    collector = get_metrics_collector()
    return {"series": collector.list_series()}


@router.get("/series/{name}")
def get_series(name: str,
               tag: Optional[str] = Query(None, description="tag filter key=value")) -> Dict[str, Any]:
    series = _get_metric_series_or_404(name)
    tags_filter = _parse_tag_filter(tag)

    values = [v.to_dict() for v in series.get_values(tags_filter)]
    return {"name": name, "type": series.metric_type.value, "values": values}


@router.get("/series/{name}/summary")
def get_series_summary(name: str,
                       since_seconds: Optional[int] = Query(None, ge=1),
                       tag: Optional[str] = Query(None, description="tag filter key=value")) -> Dict[str, Any]:
    series = _get_metric_series_or_404(name)
    tags_filter = _parse_tag_filter(tag)

    summary = compute_summary(series, since_seconds=since_seconds, tags_filter=tags_filter)
    return {"name": name, **summary}


__all__ = ["router"]
