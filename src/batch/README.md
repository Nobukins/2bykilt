# Batch Processing Module

The `src/batch` module provides CSV-driven batch execution functionality for automating browser tasks at scale.

## Overview

This module allows you to:
- Parse CSV files with configurable options
- Generate batch jobs for browser automation
- Track job execution status and progress
- Manage batch manifests and artifacts
- Retry failed jobs with exponential backoff
- Generate batch execution summaries

## Module Structure

```
src/batch/
├── __init__.py           # Package exports
├── engine.py             # Core BatchEngine class (2,073 lines)
├── exceptions.py         # Custom exceptions (39 lines)
├── models.py             # Data models (79 lines)
├── utils.py              # Utility functions (35 lines)
├── summary.py            # Batch summary generation
├── csv_utils.py          # CSV utilities
└── preview.py            # Batch preview functionality
```

## Quick Start

### Basic Usage

```python
from src.batch import BatchEngine, start_batch
from src.runtime.run_context import RunContext

# Create run context
run_context = RunContext()

# Option 1: Using BatchEngine directly
engine = BatchEngine(run_context)
manifest = engine.create_batch_jobs('customers.csv')
await engine.execute_batch_jobs(manifest.batch_id)

# Option 2: Using convenience function
manifest = await start_batch('customers.csv', run_context=run_context)
```

### With Configuration

```python
config = {
    'max_file_size_mb': 100,
    'chunk_size': 1000,
    'encoding': 'utf-8',
    'delimiter_fallback': ',',
    'allow_path_traversal': False,
    'validate_headers': True,
    'skip_empty_rows': True,
    'log_level': 'INFO',
}

engine = BatchEngine(run_context, config=config)
```

## Core Components

### BatchEngine

The main engine class that orchestrates batch processing.

**Key Methods**:
- `parse_csv(csv_path)` - Parse CSV file into row dictionaries
- `create_batch_jobs(csv_path)` - Generate batch jobs from CSV
- `execute_batch_jobs(batch_id)` - Execute all jobs in a batch
- `retry_batch_jobs(batch_id, job_ids)` - Retry failed jobs
- `get_batch_summary(batch_id)` - Get execution summary

### Data Models

#### BatchJob

Represents a single job in a batch.

```python
@dataclass
class BatchJob:
    job_id: str
    run_id: str
    row_data: Dict[str, Any]
    status: str = "pending"  # pending, running, completed, failed
    error_message: Optional[str] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
    batch_id: Optional[str] = None
    row_index: Optional[int] = None
    artifacts: Optional[List[Dict[str, Any]]] = None
```

#### BatchManifest

Tracks a batch execution.

```python
@dataclass
class BatchManifest:
    batch_id: str
    run_id: str
    csv_path: str
    total_jobs: int
    completed_jobs: int = 0
    failed_jobs: int = 0
    created_at: Optional[str] = None
    jobs: Optional[List[BatchJob]] = None
```

### Exceptions

```python
from src.batch.exceptions import (
    BatchEngineError,       # Base exception
    ConfigurationError,     # Configuration errors
    FileProcessingError,    # File processing errors
    SecurityError,          # Security violations
)
```

## Configuration Options

### File Processing

- **`max_file_size_mb`** (default: 500)  
  Maximum CSV file size in megabytes

- **`chunk_size`** (default: 1000)  
  Number of rows to process at once

- **`encoding`** (default: 'utf-8')  
  File encoding for CSV parsing

- **`delimiter_fallback`** (default: ',')  
  Fallback delimiter if auto-detection fails

### Security

- **`allow_path_traversal`** (default: True)  
  Allow access to files outside current directory

- **`validate_headers`** (default: True)  
  Validate CSV has headers

### Processing

- **`skip_empty_rows`** (default: True)  
  Skip rows with no data

- **`log_level`** (default: 'INFO')  
  Logging level (DEBUG, INFO, WARNING, ERROR)

### Environment Variables

Configuration can also be set via environment variables:

```bash
export BATCH_MAX_FILE_SIZE_MB=100
export BATCH_CHUNK_SIZE=1000
export BATCH_ENCODING=utf-8
export BATCH_ALLOW_PATH_TRAVERSAL=false
export BATCH_LOG_LEVEL=INFO
```

## Features

### CSV Parsing

- Automatic delimiter detection
- Configurable encoding
- Memory-efficient chunked processing
- Empty row filtering
- Header validation

### Security

- Path traversal prevention
- Sensitive directory protection
- File size limits
- MIME type validation

### Job Management

- Unique job ID generation
- Status tracking (pending, running, completed, failed)
- Progress callbacks
- Job artifact management

### Retry Logic

- Exponential backoff
- Configurable retry attempts
- Delay customization
- Maximum delay cap

### Batch Execution

- Sequential job processing
- Error handling and recovery
- Progress reporting
- Execution metrics

## Examples

### Parse CSV

```python
engine = BatchEngine(run_context)
rows = engine.parse_csv('data.csv')
print(f"Parsed {len(rows)} rows")
```

### Create and Execute Batch

```python
# Create batch
manifest = engine.create_batch_jobs('customers.csv')
print(f"Created batch {manifest.batch_id} with {manifest.total_jobs} jobs")

# Execute batch
result = await engine.execute_batch_jobs(manifest.batch_id)
print(f"Completed: {result['completed']}, Failed: {result['failed']}")
```

### Retry Failed Jobs

```python
# Get failed job IDs
manifest = engine._load_manifest_by_batch_id(batch_id)
failed_jobs = [job.job_id for job in manifest.jobs if job.status == 'failed']

# Retry with custom settings
result = engine.retry_batch_jobs(
    batch_id=batch_id,
    job_ids=failed_jobs,
    max_retries=5,
    retry_delay=2.0,
    backoff_factor=2.0
)
```

### Get Batch Summary

```python
summary = engine.get_batch_summary(batch_id)
if summary:
    print(f"Total: {summary.total_jobs}")
    print(f"Completed: {summary.completed_jobs}")
    print(f"Failed: {summary.failed_jobs}")
    print(f"Success Rate: {summary.success_rate:.1%}")
```

## Testing

Run batch module tests:

```bash
# All batch tests
pytest tests/batch/ -v

# Specific test modules
pytest tests/batch/test_batch_core.py -v
pytest tests/batch/test_batch_retry.py -v
pytest tests/batch/test_batch_execution.py -v
```

Current test coverage: **70%** (631/905 lines)

## Architecture

### Method Organization

The `BatchEngine` class is organized into logical sections:

1. **Initialization and Configuration**
   - `__init__()`, `_validate_config()`, `_configure_logging()`

2. **CSV Parsing Helper Methods**
   - `_check_security_for_path()`, `_validate_csv_file_exists_and_size()`
   - `_read_and_parse_csv_content()`, `parse_csv()`

3. **Manifest Management Methods**
   - `_load_manifest()`, `_save_manifest()`, `_find_manifest_file_for_batch()`
   - `_load_manifest_by_batch_id()`, `_search_batch_manifest_in_artifacts()`

4. **Job Status Management Methods**
   - `update_job_status()`, `add_row_artifact()`
   - `_update_single_job_status()`, `_find_job_by_id()`

5. **Retry Management Methods**
   - `retry_batch_jobs()`, `_validate_retry_parameters()`

6. **Batch Execution Methods**
   - `execute_batch_jobs()`, `execute_job_with_retry()`
   - `_simulate_job_execution()`

## Migration Guide

See [`docs/refactoring/PHASE_3_MIGRATION.md`](../../docs/refactoring/PHASE_3_MIGRATION.md) for:
- Module reorganization details
- API compatibility information
- Breaking changes (none)
- Migration steps

## Performance Considerations

- **Large Files**: Use `chunk_size` to control memory usage
- **Concurrent Execution**: Jobs execute sequentially by design
- **Retry Delays**: Configure backoff to balance speed vs. resource usage

## Troubleshooting

### Common Issues

1. **"CSV file too large"**
   - Increase `max_file_size_mb` in configuration
   - Or split the CSV file

2. **"Access denied: path traversal detected"**
   - Set `allow_path_traversal: True` in configuration
   - Or move CSV file to current directory

3. **"Invalid file encoding"**
   - Specify correct encoding in configuration
   - Convert file to UTF-8

4. **Job execution fails**
   - Check job error messages in manifest
   - Use `retry_batch_jobs()` to retry failed jobs

## Related Documentation

- [Phase 3 Migration Guide](../../docs/refactoring/PHASE_3_MIGRATION.md)
- [Phase 3 Analysis](../../docs/refactoring/PHASE_3_ANALYSIS.md)
- [Implementation Report](../../docs/refactoring/IMPLEMENTATION_REPORT_255.md)

## Contributing

When modifying this module:
1. Maintain 70%+ test coverage
2. Run all 81 batch tests
3. Follow existing method organization
4. Update this README for API changes
5. Maintain backward compatibility

## License

See project LICENSE file.
