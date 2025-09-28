## Summary
This PR addresses the security vulnerability in Issue #274 by disabling unsafe pickle-based config loading and implementing safe JSON-based import/export functionality.

## Changes
- **Security Fix**: Reject `.pkl` files in the Web UI upload handler to prevent deserialization of untrusted data
- **New Feature**: Add JSON Schema validation for configuration files
- **Implementation**:
  - `load_config_from_json()` function with schema validation
  - `save_config_to_json()` function for exporting configs
  - Updated `update_ui_from_config()` to support `.json` files
- **Migration Tool**: `scripts/migrate_pkl_to_json.py` for converting existing `.pkl` files to JSON
- **Feature Flag**: `ALLOW_PICKLE_CONFIG` environment variable controls `.pkl` access (default: disabled)

## Testing
- All existing tests pass (1 unrelated failure in browser profile test)
- JSON schema validation ensures config integrity
- Migration script includes safety checks

## Breaking Changes
- `.pkl` files are no longer accepted via Web UI by default
- Users must use JSON format for config import/export
- Existing `.pkl` files can be migrated using the provided script

## Related Issues
- Fixes #274
- Related: #64, #65, #102, #192, #228

## Acceptance Criteria
- ✅ Web UI rejects `.pkl` files with clear error message
- ✅ JSON import validates against schema
- ✅ Migration script safely converts existing `.pkl` files
- ✅ No degradation in existing functionality