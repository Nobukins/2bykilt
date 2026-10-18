"""Tests for time-boxed vulnerability suppressions (2026-07 security modernization).

Covers tools/security/normalize_pip_audit.py:
- expires_at is enforced: expired suppressions no longer apply
- entries without expires_at never expire
- malformed dates fail safe (suppression stays active, warning emitted)
"""

import importlib.util
from datetime import date, timedelta
from pathlib import Path

import pytest

_MODULE_PATH = Path(__file__).resolve().parents[2] / "tools" / "security" / "normalize_pip_audit.py"
_spec = importlib.util.spec_from_file_location("normalize_pip_audit", _MODULE_PATH)
normalize_pip_audit = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(normalize_pip_audit)


def _make_project(tmp_path: Path, expires_at: str | None) -> Path:
    (tmp_path / "requirements.txt").write_text("")  # project-root marker
    security_dir = tmp_path / "security"
    security_dir.mkdir()
    expiry_line = f'    expires_at: "{expires_at}"\n' if expires_at is not None else ""
    (security_dir / "suppressions.yaml").write_text(
        "suppressions:\n"
        '  "GHSA-test-entry":\n'
        '    reason: "test suppression"\n'
        '    added_at: "2025-01-01"\n'
        + expiry_line
    )
    return tmp_path


_VULN = {"id": "GHSA-test-entry", "cve": "", "package": "pkg", "version": "1.0"}


@pytest.mark.ci_safe
@pytest.mark.unit
class TestSuppressionExpiry:
    def test_active_suppression_applies(self, tmp_path):
        future = (date.today() + timedelta(days=30)).isoformat()
        root = _make_project(tmp_path, future)
        assert normalize_pip_audit.is_suppressed(_VULN, project_root=root) is True

    def test_expired_suppression_is_ignored(self, tmp_path, capsys):
        past = (date.today() - timedelta(days=1)).isoformat()
        root = _make_project(tmp_path, past)
        assert normalize_pip_audit.is_suppressed(_VULN, project_root=root) is False
        assert "expired" in capsys.readouterr().err

    def test_missing_expiry_never_expires(self, tmp_path):
        root = _make_project(tmp_path, None)
        assert normalize_pip_audit.is_suppressed(_VULN, project_root=root) is True

    def test_invalid_expiry_fails_safe_as_active(self, tmp_path, capsys):
        root = _make_project(tmp_path, "not-a-date")
        assert normalize_pip_audit.is_suppressed(_VULN, project_root=root) is True
        assert "invalid" in capsys.readouterr().err

    def test_unlisted_vulnerability_not_suppressed(self, tmp_path):
        future = (date.today() + timedelta(days=30)).isoformat()
        root = _make_project(tmp_path, future)
        other = {"id": "GHSA-other", "cve": "", "package": "pkg", "version": "1.0"}
        assert normalize_pip_audit.is_suppressed(other, project_root=root) is False
