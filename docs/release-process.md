# Release Process Guide (Issue #342)

This guide describes the recommended workflow for managing releases and versions in the 2bykilt project using the Version Management System.

## Overview

A typical release workflow includes:

1. **Development Phase**: Feature development and bugfixes
2. **Pre-release Phase**: Create prerelease versions for testing
3. **Release Phase**: Create release version and Git tag
4. **Post-release Phase**: Update documentation and plan next release

## Release Workflow

### Phase 1: Development Phase

During development, maintain version consistency:

```bash
# Check current version
python bykilt.py version show
# Output: 2bykilt version: 1.0.0

# Make your changes...
git add .
git commit -m "feat: Add new feature"
```

### Phase 2: Pre-release Phase

When preparing for release testing, create prerelease versions:

```bash
# Create an alpha prerelease
python bykilt.py version set 1.1.0-alpha.1

# Commit prerelease version
git add VERSION
git commit -m "chore: Bump to 1.1.0-alpha.1 for testing"

# Push to development branch
git push origin develop
```

### Phase 3: Release Phase

When ready for production release:

#### Step 1: Bump to Release Version

```bash
# Bump minor version (removes prerelease tag)
python bykilt.py version bump --type minor
# Result: 1.1.0-alpha.1 → 1.1.0

# Verify version change
python bykilt.py version show
```

#### Step 2: Create Release Commit

```bash
# Commit version bump
git add VERSION
git commit -m "chore(release): Bump version to 1.1.0"

# Create Git tag
python bykilt.py version tag
# Output: Created Git tag: v1.1.0
```

#### Step 3: Push to Main Branch

```bash
# Merge release to main
git checkout main
git merge develop --no-ff -m "merge(release): Release version 1.1.0"

# Push changes
git push origin main
git push origin --tags  # Push the version tag
```

#### Step 4: Verify Release

```bash
# List all version tags
python bykilt.py version tags
# Output:
# Version tags:
#   v1.1.0
#   v1.0.0
#   v0.9.0

# Verify tag exists in Git
git tag -l | grep v1.1.0
```

### Phase 4: Post-release Phase

After release:

```bash
# Bump to next development version
python bykilt.py version set 1.2.0-dev.0

# Commit development version
git add VERSION
git commit -m "chore: Bump to 1.2.0-dev.0 for next development cycle"

# Push to develop branch
git checkout develop
git push origin develop
```

## Common Release Scenarios

### Scenario 1: Bug Fix Release

Release format: `X.Y.Z` (patch bump)

```bash
# Current version: 1.0.0
python bykilt.py version bump --type patch
# Result: 1.0.1

git add VERSION
git commit -m "chore(release): Bump to 1.0.1"
python bykilt.py version tag
```

### Scenario 2: Feature Release

Release format: `X.Y.0` (minor bump)

```bash
# Current version: 1.0.2
python bykilt.py version bump --type minor
# Result: 1.1.0

git add VERSION
git commit -m "chore(release): Bump to 1.1.0"
python bykilt.py version tag
```

### Scenario 3: Major Release

Release format: `X.0.0` (major bump)

```bash
# Current version: 1.5.3
python bykilt.py version bump --type major
# Result: 2.0.0

git add VERSION
git commit -m "chore(release): Bump to 2.0.0"
python bykilt.py version tag
```

### Scenario 4: Hotfix Release

Quick fix released out of normal cycle:

```bash
# Current version: 1.0.0
# Create hotfix branch
git checkout -b hotfix/critical-bug main

# Fix the bug
git add .
git commit -m "fix(critical): Fix critical issue"

# Bump patch version
python bykilt.py version bump --type patch
# Result: 1.0.1

git add VERSION
git commit -m "chore(release): Bump to 1.0.1"
python bykilt.py version tag

# Merge back
git checkout main
git merge hotfix/critical-bug --no-ff
git push origin main --tags

# Also merge to develop
git checkout develop
git merge hotfix/critical-bug --no-ff
git push origin develop
```

## Prerelease Versions

### Naming Conventions

Use semantic prerelease identifiers:

- **Alpha**: `1.0.0-alpha`, `1.0.0-alpha.1` - Early development, experimental
- **Beta**: `1.0.0-beta`, `1.0.0-beta.1` - Feature complete, testing phase
- **RC**: `1.0.0-rc.1` - Release candidate, final testing
- **Dev**: `1.0.0-dev.0` - Development snapshot

### Version Progression Example

```text
1.0.0-alpha.1      # First alpha
1.0.0-alpha.2      # Second alpha
1.0.0-beta.1       # First beta
1.0.0-beta.2       # Second beta
1.0.0-rc.1         # Release candidate
1.0.0              # Release
1.1.0-dev.0        # Development for next version
```

### Creating Prerelease Versions

```bash
# Create prerelease manually
python bykilt.py version set 1.0.0-beta.1

# Or update prerelease identifier
python bykilt.py version set 1.0.0-beta.2
```

## Version Constraints

When integrating with other systems, use semantic version constraints:

```text
1.0.0       - Exact version
>=1.0.0     - Version 1.0.0 or later
<2.0.0      - Before version 2.0.0
>=1.0.0 <2.0.0  - Compatibility range (1.x.x)
~1.2.3      - Approximately 1.2.3 (compatible with 1.2.x)
^1.2.3      - Caret range (compatible with 1.x.x)
```

## Git Tag Management

### List All Version Tags

```bash
# List all version tags
python bykilt.py version tags

# Or using Git directly
git tag -l 'v*'
```

### Delete Accidental Tags

```bash
# Delete local tag
git tag -d v1.0.0-wrong

# Delete remote tag
git push origin --delete v1.0.0-wrong
```

### Create Tag with Custom Prefix

```bash
# Create tag with custom prefix
python bykilt.py version tag --prefix release-
# Result: release-1.0.0
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Release

on:
  workflow_dispatch:
    inputs:
      bump_type:
        description: 'Bump type (major, minor, patch)'
        required: true
        default: 'minor'

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.12'
      
      - name: Bump version
        run: |
          python bykilt.py version bump --type ${{ github.event.inputs.bump_type }}
      
      - name: Create tag
        run: |
          python bykilt.py version tag
      
      - name: Commit and push
        run: |
          git add VERSION
          git commit -m "chore(release): Bump version"
          git push origin main --tags
```

## Troubleshooting

### Version Mismatch

**Problem**: VERSION file doesn't match Git tags

**Solution**: Ensure consistency before release

```bash
# Check current version
python bykilt.py version show

# Verify Git tags
python bykilt.py version tags

# Update if needed
python bykilt.py version set <correct-version>
```

### Release Already Tagged

**Problem**: Cannot create tag because version is already tagged

**Solution**: Check existing tags and delete if necessary

```bash
# Check tags
python bykilt.py version tags

# Delete accidental tag
git tag -d v1.0.0
git push origin --delete v1.0.0

# Create correct tag
python bykilt.py version bump --type patch
python bykilt.py version tag
```

### Prerelease Won't Bump

**Problem**: Cannot bump prerelease version

**Solution**: Prerelease bump is not automatic. Set version explicitly:

```bash
# Set specific prerelease
python bykilt.py version set 1.0.0-beta.1

# Then bump for release
python bykilt.py version bump --type patch  # Removes prerelease
```

## Best Practices

1. **Semantic Versioning**: Always follow semantic versioning format
   - Major changes → Major version bump
   - Feature additions → Minor version bump
   - Bug fixes → Patch version bump

2. **Tag Every Release**: Create Git tags for every production release
   - Use consistent prefix: `v` for versions
   - Tag AFTER all tests pass

3. **Version in Code**: Keep VERSION file in sync with actual version
   - Check version before release
   - Commit version changes with release

4. **Prerelease Testing**: Use prerelease versions for testing
   - Alpha for internal testing
   - Beta for external testing
   - RC for final validation

5. **Documentation**: Update documentation for major/minor releases
   - Changelog
   - Migration guides
   - New features documentation

6. **Automation**: Automate where possible
   - Use CI/CD for version bumping
   - Automated changelog generation
   - Automated tagging

## Release Checklist

Before releasing:

- [ ] All tests passing
- [ ] Code review completed
- [ ] Changelog updated
- [ ] Documentation updated
- [ ] No breaking changes in patch release
- [ ] Version follows semantic versioning
- [ ] VERSION file updated
- [ ] Git tag created
- [ ] Tag pushed to repository
- [ ] Release notes prepared

## References

- [Semantic Versioning 2.0.0](https://semver.org/)
- [Git Tagging Guide](https://git-scm.com/book/en/v2/Git-Basics-Tagging)
- [Version Management Documentation](./version-management.md)
- [GitHub Flow](https://docs.github.com/en/get-started/quickstart/github-flow)
