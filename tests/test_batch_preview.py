import sys
import os
import pytest

# Ensure project root is importable
ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.batch.preview import _detect_unique_candidate, build_preview_from_bytes


@pytest.mark.ci_safe
def test_detect_unique_candidate_no_headers():
    result = _detect_unique_candidate([], [])
    assert result is None


@pytest.mark.ci_safe
def test_detect_unique_candidate_no_rows():
    result = _detect_unique_candidate(["id", "name"], [])
    assert result is None


@pytest.mark.ci_safe
def test_detect_unique_candidate_common_candidates():
    headers = ["name", "id", "email"]
    rows = [{"name": "Alice", "id": "1", "email": "alice@test.com"}]
    result = _detect_unique_candidate(headers, rows)
    assert result == "id"  # Should pick first common candidate


@pytest.mark.ci_safe
def test_detect_unique_candidate_unique_column():
    headers = ["name", "value"]
    rows = [
        {"name": "Alice", "value": "A"},
        {"name": "Bob", "value": "B"},
        {"name": "Charlie", "value": "C"}
    ]
    result = _detect_unique_candidate(headers, rows)
    assert result == "name" or result == "value"  # Either could be detected as unique


@pytest.mark.ci_safe
def test_detect_unique_candidate_no_unique():
    headers = ["category", "count"]
    rows = [
        {"category": "A", "count": "1"},
        {"category": "A", "count": "2"},
        {"category": "B", "count": "1"}
    ]
    result = _detect_unique_candidate(headers, rows)
    assert result is None  # No unique columns


@pytest.mark.ci_safe
def test_detect_unique_candidate_empty_values():
    headers = ["id", "name", "empty_col"]
    rows = [
        {"id": "1", "name": "Alice", "empty_col": ""},
        {"id": "2", "name": "Bob", "empty_col": None},
        {"id": "3", "name": "Charlie", "empty_col": ""}
    ]
    result = _detect_unique_candidate(headers, rows)
    # Should detect id as unique since empty_col has only empty values
    assert result == "id"


@pytest.mark.ci_safe
def test_build_preview_from_bytes_none():
    result = build_preview_from_bytes(None, 5, "test_template")
    display_rows, display_headers, status_msg, header_choices, selected_value = result
    assert display_rows == []
    assert display_headers == []
    assert "No CSV file selected" in status_msg
    assert header_choices == []
    assert selected_value is None


@pytest.mark.ci_safe
def test_build_preview_from_bytes_valid_csv():
    csv_bytes = b"id,name,email\n1,Alice,alice@test.com\n2,Bob,bob@test.com"
    result = build_preview_from_bytes(csv_bytes, 5, "test_template")
    display_rows, display_headers, status_msg, header_choices, selected_value = result

    assert len(display_rows) == 2
    assert display_headers == ["id", "name", "email", "_job_template"]
    assert "Previewing top 2 rows" in status_msg
    assert "test_template" in status_msg
    assert header_choices == ["id", "name", "email"]
    assert selected_value == "id"  # Should detect id as unique


@pytest.mark.ci_safe
def test_build_preview_from_bytes_with_unique_override():
    csv_bytes = b"name,value\nAlice,100\nBob,200"
    result = build_preview_from_bytes(csv_bytes, 5, "test_template", unique_override="name")
    display_rows, display_headers, status_msg, header_choices, selected_value = result

    assert display_headers[0] == "name"  # name should be first
    assert selected_value == "name"
    assert len(display_rows) == 2
    assert display_rows[0][0] == "Alice"  # First column should be name


@pytest.mark.ci_safe
def test_build_preview_from_bytes_no_template():
    csv_bytes = b"id,value\n1,test"
    result = build_preview_from_bytes(csv_bytes, 5, None)
    display_rows, display_headers, status_msg, header_choices, selected_value = result

    assert display_rows[0][-1] == "<none>"  # Last column should be <none>
    assert "Template: <none>" in status_msg


@pytest.mark.ci_safe
def test_build_preview_from_bytes_row_count():
    csv_bytes = b"id,value\n1,a\n2,b\n3,c\n4,d\n5,e\n6,f\n"
    result = build_preview_from_bytes(csv_bytes, 3, "test_template")
    display_rows, display_headers, status_msg, header_choices, selected_value = result

    assert len(display_rows) == 3  # Limited by n_rows
    assert "approx total rows: 7" in status_msg  # Includes header + 6 data rows + empty line