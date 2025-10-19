import sys
import os
import io

import pytest

# Ensure project root is importable
ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.batch.csv_utils import parse_csv_preview


@pytest.mark.ci_safe
def test_parse_csv_preview_basic():
    csv_bytes = b"id,name,email\n1,Alice,alice@example.com\n2,Bob,bob@example.com\n"
    headers, rows = parse_csv_preview(csv_bytes, max_rows=5)
    assert isinstance(headers, list)
    assert headers == ["id", "name", "email"]
    assert isinstance(rows, list)
    assert len(rows) == 2
    assert rows[0]["id"] == "1"
    assert rows[1]["name"] == "Bob"


@pytest.mark.ci_safe
def test_parse_csv_preview_unicode_and_empty_fields():
    csv_bytes = "id,name,notes\n1,太郎,ご挨拶\n2,花子,\n".encode("utf-8")
    headers, rows = parse_csv_preview(csv_bytes, max_rows=10)
    assert headers[0] == "id"
    assert rows[0]["name"] == "太郎"
    # parser may return None for empty fields depending on csv parsing behavior
    assert rows[1]["notes"] in (None, "")


@pytest.mark.ci_safe
def test_parse_csv_preview_shift_jis_encoding():
    # Test Shift_JIS encoding
    csv_text = "id,name\n1,テスト\n"
    csv_bytes = csv_text.encode("shift_jis")
    headers, rows = parse_csv_preview(csv_bytes, max_rows=5)
    assert headers == ["id", "name"]
    assert len(rows) == 1
    assert rows[0]["name"] == "テスト"


@pytest.mark.ci_safe
def test_parse_csv_preview_max_rows_limit():
    csv_bytes = b"id,value\n1,a\n2,b\n3,c\n4,d\n5,e\n6,f\n"
    headers, rows = parse_csv_preview(csv_bytes, max_rows=3)
    assert headers == ["id", "value"]
    assert len(rows) == 3
    assert rows[2]["id"] == "3"


@pytest.mark.ci_safe
def test_parse_csv_preview_empty_csv():
    csv_bytes = b""
    with pytest.raises(RuntimeError, match="Failed to parse CSV"):
        parse_csv_preview(csv_bytes)


@pytest.mark.ci_safe
def test_parse_csv_preview_header_only():
    csv_bytes = b"id,name,email\n"
    headers, rows = parse_csv_preview(csv_bytes, max_rows=5)
    assert headers == ["id", "name", "email"]
    assert len(rows) == 0


@pytest.mark.ci_safe
def test_parse_csv_preview_invalid_encoding():
    # Random bytes that won't decode with any of the supported encodings
    csv_bytes = b"\xff\xfe\xfd\xfc\xfb\xfa\xf9\xf8"
    with pytest.raises(RuntimeError, match="Failed to parse CSV"):
        parse_csv_preview(csv_bytes)


@pytest.mark.ci_safe
def test_parse_csv_preview_no_headers_no_rows():
    # Data that produces no headers and no rows - should fail
    csv_bytes = b"single line with no newline"
    with pytest.raises(RuntimeError, match="Failed to parse CSV"):
        parse_csv_preview(csv_bytes)


@pytest.mark.ci_safe
def test_parse_csv_preview_header_only_no_newline():
    # Header only with no newline - should be treated as invalid
    csv_bytes = b"id,name,email"
    with pytest.raises(RuntimeError, match="Failed to parse CSV"):
        parse_csv_preview(csv_bytes)
