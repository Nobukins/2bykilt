import pytest
from src.batch.csv_utils import parse_csv_preview


@pytest.mark.ci_safe
def test_parse_utf8_simple():
    csv_bytes = "a,b,c\n1,2,3\n4,5,6\n".encode("utf-8")
    headers, rows = parse_csv_preview(csv_bytes, max_rows=10)
    assert headers == ["a", "b", "c"]
    assert rows[0]["a"] == "1"
    assert rows[1]["c"] == "6"


@pytest.mark.ci_safe
def test_parse_shift_jis():
    # Japanese header and content encoded in cp932/shift_jis
    csv_text = "名前,値\nテスト,あいう\n"  # simple CSV
    csv_bytes = csv_text.encode("cp932")
    headers, rows = parse_csv_preview(csv_bytes, max_rows=5)
    assert "名前" in headers
    assert rows[0]["値"] == "あいう"


@pytest.mark.ci_safe
def test_parse_latin1():
    csv_text = "col1,col2\ncaf\xe9,100\n"  # café in latin1
    csv_bytes = csv_text.encode("latin1")
    headers, rows = parse_csv_preview(csv_bytes, max_rows=5)
    assert headers == ["col1", "col2"]
    assert "caf" in rows[0]["col1"]


@pytest.mark.ci_safe
def test_empty_or_invalid_raises():
    with pytest.raises(RuntimeError):
        parse_csv_preview(b"\xff\xff\xff")
