# Documentation Index

Find key guides, reports, and references after the docs/ consolidation.

## Quick start

- [README.md](../README.md) — Project overview and entry points
- [README-MINIMAL.md](../README-MINIMAL.md) — Minimal setup and usage
- [LOCAL_TESTING.md](./LOCAL_TESTING.md) — How to run tests locally with markers and coverage

## Security and DevSecOps

- [SECURITY.md](./SECURITY.md) — Security policies and practices
- [continuous-security.md](./continuous-security.md) — Continuous security notes
- [PROJECT_REORGANIZATION_REPORT.md](./PROJECT_REORGANIZATION_REPORT.md) — Repo structure changes and rationale

## Browser and profiles

- [BROWSER_PROFILE_NEW_METHOD.md](./BROWSER_PROFILE_NEW_METHOD.md) — Profile handling for new method

## Platform and compatibility

- [MAC_COMPATIBILITY_REPORT.md](./MAC_COMPATIBILITY_REPORT.md) — macOS results
- [WINDOWS_SETUP_GUIDE.md](./WINDOWS_SETUP_GUIDE.md) — Windows setup
- [WINDOWS_COMPATIBILITY_REPORT.md](./WINDOWS_COMPATIBILITY_REPORT.md) — Windows results
- [VENV312_MINIMAL_VERIFICATION_REPORT.md](./VENV312_MINIMAL_VERIFICATION_REPORT.md) — Python 3.12 minimal verification

## Implementation and change logs

- [CHANGELOG.md](./CHANGELOG.md) — Canonical changelog
- [root-CHANGELOG.md](./root-CHANGELOG.md) — Migrated root copy for traceability
- [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md) / [FIX_SUMMARY.md](./FIX_SUMMARY.md) — Work summaries
- [PR_MESSAGE.md](./PR_MESSAGE.md) / [COMMIT_MESSAGE.md](./COMMIT_MESSAGE.md) — Templates

## Recording and prompts

- [RECORDING_PATH_FIX_REPORT.md](./RECORDING_PATH_FIX_REPORT.md) — Recording path notes
- [LLM_AS_OPTION.prompt.md](./LLM_AS_OPTION.prompt.md) / [LLM_OPTIONAL.md](./LLM_OPTIONAL.md) — Prompting options

## Requirements

- [requirements-minimal-working.txt](./requirements-minimal-working.txt) — Minimal deps that pass locally
- [requirements-full.txt](./requirements-full.txt) — Full environment

## Archive and moved files

- Root-level documents migrated are prefixed with `root-*.md` to preserve originals when duplicates existed.
- Root-level scripts and tests were moved to `.archive/` to keep `tests/` authoritative for pytest discovery.

See also: [ARCHIVE_POLICY.md](./ARCHIVE_POLICY.md) for details.