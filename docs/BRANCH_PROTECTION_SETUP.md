# Branch Protection Configuration Guide

## GitHub Settings for 2bykilt and main Branches

### Why Branch Protection?

Protect the main development branches (`2bykilt` and `main`) to:
- ✅ Prevent direct commits (require PR review)
- ✅ Enforce code quality standards
- ✅ Maintain linear history (easier debugging)
- ✅ Catch conflicts before merge

---

## Manual Configuration Steps

### 1. Access Branch Protection Settings

Navigate to: https://github.com/Nobukins/2bykilt/settings/branches

### 2. Add Protection Rule for `2bykilt` Branch

**Pattern to match**: `2bykilt`

#### Required Settings:

**Under "Protect this branch":**

- [x] **Require a pull request before merging**
  - Require approvals: ☐ (unchecked - not required for solo dev)
  - Dismiss stale pull request approvals when new commits are pushed: ☑️ (checked)
  - Require review from Code Owners: ☐ (unchecked)

- [x] **Require status checks to pass before merging**
  - Require branches to be up to date before merging: ☑️ (checked)
  - Status checks: (select any CI/CD workflows if configured)

- [x] **Require linear history**
  - This prevents merge commits and keeps history clean

- [x] **Require branches to be up to date before merging**

- [x] **Dismiss stale pull request approvals when new commits are pushed**

- [x] **Include administrators**
  - Even repo admins must follow the rules

- [ ] **Allow force pushes** (leave unchecked)

- [ ] **Allow deletions** (leave unchecked)

---

### 3. Repeat for `main` Branch

If a `main` branch exists, apply identical protection rules:

Navigate to same settings page, add another rule for `main`

---

## Why These Specific Settings?

| Setting | Reason |
|---------|--------|
| Require PR before merge | Enforces code review process |
| Require status checks | Ensures tests pass |
| Require linear history | Clean git history, easier bisect |
| Require branches up to date | Prevents stale PRs being merged |
| Dismiss stale approvals | Keeps security current |
| Include administrators | No one bypasses rules |
| Block force pushes | Prevents history rewriting |
| Block deletions | Protects branch from accidents |

---

## For Command-Line Users (After Web Setup)

If configured via web interface, you can view settings:

```bash
# View protection rules for 2bykilt
gh api repos/Nobukins/2bykilt/branches/2bykilt/protection --jq '.required_pull_request_reviews, .required_linear_history'

# View protection rules for main
gh api repos/Nobukins/2bykilt/branches/main/protection --jq '.required_pull_request_reviews, .required_linear_history'
```

---

## Workflow After Protection Enabled

### ✅ Allowed
```bash
# Create feature branch
git checkout -b feat/new-feature

# Make changes and commits
git add .
git commit -m "feat: add new feature"

# Push to remote
git push -u origin feat/new-feature

# Create PR on GitHub
gh pr create --base 2bykilt --title "New Feature"

# After approval, merge PR
gh pr merge 123 --rebase --delete-branch
```

### ❌ Blocked
```bash
# BLOCKED: Direct commit to 2bykilt
git checkout 2bykilt
git commit -m "Direct commit"  # ❌ Will fail on push

# BLOCKED: Force push to 2bykilt
git push --force origin 2bykilt  # ❌ Not allowed

# BLOCKED: Delete 2bykilt branch
git branch -D 2bykilt
git push origin --delete 2bykilt  # ❌ Not allowed
```

---

## Verification Checklist

After setting up branch protection:

- [ ] Navigate to https://github.com/Nobukins/2bykilt/settings/branches
- [ ] Verify `2bykilt` has protection rules enabled
- [ ] Verify `main` has protection rules enabled (if exists)
- [ ] Try to create a direct commit to 2bykilt (should fail on push)
- [ ] Try to create a PR - should succeed ✅

---

## Current PR Status

When protection is active:

| PR | Status | Next Step |
|----|--------|-----------|
| #356 | Awaiting merge | `gh pr merge 356 --rebase` |
| #357 | Awaiting merge | `gh pr merge 357 --rebase` |
| #358 | Awaiting merge | `gh pr merge 358 --rebase` |
| #359 | Awaiting merge | `gh pr merge 359 --rebase` |

---

**Note**: Branch protection rules are configured via GitHub Web UI and are not CLI-easily automatable due to API authentication scope limitations. These rules persist once set and apply to all users.
