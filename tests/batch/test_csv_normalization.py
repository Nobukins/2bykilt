"""Test CSV input normalization for batch processing."""
import io
import tempfile
import os
from pathlib import Path
import pytest

def normalize_csv_input(csv_input):
    """Normalize CSV input to bytes for file writing."""
    if hasattr(csv_input, 'read'):
        # File-like object
        return csv_input.read()
    elif isinstance(csv_input, str):
        # Path string
        with open(csv_input, 'rb') as f:
            return f.read()
    elif hasattr(csv_input, 'value'):
        # NamedString (Gradio file upload)
        return csv_input.value.encode('utf-8')
    else:
        raise ValueError(f"Unsupported CSV input type: {type(csv_input)}")


class TestCSVInputNormalization:
    """Test CSV input normalization function."""

    def test_file_like_object(self):
        """Test with file-like object."""
        csv_content = b"name,value\ntest,123"
        file_like = io.BytesIO(csv_content)
        result = normalize_csv_input(file_like)
        assert result == csv_content

    def test_path_string(self):
        """Test with path string."""
        csv_content = b"name,value\ntest,123"
        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f:
            f.write(csv_content)
            temp_path = f.name

        try:
            result = normalize_csv_input(temp_path)
            assert result == csv_content
        finally:
            os.remove(temp_path)

    def test_named_string(self):
        """Test with NamedString-like object."""
        csv_content = "name,value\ntest,123"

        class MockNamedString:
            def __init__(self, value):
                self.value = value

        named_string = MockNamedString(csv_content)
        result = normalize_csv_input(named_string)
        assert result == csv_content.encode('utf-8')

    def test_unsupported_type(self):
        """Test with unsupported type."""
        with pytest.raises(ValueError, match="Unsupported CSV input type"):
            normalize_csv_input(123)