# Phase 3 Migration Guide: Batch Engine Refactoring

**Date**: 2025-10-16  
**Issue**: #328  
**Branch**: `refactor/issue-328-split-batch-engine`

## Overview

Phase 3 focused on refactoring `src/batch/engine.py` to improve code organization, maintainability, and readability. The primary goal was to extract reusable components and reduce cognitive complexity of large methods.

## Changes Summary

### New Modules Created

#### 1. `src/batch/exceptions.py` (39 lines)
**Purpose**: Centralized exception handling for batch processing

**Exported Classes**:
- `BatchEngineError` - Base exception
- `ConfigurationError` - Configuration validation errors
- `FileProcessingError` - File processing errors
- `SecurityError` - Security violation errors

**Migration**:
```python
# Before
from src.batch.engine import BatchEngineError

# After (both work, backward compatible)
from src.batch.engine import BatchEngineError
from src.batch.exceptions import BatchEngineError
from src.batch import BatchEngineError  # Also works
```

#### 2. `src/batch/models.py` (79 lines)
**Purpose**: Data models for batch processing

**Exported Classes**:
- `BatchJob` - Individual job data structure
- `BatchManifest` - Batch manifest data structure

**Exported Constants**:
- `BATCH_MANIFEST_FILENAME = "batch_manifest.json"`
- `JOBS_DIRNAME = "jobs"`

**Migration**:
```python
# Before
from src.batch.engine import BatchJob, BatchManifest

# After (both work, backward compatible)
from src.batch.engine import BatchJob, BatchManifest
from src.batch.models import BatchJob, BatchManifest
from src.batch import BatchJob, BatchManifest  # Also works
```

#### 3. `src/batch/utils.py` (35 lines)
**Purpose**: Utility functions for batch processing

**Exported Functions**:
- `to_portable_relpath(p: Path) -> str` - Convert Path to portable relative path

**Migration**:
```python
# Before (was a static method)
from src.batch.engine import BatchEngine
path_str = BatchEngine._to_portable_relpath(path)

# After
from src.batch.utils import to_portable_relpath
path_str = to_portable_relpath(path)

# Also available from package level
from src.batch import to_portable_relpath
```

### BatchEngine Internal Refactoring

#### Extracted Helper Methods

The following private methods were extracted to reduce complexity:

1. **`_check_security_for_path(csv_path_obj, csv_path)`**
   - Separated from `parse_csv()`
   - Handles path traversal and sensitive directory checks
   - ~60 lines

2. **`_validate_csv_file_exists_and_size(csv_path_obj, csv_path)`**
   - Separated from `parse_csv()`
   - Validates file existence, size, and type
   - ~35 lines

3. **`_read_and_parse_csv_content(csv_path_obj, csv_path, chunk_size)`**
   - Separated from `parse_csv()`
   - Handles actual CSV reading and parsing
   - ~70 lines

#### Simplified Methods

**`parse_csv()` Method**:
- **Before**: ~160 lines, cognitive complexity 36
- **After**: ~10 lines, cognitive complexity ~5
- **Improvement**: 86% reduction in complexity

```python
# New simplified structure
def parse_csv(self, csv_path: str, chunk_size: int = 1000) -> List[Dict[str, Any]]:
    csv_path_obj = Path(csv_path).resolve()
    
    # Security check
    self._check_security_for_path(csv_path_obj, csv_path)
    
    # Validation
    self._validate_csv_file_exists_and_size(csv_path_obj, csv_path)
    
    # Parse
    return self._read_and_parse_csv_content(csv_path_obj, csv_path, chunk_size)
```

#### Section Organization

Added clear section headers in `engine.py`:
- `CSV Parsing Helper Methods`
- `Manifest Management Methods`
- `Job Status Management Methods`
- `Retry Management Methods`
- `Batch Execution Methods`

## Metrics

### Code Size

| File | Before | After | Change |
|------|--------|-------|--------|
| `engine.py` | 2,112 lines | 2,073 lines | -39 lines (1.8%) |
| New modules | 0 lines | 153 lines | +153 lines |
| **Total** | 2,112 lines | 2,226 lines | +114 lines (5.4%) |

**Note**: Total lines increased due to:
- Method extraction overhead (docstrings, signatures)
- Section comments for organization
- Improved code clarity trades off brevity

### Quality Improvements

- **Cognitive Complexity**: Reduced from 36 to 5 in `parse_csv()` (86% improvement)
- **Test Coverage**: Maintained at 70% (631/905 lines)
- **Test Suite**: All 81 tests passing (100%)
- **Backward Compatibility**: 100% maintained

## Breaking Changes

**None**. All changes are backward compatible.

## API Compatibility

### Public API (Unchanged)

```python
# All existing imports continue to work
from src.batch import (
    BatchEngine,
    BatchJob,
    BatchManifest,
    BatchSummary,
    start_batch,
    generate_batch_summary,
    # Exception classes
    BatchEngineError,
    ConfigurationError,
    FileProcessingError,
    SecurityError,
)

# All BatchEngine methods unchanged
engine = BatchEngine(run_context, config)
rows = engine.parse_csv('data.csv')
manifest = engine.create_batch_jobs('data.csv')
```

### New Recommended Imports

```python
# For better code organization, prefer:
from src.batch.exceptions import ConfigurationError
from src.batch.models import BatchJob, BatchManifest
from src.batch.utils import to_portable_relpath
```

## Benefits

### 1. Improved Readability
- Methods have clear, single responsibilities
- Section headers guide navigation
- Reduced cognitive load when reading code

### 2. Better Testability
- Extracted methods can be unit tested independently
- Easier to mock and test edge cases

### 3. Easier Maintenance
- Changes to security logic isolated in one method
- Validation logic separated from parsing logic
- Clear boundaries between concerns

### 4. Reusability
- Utility functions available across the codebase
- Models and exceptions can be imported independently

## Migration Steps

### For External Users

**No action required**. All existing code continues to work.

### For Internal Developers

**Optional**: Update imports to use new modules for better organization:

```python
# Old style (still works)
from src.batch.engine import BatchEngineError, FileProcessingError

# New style (recommended)
from src.batch.exceptions import BatchEngineError, FileProcessingError
```

## Testing

All Phase 2 tests continue to pass:
```bash
pytest tests/batch/test_batch_*.py -v
# 81 passed (100%)
```

## Future Work

Phase 3 established the foundation. Future phases may consider:

1. **Phase 4**: Further method extraction
   - Manifest management methods
   - Retry handler methods
   - Job execution methods

2. **Phase 5**: Consider class extraction
   - `ManifestManager` class
   - `JobManager` class
   - `RetryHandler` class

## Related Issues

- Parent Issue: #264 - Overall refactoring plan
- Phase 1: #326 - bykilt.py split (completed)
- Phase 2: #327 - test_batch_engine.py split (completed)
- Phase 3: #328 - batch/engine.py refactoring (current)
- Phase 4: #329 - Further refactoring (planned)

## Commit History

1. `a0168a7` - Step 1-2: Extract exceptions.py and models.py
2. `f168b5b` - Step 3: Extract utility functions to utils.py
3. `611bd0b` - Step 4: Extract security check method from parse_csv
4. `8ec2edf` - Step 5: Extract CSV parsing logic into helper methods
5. `07c80fe` - Step 6: Add section comments for method organization

## Questions or Issues?

Please refer to:
- GitHub Issue #328
- `docs/refactoring/PHASE_3_ANALYSIS.md` - Initial analysis
- `docs/refactoring/IMPLEMENTATION_REPORT_255.md` - Earlier refactoring context
