# CI/CD Integration Guide

## Overview

This guide explains the automated CI/CD workflows for version management, tagging, and release creation.

## Release Management Workflow

The `.github/workflows/release-management.yml` workflow automates:

- Automatic version tagging on VERSION file changes
- GitHub Release creation with auto-generated release notes
- Changelog generation from conventional commits (feat, fix, docs, refactor, etc.)
- Categorized release notes (Features, Bug Fixes, Documentation, etc.)
- Version format validation
- Prerelease detection

## How It Works

### Automatic Release Trigger

```bash
# 1. Change version using CLI
python bykilt.py version bump --type minor

# 2. Commit the change
git add VERSION
git commit -m "chore(release): Bump version to 1.1.0"

# 3. Push to main branch
git push origin main

# → GitHub Actions automatically:
#   - Detects VERSION file change
#   - Creates Git tag v1.1.0
#   - Creates GitHub Release
#   - Generates release notes from commits
```

### Manual Release Trigger

```text
GitHub → Actions → release-management → Run workflow
Select branch → Set create_release=true → Run
→ Creates release for current VERSION
```

## Workflow Components

### Version Check Job

Validates and processes version:

- Reads VERSION file
- Checks if prerelease (`1.0.0-rc.1` vs `1.0.0`)
- Generates changelog from commits
- Creates Git tag
- Creates GitHub Release

### Verify Version Format Job

Ensures version validity:

- Semantic versioning format check
- VERSION file structure validation
- Proper newline handling

### Changelog Validation Job

Reviews commit quality:

- Conventional commit format analysis
- Commit message best practices
- Guidance for developers

### Test Version Commands Job

Validates version system:

- Runs version management tests
- Tests CLI command availability
- Validates functionality

## Setting Up

### 1. GitHub Repository Permissions

Ensure GitHub Actions has write permissions:

1. Go to Settings
2. Actions → General
3. Under "Workflow permissions":
   - Select "Read and write permissions"
   - Check "Allow GitHub Actions to create and approve pull requests"

### 2. VERSION File

Create in project root:

```bash
echo "0.0.1" > VERSION
git add VERSION
git commit -m "chore: Initialize version"
```

### 3. Release Workflow File

The workflow is configured in:
`.github/workflows/release-management.yml`

## Integration Strategy

### Development Workflow

```text
Feature development (multiple commits)
  ↓
Conventional commit messages (feat, fix, etc.)
  ↓
VERSION file update (using version CLI)
  ↓
Push to main
  ↓
GitHub Actions triggers
  ↓
Automatic release created
```

### Commit Conventions

Use conventional commit format for meaningful changelogs:

```bash
git commit -m "feat(version): Add new feature"
git commit -m "fix(parser): Resolve issue"
git commit -m "docs(readme): Update documentation"
```

Types: `feat`, `fix`, `docs`, `refactor`, `perf`, `test`, `chore`, `ci`

## Changelog Generation

### Automatic Release Notes

The workflow generates categorized release notes from conventional commits:

```markdown
# Release Notes: v1.1.0

## Changes since v1.0.0

### ✨ Features
- abc1234 feat(version): Add prerelease support
- def5678 feat(cli): Add batch operations

### 🐛 Bug Fixes
- ghi9012 fix(parser): Resolve edge case
- jkl3456 fix(cli): Improve error messages

### 📚 Documentation
- mno7890 docs(readme): Update guide
- pqr1234 docs(guide): Add examples

### 🔧 Refactoring
- stu5678 refactor(parser): Simplify logic

### 📖 Documentation
- [Version Management Guide](...)
- [Release Process Guide](...)
- [CI/CD Integration Guide](...)
```

### Release Configuration

The `.github/release.yml` file configures automatic release notes:

```yaml
changelog:
  categories:
    - title: 🚀 Features
      labels: [feature, enhancement, feat]
    - title: 🐛 Bug Fixes
      labels: [bug, bugfix, fix]
    - title: 📚 Documentation
      labels: [documentation, docs]
    # ... more categories
```

### Best Practices

- Use conventional commit format consistently: `feat(scope): description`
- Write descriptive commit subjects
- Add PR labels to categorize changes
- Types: `feat`, `fix`, `docs`, `refactor`, `perf`, `test`, `chore`, `ci`

### Commit to Release Notes Mapping

| Commit Prefix | Release Category | Example |
|---|---|---|
| `feat` | ✨ Features | `feat(cli): Add new command` |
| `fix` | 🐛 Bug Fixes | `fix(parser): Handle edge case` |
| `docs` | 📚 Documentation | `docs(readme): Update guide` |
| `refactor` | 🔧 Refactoring | `refactor(core): Improve structure` |
| `perf` | ⚡ Performance | `perf(parser): Optimize speed` |
| `test` | ✅ Testing | `test(version): Add coverage` |
| `chore` | 📝 Other Changes | `chore(deps): Update packages` |
| `ci` | 🤖 CI/CD | `ci(actions): Improve workflow` |

## Release Process

### Step 1: Version Bump

```bash
# Determine bump type
python bykilt.py version show          # Current: 1.0.0

# Bump version
python bykilt.py version bump --type minor   # → 1.1.0
```

### Step 2: Commit

```bash
git add VERSION
git commit -m "chore(release): Bump to 1.1.0"
```

### Step 3: Push

```bash
git push origin main
```

### Step 4: Automated Release

GitHub Actions automatically:

- Creates tag: `v1.1.0`
- Creates GitHub Release
- Includes changelog

## Validation

### Before Push

Verify locally:

```bash
# Check VERSION format
cat VERSION

# Check recent commits
git log --oneline -10

# Verify conventional format
git log --format="%s" -5 | grep -E "^(feat|fix|docs):"
```

### After Push

Monitor GitHub Actions:

```text
GitHub → Actions → release-management
  → View workflow run
  → Check job status
  → Review release notes
```

Verify in repository:

```bash
# Check tag
git tag -l | grep v1.1.0

# Check GitHub Release
Go to Releases tab on GitHub
```

## Troubleshooting

### Workflow doesn't trigger

**Check**:

- VERSION file was actually changed
- Push is to correct branch (main or 2bykilt)

```bash
git diff HEAD~1 VERSION
```

### Tag not created

**Check**:

- GitHub Actions permissions are correct
- Tag doesn't already exist

```bash
git tag -l "v*"
```

### Release notes empty

**Check**:

- Commits have conventional format
- Recent commits exist

```bash
git log --oneline -20
git log --format="%s" | head -5
```

## Advanced Usage

### Custom Release Notes

Edit the workflow to customize release template in release creation step.

### Multi-Branch Releases

Support multiple branches:

```yaml
on:
  push:
    branches: [ main, develop, release/* ]
    paths:
      - 'VERSION'
```

### Conditional Releases

Only release non-prerelease versions:

```yaml
if: steps.check-prerelease.outputs.is_prerelease == 'false'
```

## Recommended Practices

**Do**:

- Use version CLI commands exclusively
- Follow conventional commit format
- Push VERSION changes to main
- Let GitHub Actions create releases

**Don't**:

- Manually create tags
- Edit VERSION file directly
- Create releases without versioning
- Push without conventional commits

## Related Documentation

- [Version Management Guide](./version-management.md)
- [Release Process Guide](./release-process.md)
- [Changelog Management Guide](./changelog-management.md)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)

## Summary

The automated CI/CD workflow:

✅ Automatically creates releases on VERSION changes
✅ Generates release notes from commits
✅ Validates version format
✅ Supports prerelease versions
✅ Integrates with deployment systems
✅ Requires minimal manual intervention

This enables a streamlined, reliable release process.
