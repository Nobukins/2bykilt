# Secret Masking Extension (Issue #60)

The Secret Masking Extension provides automatic detection and masking of sensitive information in log output to prevent accidental exposure of secrets.

## Features

- **Automatic Pattern Detection**: Detects common secret patterns including API keys, passwords, tokens, and authorization headers
- **Feature Flag Control**: Can be enabled/disabled via configuration
- **Minimal Performance Impact**: Processing overhead <5ms per log entry
- **Hook-based Integration**: Integrates seamlessly with existing logging infrastructure
- **No Breaking Changes**: Existing logging functionality remains unaffected

## Supported Secret Patterns

### API Keys
- **Prefixed Keys**: `sk-`, `pk-`, `xoxp-`, `xoxb-` followed by 16+ alphanumeric characters
- Example: `sk-1234567890abcdefgh` → `***MASKED_API_KEY***`

### Passwords
- **Field Patterns**: `password=`, `passwd=`, `pwd=` followed by 8+ characters
- Example: `password=secret123` → `password=***MASKED_PASSWORD***`

### Tokens
- **Bearer Tokens**: `Bearer` followed by 16+ alphanumeric characters
- **Authorization Headers**: `Authorization:` followed by 16+ characters
- Example: `Bearer abc123def456789` → `Bearer ***MASKED_TOKEN***`

### Generic Secrets
- **Long Strings**: 32+ character alphanumeric strings
- Example: `1234567890abcdefghijklmnopqrstuvwxyz` → `***MASKED_GENERIC***`

### Sensitive Keys
Any dictionary key containing these terms (case-insensitive) will have its value masked:
- `password`, `secret`, `token`, `key`, `credential`
- `auth`, `session`, `cookie`, `private`, `api_key`
- `access_token`, `refresh_token`, `client_secret`

## Configuration

### Feature Flag

Secret masking is controlled by the feature flag `security.secret_masking_enabled` in `config/feature_flags.yaml`:

```yaml
security.secret_masking_enabled:
  description: "秘密情報マスキング機能を有効化 (#60)"
  type: bool
  default: true
```

### Environment Override

You can override the feature flag using environment variables:
```bash
export BYKILT_FLAG_SECURITY_SECRET_MASKING_ENABLED=false
```

## Usage

### Basic Integration with JsonlLogger

```python
from src.logging.jsonl_logger import JsonlLogger
from src.security.secret_masker import create_masking_hook

# Create logger
logger = JsonlLogger.get(component="my_app")

# Register the masking hook
masking_hook = create_masking_hook()
logger.register_hook(masking_hook)

# Log with sensitive information - it will be automatically masked
logger.info(
    "User authentication with password=secret123",
    api_key="sk-1234567890abcdefgh",
    user_data={
        "password": "userpassword",
        "token": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9"
    }
)
```

### Direct Usage of SecretMasker

```python
from src.security.secret_masker import SecretMasker

# Create masker instance
masker = SecretMasker.from_feature_flags()

# Mask text
masked_text = masker.mask_text("password=secret123")
# Result: "password=***MASKED_PASSWORD***"

# Mask data structures
data = {
    "username": "john",
    "password": "secret",
    "config": {"api_key": "sk-1234567890abcdef"}
}
masked_data = masker.mask_data(data)
# Result: {
#     "username": "john",
#     "password": "***MASKED***",
#     "config": {"api_key": "***MASKED***"}
# }
```

### Custom Masker Configuration

```python
from src.security.secret_masker import SecretMasker

# Create with explicit enabled state
masker = SecretMasker(enabled=False)  # Disable masking

# Mask log record (for hook usage)
log_record = {"msg": "password=secret", "api_key": "sk-123"}
masked_record = masker.mask_log_record(log_record)
```

## Performance

The secret masking functionality is designed to meet strict performance requirements:

- **Target**: <5ms processing time per log entry
- **Actual**: Typically ~1-2ms for complex records
- **Performance Monitoring**: Automatic warnings if processing exceeds 5ms

Example performance test:
```python
import time
from src.security.secret_masker import SecretMasker

masker = SecretMasker(enabled=True)
complex_record = {
    "msg": "password=secret and Bearer token123",
    "nested": {"credentials": {"api_key": "sk-123", "password": "secret"}},
    "large_list": [f"item_{i}" for i in range(1000)]
}

start_time = time.time()
masked = masker.mask_log_record(complex_record)
processing_time = (time.time() - start_time) * 1000

print(f"Processing time: {processing_time:.2f}ms")
# Typical result: ~1.3ms
```

## Security Considerations

### What is Masked
- Sensitive patterns in log messages
- Dictionary values for sensitive keys
- Nested data structures are recursively processed
- List items are individually processed

### What is NOT Masked
- Core log metadata (timestamp, level, component, run_id)
- Non-sensitive field names and values
- Data when masking is disabled via feature flag

### Performance vs Security
- Pre-compiled regex patterns for optimal performance
- Minimal memory allocation during processing
- Early exit when masking is disabled
- Copy-on-write approach preserves original data

## Testing

### Unit Tests
Run the comprehensive test suite:
```bash
python -m pytest tests/security/test_secret_masker.py -v
```

### Integration Tests
Test with real logging system:
```bash
python -m pytest tests/security/test_integration.py -v
```

### Demo Script
See the functionality in action:
```bash
python demo_secret_masking.py
```

## Implementation Details

### Architecture
- **SecretMasker**: Core masking logic with pattern detection
- **SecretPattern**: Individual pattern definitions with regex and replacement
- **create_masking_hook()**: Factory function for logging integration
- **Feature Flag Integration**: Automatic configuration from feature flags

### Hook Integration
The masking hook integrates with the JsonlLogger pipeline:

1. Log record created
2. Masking hook processes record (if enabled)
3. Other hooks process record
4. Record written to file

### Error Handling
- Hook exceptions are caught and logged as warnings
- Processing continues even if masking fails
- Performance warnings added for slow operations
- Feature flag failures default to enabled (secure by default)

## Examples

### Complete Example

```python
#!/usr/bin/env python3
import os
import tempfile
from pathlib import Path

from src.logging.jsonl_logger import JsonlLogger
from src.security.secret_masker import create_masking_hook
from src.runtime.run_context import RunContext

# Set up environment
with tempfile.TemporaryDirectory() as tmp_dir:
    os.chdir(tmp_dir)
    os.environ["BYKILT_RUN_ID"] = "example"
    
    # Clear singletons for clean start
    JsonlLogger._instances.clear()
    RunContext._instance = None
    
    # Create logger with masking
    logger = JsonlLogger.get(component="app")
    logger.register_hook(create_masking_hook())
    
    # Log sensitive information
    logger.info(
        "Authentication failed for password=wrongpass",
        request_headers={
            "Authorization": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9",
            "X-API-Key": "sk-1234567890abcdefghijklmnop"
        },
        user_context={
            "password": "attempted_password",
            "session_token": "secret_session_123"
        }
    )
    
    # Read log file to see masked output
    with open(logger.file_path) as f:
        import json
        log_entry = json.loads(f.read().strip())
        print(json.dumps(log_entry, indent=2))
```

This will output:
```json
{
  "ts": "2025-09-08T03:56:28.876567Z",
  "seq": 1,
  "level": "INFO",
  "msg": "Authentication failed for password=***MASKED_PASSWORD***",
  "component": "app",
  "run_id": "example",
  "request_headers": {
    "Authorization": "***MASKED***",
    "X-API-Key": "***MASKED***"
  },
  "user_context": {
    "password": "***MASKED***",
    "session_token": "***MASKED***"
  }
}
```

## Migration Guide

### For Existing Code
No changes required! The secret masking functionality:
- Does not break existing logging calls
- Can be enabled/disabled via feature flag
- Integrates transparently through hooks

### To Enable Masking
Simply register the masking hook:
```python
logger = JsonlLogger.get(component="my_component")
logger.register_hook(create_masking_hook())
```

### To Disable Masking
Set the feature flag to false:
```yaml
security.secret_masking_enabled:
  type: bool
  default: false
```

Or use environment variable:
```bash
export BYKILT_FLAG_SECURITY_SECRET_MASKING_ENABLED=false
```