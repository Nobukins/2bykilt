# Dependency Constraints

This directory contains compiled, locked requirements generated from `requirements.in` using pip-tools (`pip-compile`).

## Process

1. Edit top-level deps in `requirements.in` only.
2. Run: `pip-compile --generate-hashes --output-file constraints/requirements.txt requirements.in`
3. Install: `pip install -r constraints/requirements.txt`
4. CI should use only the locked file for reproducibility.

## Rationale

Separating top-level intent (`requirements.in`) from fully resolved pins (`constraints/requirements.txt`) improves reproducibility and minimizes manual conflict resolution.
