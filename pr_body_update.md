Implements Issue #59: Run Metrics API

## What's in this PR

### New API Endpoints
- **GET /api/metrics/series**: List all available metric series names
- **GET /api/metrics/series/{name}**: Retrieve metric values for a specific series with optional filtering
  - Query parameters: `tag_filter` (single key=value pair), `since_seconds` (integer)
- **GET /api/metrics/series/{name}/summary**: Get statistical summary for a metric series
  - Returns: min, max, avg, p50, p90, p95, p99 percentiles

### Core Implementation
- **src/metrics/aggregator.py**: Added `compute_summary()` method with percentile calculations using numpy
- **src/api/metrics_router.py**: New FastAPI router with endpoint implementations
  - Helper function `_parse_tag_filter()` for parsing single tag filter
  - Error handling for invalid series names and malformed filters
- **src/api/app.py**: Integrated metrics router into main FastAPI application

### Testing & Documentation
- **tests/api/test_metrics_api.py**: Comprehensive test suite covering all endpoints
  - Tests for series listing, value retrieval with filters, summary calculations
  - Uses FastAPI TestClient for integration testing
- **docs/observability/METRICS_API.md**: Complete API documentation
  - Endpoint specifications, request/response examples, error codes
  - Current limitations (single tag filter, no pagination)

### Dependencies & Configuration
- No new external dependencies added
- Updated `docs/roadmap/ISSUE_DEPENDENCIES.yml` to mark #59 as in-progress
- All changes are backward compatible

## Checks

### Dependencies Validation
- [x] No new dependencies added to `requirements.txt` or `pyproject.toml`
- [x] `docs/roadmap/ISSUE_DEPENDENCIES.yml` updated correctly (#59 marked in-progress)
- [x] Dependency graph validation passed (`scripts/validate_dependencies.py`)

### Testing
- [x] Unit tests added and passing locally (`pytest tests/api/test_metrics_api.py`)
- [x] Integration tests with FastAPI TestClient
- [x] Test coverage maintained (>80% overall)
- [x] No existing tests broken

### Idempotency & Safety
- [x] No generated artifacts or persistent state changes
- [x] API-only addition with read-only operations
- [x] Safe rollback: removal of router integration reverts changes
- [x] No breaking changes to existing APIs

### Documentation
- [x] API documentation added (`docs/observability/METRICS_API.md`)
- [x] Inline code documentation with type hints
- [x] Error handling documented
- [x] Current limitations clearly stated

## Follow-ups

### Testing Enhancements
- Expand test coverage for edge cases (empty series, malformed filters)
- Add performance tests for large metric datasets
- Integration tests with actual metric collection workflow

### API Improvements
- Consider pagination for large series responses
- Support multiple tag filters (currently limited to single key=value)
- Add rate limiting and caching considerations
- Streaming responses for very large datasets

### Monitoring & Observability
- Add metrics for API usage (request count, response times)
- Consider API versioning strategy for future changes

## Closes

- Closes: #59
- Refs: #184 (Phase2-07 tracker)

---

*Implementation follows project guidelines: minimal changes, comprehensive testing, full documentation, and dependency validation.*