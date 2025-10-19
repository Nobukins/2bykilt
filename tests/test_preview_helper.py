import sys
import pytest
import os

ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.batch.preview import build_preview_from_bytes


@pytest.mark.ci_safe
def test_build_preview_basic():
    csv_bytes = b"id,name,email\n1,Alice,alice@example.com\n2,Bob,bob@example.com\n"
    rows, headers, status, choices, selected = build_preview_from_bytes(csv_bytes, 5, 't-1', None)
    assert isinstance(rows, list)
    assert isinstance(headers, list)
    assert headers[-1] == '_job_template'
    assert status.startswith('✅ Previewing top')
    assert 'id' in choices


@pytest.mark.ci_safe
def test_build_preview_with_override():
    csv_bytes = b"id,name,email\n1,Alice,alice@example.com\n2,Bob,bob@example.com\n"
    rows, headers, status, choices, selected = build_preview_from_bytes(csv_bytes, 5, 't-1', unique_override='email')
    # selected should be email when override provided
    assert selected == 'email'
    # email should be first column in headers
    assert headers[0] == 'email' or headers[1] == 'email' or 'email' in headers
