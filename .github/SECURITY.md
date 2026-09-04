# Security Policy

## Reporting a Vulnerability

If you believe you have found a security vulnerability in 2bykilt, please report it through coordinated disclosure.

**Please do not report security vulnerabilities through public issues, discussions, or pull requests.**

Instead, open a private report via [GitHub Security Advisories for this repository](https://github.com/Nobukins/2bykilt/security/advisories/new).

Please include as much of the following as you can:

* The type of issue (e.g. command injection via `llms.txt` actions, path traversal in artifact handling, SSRF in llms.txt remote import)
* Affected source file paths and the tag/branch/commit
* Whether the issue affects the **minimal (LLM-free)** edition, the **full** edition, or both (`ENABLE_LLM` mode)
* Step-by-step reproduction instructions and any special configuration required
* Proof-of-concept code if available, and the impact you foresee

We aim to acknowledge reports within 5 business days.

## Supported Versions

Only the latest release and the default branch (`2bykilt`) receive security fixes.

## Automated Security Posture

This repository runs a layered, continuously-updated security pipeline (see `docs/security/continuous-security.md` for details):

| Layer | Tooling |
|-------|---------|
| SAST | SonarCloud + CodeQL (`python`, `actions`) |
| SCA / dependencies | pip-audit policy gate, Dependency Review on PRs, Dependabot (grouped weekly), Trivy deep scan |
| Secrets | gitleaks on every PR/push |
| Workflow security | zizmor lint of GitHub Actions workflows |
| Supply chain | SBOM (SPDX + CycloneDX) with GitHub dependency snapshot, OpenSSF Scorecard |

Time-boxed risk acceptances live in `security/suppressions.yaml`; expired suppressions are automatically un-suppressed.
