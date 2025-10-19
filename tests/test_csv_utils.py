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
