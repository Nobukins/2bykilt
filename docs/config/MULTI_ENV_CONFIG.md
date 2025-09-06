# Multi-Environment Configuration Loader

This document describes the multi-environment configuration system implemented for Issue #65.

## Overview

The multi-environment configuration loader provides a flexible, hierarchical configuration management system that supports:

- **Environment-specific configurations** (dev/staging/prod) 
- **Base + environment hierarchical merging**
- **Environment variable overrides**
- **Configuration validation and schema support**
- **CLI tools for operations and debugging**
- **Effective configuration artifacts**
- **Backward compatibility** with existing pickle-based configurations

## Directory Structure

```
config/
├── schema/
│   └── v1.0.yml          # Configuration schema with validation rules
├── base.yml              # Base configuration (common settings)
├── development.yml       # Development environment overrides
├── staging.yml           # Staging environment overrides
└── production.yml        # Production environment overrides
```

## Environment Switching

The system uses the `BYKILT_ENV` environment variable to determine which configuration to load:

```bash
export BYKILT_ENV=dev       # Uses development.yml (default)
export BYKILT_ENV=staging   # Uses staging.yml
export BYKILT_ENV=prod      # Uses production.yml
```

## Configuration Merging

The system performs hierarchical merging:

1. **Base configuration** (`base.yml`) is loaded first
2. **Environment-specific configuration** is merged on top
3. **Environment variable overrides** are applied
4. **Validation** is performed against the schema

Example:
- `base.yml` defines `llm.temperature: 1.0`
- `development.yml` overrides to `llm.temperature: 1.2`
- `BYKILT_LLM_TEMPERATURE=1.8` further overrides to `1.8`

## CLI Tools

### List Available Environments
```bash
python scripts/config_cli.py list
```

### Validate Configuration
```bash
python scripts/config_cli.py validate development
python scripts/config_cli.py validate production
```

### Compare Configurations
```bash
python scripts/config_cli.py compare development production
python scripts/config_cli.py compare development staging --output comparison.json
```

### Generate Effective Configuration
```bash
python scripts/config_cli.py effective production
python scripts/config_cli.py effective development --output dev_effective.json
```

## Environment Variable Overrides

The schema defines which configuration values can be overridden via environment variables:

```yaml
# In config/schema/v1.0.yml
llm:
  properties:
    temperature:
      type: float
      environment_override: "BYKILT_LLM_TEMPERATURE"
    model_name:
      type: string  
      environment_override: "BYKILT_LLM_MODEL"
```

Usage:
```bash
export BYKILT_LLM_TEMPERATURE=1.5
export BYKILT_LLM_MODEL=gpt-4
export BYKILT_HEADLESS=true
export BYKILT_DEV_MODE=false
```

## Integration with Existing Code

The multi-environment configuration integrates seamlessly with existing code through the configuration adapter:

```python
from src.utils.default_config_settings import default_config

# This function now automatically uses multi-env config when available
config = default_config()

# Configuration values are in the same format as before
print(config['llm_temperature'])  # Gets env-specific value
print(config['headless'])         # Gets env-specific value
```

## Configuration Examples

### Base Configuration (base.yml)
```yaml
config_version: "1.0.0"
agent:
  type: "custom"
  max_steps: 100
llm:
  provider: "openai"
  model_name: "gpt-4o"
  temperature: 1.0
browser:
  headless: false
  enable_recording: true
```

### Development Environment (development.yml)
```yaml
# Development-specific overrides
browser:
  headless: false        # Show browser in dev
  enable_recording: true
llm:
  temperature: 1.2       # More creative in dev
development:
  dev_mode: true
  debug_logging: true
storage:
  save_recording_path: "./tmp/dev/record_videos"
```

### Production Environment (production.yml)
```yaml
# Production-specific overrides
browser:
  headless: true         # Always headless in prod
  enable_recording: false # Disable for performance
llm:
  temperature: 0.8       # More conservative
development:
  dev_mode: false
  debug_logging: false
storage:
  save_recording_path: "./tmp/prod/record_videos"
```

## Effective Configuration Artifacts

The system can generate effective configuration artifacts that show the final merged configuration:

```bash
python scripts/config_cli.py effective production -o effective_config_prod.json
```

This creates a JSON file containing the complete configuration after all merging and overrides are applied.

## Testing

Run the test suite:
```bash
python tests/test_multi_env_config.py
```

The test suite includes:
- Configuration loading for different environments
- Hierarchical merging validation
- Environment variable override testing
- CLI tool functionality
- Error handling and validation

## Backward Compatibility

The system maintains full backward compatibility:

- Existing `default_config()` calls work unchanged
- Legacy pickle-based configurations are still supported as fallback
- No changes required to existing UI or application code
- Graceful fallback if multi-env config is not available

## Setup

To set up the multi-environment configuration system:

```bash
python scripts/setup_config.py
```

This script will:
- Verify configuration files exist
- Test the configuration system
- Show usage examples
- Validate CLI tools are working

## Dependencies for Future Issues

This configuration foundation supports the following dependent issues:

- **#64 Feature Flags Framework**: Can use environment-specific feature flag configurations
- **#63 llms.txt Schema Validator**: Can validate against environment-specific schemas  
- **#48 Environment Variable Validation**: Uses the same schema-based validation system

## Benefits

1. **Environment Isolation**: Clear separation between dev/staging/prod configurations
2. **Hierarchical Management**: Base configuration with environment-specific overrides
3. **Operational Visibility**: CLI tools for debugging and comparison
4. **Deployment Artifacts**: Effective configuration generation for deployment verification
5. **Developer Experience**: Easy environment switching and validation
6. **Production Safety**: Schema validation and environment variable overrides
7. **Backward Compatibility**: Works with existing codebase without changes