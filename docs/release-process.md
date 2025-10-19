# Release Process Guide

## Overview

This guide outlines the recommended release workflow for managing versions and creating releases using the version management system.

## Release Phases

### Phase 1: Development

**Duration**: Multiple days/weeks  
**Activities**:

- Develop features and fix bugs
- Create feature branches (`feat/issue-XXX`)
- Merge commits to main branch
- Version remains at current development version

**Example**:

```bash
# Work normally on main
git commit -m "feat: Add new feature"
git commit -m "fix: Resolve issue #123"

# Current version: 0.1.0
python bykilt.py version show
```

### Phase 2: Pre-release

**Duration**: 1-3 days  
**Activities**:

- Create prerelease version
- Run full test suite
- Deploy to staging environment
- Gather feedback

**Commands**:

```bash
# Set prerelease version
python bykilt.py version set 0.2.0-rc.1

# Create tag for prerelease
python bykilt.py version tag

# Deploy to staging
./scripts/deploy.sh staging
```

### Phase 3: Release

**Duration**: Final release day  
**Activities**:

- Approve prerelease in staging
- Bump to release version
- Create release tag
- Deploy to production

**Commands**:

```bash
# Remove prerelease suffix
python bykilt.py version set 0.2.0

# Create release tag
python bykilt.py version tag

# Deploy to production
./scripts/deploy.sh production
```

### Phase 4: Post-release

**Duration**: After release  
**Activities**:

- Verify production stability
- Respond to issues
- Plan next release
- Begin Phase 1 for next version

## Common Scenarios

### Scenario 1: Bug Fix Release

**Current Version**: `1.0.0`  
**Goal**: Release bug fix as `1.0.1`

**Steps**:

```bash
# 1. Make bug fix commits on main
git commit -m "fix: Resolve critical bug in core module"

# 2. Bump patch version
python bykilt.py version bump --type patch
# Now: 1.0.1

# 3. Create release tag
python bykilt.py version tag

# 4. Deploy
./scripts/deploy.sh production
```

### Scenario 2: Feature Release

**Current Version**: `1.0.0`  
**Goal**: Release new features as `1.1.0`

**Steps**:

```bash
# 1. Develop features on feature branches
git checkout -b feat/issue-200
git commit -m "feat: Add user authentication"
git commit -m "feat: Add session management"
git checkout main
git merge feat/issue-200

# 2. Bump minor version
python bykilt.py version bump --type minor
# Now: 1.1.0

# 3. Create staging prerelease
python bykilt.py version set 1.1.0-rc.1
python bykilt.py version tag
./scripts/deploy.sh staging

# 4. After staging validation, release
python bykilt.py version set 1.1.0
python bykilt.py version tag
./scripts/deploy.sh production
```

### Scenario 3: Major Release

**Current Version**: `1.5.3`  
**Goal**: Release breaking changes as `2.0.0`

**Steps**:

```bash
# 1. Develop breaking changes on feature branch
git checkout -b feat/v2-refactor
# ... make significant changes ...
git checkout main
git merge feat/v2-refactor

# 2. Create alpha/beta versions for extended testing
python bykilt.py version set 2.0.0-alpha.1
python bykilt.py version tag
./scripts/deploy.sh staging

# ... gather feedback, iterate ...

# 3. Create beta version
python bykilt.py version set 2.0.0-beta.1
python bykilt.py version tag
./scripts/deploy.sh staging

# 4. Create release candidate
python bykilt.py version set 2.0.0-rc.1
python bykilt.py version tag
./scripts/deploy.sh staging

# 5. Final release
python bykilt.py version set 2.0.0
python bykilt.py version tag
./scripts/deploy.sh production
```

### Scenario 4: Emergency Hotfix

**Current Version**: `1.2.3` (in production)  
**Current Development**: `1.3.0-beta` (in staging)  
**Goal**: Fix critical production issue with hotfix

**Steps**:

```bash
# 1. Create hotfix branch from release tag
git checkout v1.2.3
git checkout -b hotfix/security-patch

# 2. Fix the issue
git commit -m "fix: Security vulnerability in auth module"

# 3. Bump patch version
python bykilt.py version bump --type patch
# Now: 1.2.4

# 4. Create and tag release
python bykilt.py version tag
./scripts/deploy.sh production

# 5. Merge hotfix back to main
git checkout main
git merge hotfix/security-patch

# 6. Update main to correct version if needed
python bykilt.py version show  # Check current version
# If still 1.3.0-beta, that's correct
```

## Prerelease Versioning

### Prerelease Stages

Use standard prerelease suffixes:

```text
MAJOR.MINOR.PATCH-STAGE.NUMBER
```

**Recommended stages**:

- `alpha.N` - Early stage, features may change significantly
- `beta.N` - Feature complete, known issues being fixed
- `rc.N` (release candidate) - Stable, awaiting final approval
- `dev` - Development version (internal only)

### Progression Example

For release `2.0.0`:

```text
2.0.0-alpha.1  →  2.0.0-alpha.2  →  2.0.0-beta.1  →  2.0.0-rc.1  →  2.0.0
```

**Commands**:

```bash
# Alpha testing phase
python bykilt.py version set 2.0.0-alpha.1

# More alpha iterations
python bykilt.py version set 2.0.0-alpha.2

# Beta phase
python bykilt.py version set 2.0.0-beta.1

# Release candidate
python bykilt.py version set 2.0.0-rc.1

# Final release
python bykilt.py version set 2.0.0
```

## Git Tag Management

### Creating Tags

Tags are automatically created with proper format:

```bash
python bykilt.py version tag
# Creates: v1.2.3
```

### Tag Format

```text
v<MAJOR>.<MINOR>.<PATCH>[-PRERELEASE]
```

Examples:

```text
v0.0.1
v1.0.0
v1.2.3-rc.1
v2.0.0-beta.2
```

### Listing Tags

```bash
python bykilt.py version tags
```

Output:

```text
v0.0.1
v0.1.0
v0.2.0-alpha.1
v0.2.0-beta.1
v0.2.0
v1.0.0
```

### Reverting a Release

If an accidental release occurs:

```bash
# 1. Identify the last good version
python bykilt.py version tags

# 2. Revert to previous version
git checkout v1.0.0

# 3. Set previous version
python bykilt.py version set 1.0.0

# 4. OR, if on main branch, reset to previous release
git reset --hard v1.0.0
git push -f origin main  # Use with caution
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Release

on:
  push:
    branches: [main]
    paths:
      - 'VERSION'
      - '.github/workflows/release.yml'

jobs:
  release:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0
      
      - name: Read version
        id: version
        run: echo "version=$(cat VERSION)" >> $GITHUB_OUTPUT
      
      - name: Create GitHub Release
        uses: actions/create-release@v1
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          tag_name: v${{ steps.version.outputs.version }}
          release_name: Release ${{ steps.version.outputs.version }}
          draft: false
          prerelease: ${{ contains(steps.version.outputs.version, '-') }}
      
      - name: Build and Push Docker Image
        run: |
          docker build -t app:${{ steps.version.outputs.version }} .
          docker push app:${{ steps.version.outputs.version }}
```

## Release Checklist

Before releasing, verify:

### Code Quality

- [ ] All tests passing: `python -m pytest tests/`
- [ ] Coverage meets minimum: `--cov-report term`
- [ ] No linting errors: Code review completed
- [ ] Documentation updated: README, changelogs
- [ ] Dependencies reviewed: No security issues

### Version Management

- [ ] Correct version number set
- [ ] Version follows semantic versioning
- [ ] Prerelease stage appropriate (if prerelease)
- [ ] VERSION file updated
- [ ] Git tag created

### Testing

- [ ] Unit tests passing: `pytest`
- [ ] Integration tests passing
- [ ] Manual smoke tests in staging
- [ ] End-to-end tests passing
- [ ] Performance baseline met

### Communication

- [ ] Changelog prepared
- [ ] Release notes written
- [ ] Stakeholders notified
- [ ] Release schedule confirmed
- [ ] Rollback plan documented

### Deployment

- [ ] Deployment scripts tested
- [ ] Database migrations (if needed) tested
- [ ] Rollback procedure verified
- [ ] Monitoring configured
- [ ] On-call team notified

## Best Practices

### Version Numbering

1. **Use semantic versioning consistently**
   - Makes it easy for consumers to understand changes
   - Enables proper dependency management

2. **Avoid 0.x versions for long**
   - Indicates pre-release or unstable
   - Public APIs should use 1.0.0+

3. **Increment only one number**
   - `1.2.3` → `1.2.4` (patch fix)
   - `1.2.3` → `1.3.0` (new feature)
   - `1.2.3` → `2.0.0` (breaking change)

### Tagging Strategy

1. **Always tag releases**
   - Makes it easy to identify what was deployed
   - Enables easy rollback

2. **Tag consistently**
   - Use `v` prefix: `v1.0.0`
   - Match with code version

3. **Keep tags immutable**
   - Never move or delete release tags
   - If mistake, create new version and tag

### Timeline

1. **Development**: Variable duration
2. **Pre-release**: 1-3 days
3. **Release**: Same day
4. **Post-release**: 1-2 days stabilization

Typical cycle: 1-2 weeks per release

### Monitoring

After release, monitor:

- [ ] Application error rates
- [ ] Performance metrics
- [ ] User-reported issues
- [ ] System health checks
- [ ] Log files for warnings/errors

Set up alerts for:

- [ ] Increase in error rate
- [ ] Performance degradation
- [ ] Deployment failures
- [ ] Integration issues

## Troubleshooting

### Issue: Version already exists

**Problem**: Tag `v1.0.0` already exists

**Solution**:

```bash
# Option 1: Increment patch
python bykilt.py version set 1.0.1
python bykilt.py version tag

# Option 2: Delete accidental tag (use with caution)
git tag -d v1.0.0
git push origin --delete v1.0.0
# Then recreate with correct version
```

### Issue: Prerelease tag not created

**Problem**: `python bykilt.py version tag` doesn't work with prerelease

**Solution**:

- Prerelease tags are created, but check with: `python bykilt.py version tags`
- Verify Git is working: `git status`
- Check tag format: `v1.0.0-alpha.1` is correct

### Issue: Version doesn't match released code

**Problem**: VERSION file shows `1.0.0` but deployed code is different

**Solution**:

```bash
# 1. Check current version
python bykilt.py version show

# 2. Check deployed version
curl https://app.example.com/api/version

# 3. If mismatch, update VERSION
python bykilt.py version set 1.0.1

# 4. Create new release with correct version
python bykilt.py version tag
./scripts/deploy.sh production
```

### Issue: Can't create Git tag

**Problem**: Permission denied or Git error

**Solution**:

- Verify Git installed: `git --version`
- Check permissions: `git config --global user.name`
- Verify in Git repository: `git status`
- Try manual tag creation:

```bash
VERSION=$(cat VERSION)
git tag -a v$VERSION -m "Version $VERSION"
git push origin v$VERSION
```

## Summary

The release process follows a four-phase approach:

1. **Development**: Create features and fixes
2. **Pre-release**: Test with prerelease versions in staging
3. **Release**: Final version and production deployment
4. **Post-release**: Monitor and prepare for next cycle

Use `python bykilt.py version` commands to manage versions throughout this process.
