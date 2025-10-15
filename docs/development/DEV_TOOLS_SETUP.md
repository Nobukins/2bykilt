# Development Tools Setup

This document describes the quality assurance tools available for 2Bykilt development.

## Installation

Install all development dependencies:

```bash
# Install linting and type checking tools
pip install pylint mypy flake8 black isort

# Or use requirements-dev.txt (recommended)
pip install -r requirements-dev.txt
```

## Tools Configuration

### 1. Pylint - Code Quality Checker

**Configuration:** `.pylintrc`

Run pylint on the main module:

```bash
# Check bykilt.py
python3 -m pylint bykilt.py

# Check specific module
python3 -m pylint src/cli/

# Check with custom configuration
python3 -m pylint --rcfile=.pylintrc bykilt.py
```

**Key settings:**
- Max line length: 120 characters
- Max module lines: 3000
- Allows common variable names (i, j, k, df, gr, etc.)
- Disabled overly strict rules for pragmatic development

### 2. Mypy - Static Type Checker

**Configuration:** `mypy.ini`

Run type checking:

```bash
# Check bykilt.py
python3 -m mypy bykilt.py

# Check entire src directory
python3 -m mypy src/

# Check with configuration
python3 -m mypy --config-file=mypy.ini bykilt.py
```

**Key settings:**
- Python version: 3.12
- Incremental checking enabled
- Third-party libraries ignored (gradio, playwright, etc.)
- Strict optional checking enabled

### 3. Flake8 - Style Guide Enforcement

**Configuration:** `.flake8` (if needed)

Run style checking:

```bash
# Check bykilt.py
python3 -m flake8 bykilt.py

# Check with custom config
python3 -m flake8 --max-line-length=120 bykilt.py
```

### 4. Black - Code Formatter (Optional)

Auto-format code to PEP 8:

```bash
# Format bykilt.py
python3 -m black bykilt.py

# Check without modifying
python3 -m black --check bykilt.py

# Format specific directory
python3 -m black src/cli/
```

### 5. isort - Import Sorter (Optional)

Sort imports automatically:

```bash
# Sort imports in bykilt.py
python3 -m isort bykilt.py

# Check without modifying
python3 -m isort --check-only bykilt.py
```

## Pre-commit Checks

Recommended pre-commit workflow:

```bash
# 1. Run tests
python3 -m pytest tests/ -k "cli or batch" -q

# 2. Check imports
python3 -c "import bykilt; print('✅ Import successful')"

# 3. Run type checker
python3 -m mypy bykilt.py src/cli/ src/ui/

# 4. Run linter (optional - can be noisy)
python3 -m pylint bykilt.py --rcfile=.pylintrc

# 5. Format code (if desired)
python3 -m black bykilt.py src/
python3 -m isort bykilt.py src/
```

## Continuous Integration

For CI/CD pipelines:

```bash
# Fast quality check
python3 -m pytest tests/ --tb=short -q
python3 -c "import bykilt"
python3 -m mypy bykilt.py --config-file=mypy.ini

# Full quality check
python3 -m pytest tests/
python3 -m pylint bykilt.py src/ --rcfile=.pylintrc
python3 -m mypy bykilt.py src/
python3 -m flake8 bykilt.py src/
```

## IDE Integration

### VS Code

Add to `.vscode/settings.json`:

```json
{
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.linting.pylintPath": "pylint",
  "python.linting.pylintArgs": ["--rcfile=.pylintrc"],
  "python.linting.mypyEnabled": true,
  "python.linting.mypyPath": "mypy",
  "python.linting.mypyArgs": ["--config-file=mypy.ini"],
  "python.formatting.provider": "black",
  "python.formatting.blackArgs": ["--line-length=120"],
  "editor.formatOnSave": true
}
```

### PyCharm

1. **Pylint:** File → Settings → Tools → External Tools → Add Pylint
2. **Mypy:** File → Settings → Tools → External Tools → Add Mypy
3. **Black:** File → Settings → Tools → Black → Enable on save

## Type Hints Best Practices

When adding type hints to existing code:

```python
# Good
def create_ui(config: Dict[str, Any], theme_name: str = "Ocean") -> gr.Blocks:
    """Create Gradio UI."""
    ...

# Better - with imports
from typing import Dict, Any, Optional
import gradio as gr

def create_ui(
    config: Dict[str, Any], 
    theme_name: str = "Ocean"
) -> gr.Blocks:
    """
    Create the Gradio UI.
    
    Args:
        config: Configuration dictionary
        theme_name: Gradio theme name
    
    Returns:
        Configured Gradio interface
    """
    ...
```

## Current Status

✅ **Configured:**
- `.pylintrc` - Pylint configuration
- `mypy.ini` - Mypy configuration
- Test infrastructure (pytest)

📋 **Next Steps:**
1. Install tools: `pip install pylint mypy flake8 black isort`
2. Create `requirements-dev.txt` with dev dependencies
3. Run initial quality checks
4. Add pre-commit hooks (optional)
5. Configure CI/CD pipeline

## Refactoring Progress

As of Phase 6 (2024-10-16):
- ✅ 31% size reduction (3888 → 2681 lines)
- ✅ 4 modules extracted
- ✅ 158/158 tests passing
- ✅ All imports verified
- ✅ CLI functionality confirmed
- ✅ Type hints infrastructure ready
- 📋 Full type annotation (gradual rollout)
- 📋 Linter integration (tooling ready)

## References

- [Pylint Documentation](https://pylint.pycqa.org/)
- [Mypy Documentation](https://mypy.readthedocs.io/)
- [Flake8 Documentation](https://flake8.pycqa.org/)
- [Black Documentation](https://black.readthedocs.io/)
- [PEP 8 Style Guide](https://pep8.org/)
- [PEP 484 Type Hints](https://www.python.org/dev/peps/pep-0484/)
