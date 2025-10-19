# Changelog Management

## Format

Use Keep a Changelog format in CHANGELOG.md file:

- Added section for new features
- Changed section for modifications
- Deprecated section for soon-to-be removed
- Removed section for deleted features
- Fixed section for bug fixes
- Security section for security patches

## Commit Convention

Use Conventional Commits format:

```bash
git commit -m "feat(module): Add new feature"
git commit -m "fix(module): Fix bug"
git commit -m "docs: Update readme"
```

Types: feat, fix, docs, refactor, perf, test, chore, ci

## Release Process

1. Make commits with conventional format
2. Update CHANGELOG.md
3. Bump version using CLI
4. Push to main branch
5. GitHub Actions creates release

## CI/CD Integration

The release-management.yml workflow:

- Detects VERSION file changes
- Creates Git tag
- Generates GitHub Release
- Includes changelog in release notes
- Validates version format

## Best Practices

- Use conventional commits consistently
- Update changelog before each release
- Use version CLI commands exclusively
- Keep VERSION file in sync
- Never manually create tags
