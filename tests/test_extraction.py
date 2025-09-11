"""
Tests for the extraction module.
"""

import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import Mock, patch

from src.extraction.models import ExtractionResult, ExtractionWarning
from src.extraction.schema import ExtractionSchema, FieldDefinition
from src.extraction.extractor import FieldExtractor


class TestExtractionModels:
    """Test extraction data models."""

    def test_extraction_warning_creation(self):
        """Test ExtractionWarning creation."""
        warning = ExtractionWarning(
            field_name="test_field",
            selector=".test",
            reason="Test reason",
            timestamp="2024-01-01T00:00:00Z"
        )

        assert warning.field_name == "test_field"
        assert warning.selector == ".test"
        assert warning.reason == "Test reason"
        assert warning.timestamp == "2024-01-01T00:00:00Z"

    def test_extraction_result_creation(self):
        """Test ExtractionResult creation."""
        extracted_fields = {"field1": "value1", "field2": None}
        warnings = [
            ExtractionWarning("field2", ".field2", "Not found", "2024-01-01T00:00:00Z")
        ]

        result = ExtractionResult(
            job_id="test_job_001",
            row_index=0,
            extracted_fields=extracted_fields,
            warnings=warnings,
            success_count=1,
            failure_count=1,
            total_fields=2,
            extracted_at="2024-01-01T00:00:00Z"
        )

        assert result.job_id == "test_job_001"
        assert result.row_index == 0
        assert result.extracted_fields == extracted_fields
        assert len(result.warnings) == 1
        assert result.success_count == 1
        assert result.failure_count == 1
        assert result.total_fields == 2

    def test_extraction_result_to_dict(self):
        """Test ExtractionResult to_dict conversion."""
        result = ExtractionResult(
            job_id="test_job_001",
            row_index=0,
            extracted_fields={"field1": "value1"},
            warnings=[],
            success_count=1,
            failure_count=0,
            total_fields=1,
            extracted_at="2024-01-01T00:00:00Z"
        )

        data = result.to_dict()
        assert data["job_id"] == "test_job_001"
        assert data["row_index"] == 0
        assert data["extracted_fields"] == {"field1": "value1"}
        assert data["success_count"] == 1
        assert data["failure_count"] == 0
        assert data["total_fields"] == 1


class TestFieldDefinition:
    """Test FieldDefinition class."""

    def test_field_definition_creation(self):
        """Test FieldDefinition creation."""
        field = FieldDefinition(
            name="test_field",
            selector=".test",
            mode="text",
            required=True,
            attr_name=None,
            normalize=None,
            default_value=None
        )

        assert field.name == "test_field"
        assert field.selector == ".test"
        assert field.mode == "text"
        assert field.required is True

    def test_field_definition_validation_valid_modes(self):
        """Test FieldDefinition with valid modes."""
        # Test text mode
        field_text = FieldDefinition(
            name="test_field_text",
            selector=".test",
            mode="text"
        )
        assert field_text.mode == "text"

        # Test attr mode with attr_name
        field_attr = FieldDefinition(
            name="test_field_attr",
            selector=".test",
            mode="attr",
            attr_name="data-value"
        )
        assert field_attr.mode == "attr"
        assert field_attr.attr_name == "data-value"

        # Test html mode
        field_html = FieldDefinition(
            name="test_field_html",
            selector=".test",
            mode="html"
        )
        assert field_html.mode == "html"

    def test_field_definition_validation_invalid_mode(self):
        """Test FieldDefinition with invalid mode."""
        with pytest.raises(ValueError, match="Invalid mode 'invalid'"):
            FieldDefinition(
                name="test_field",
                selector=".test",
                mode="invalid"
            )

    def test_field_definition_attr_mode_requires_attr_name(self):
        """Test that attr mode requires attr_name."""
        with pytest.raises(ValueError, match="attr_name is required when mode is 'attr'"):
            FieldDefinition(
                name="test_field",
                selector=".test",
                mode="attr"
            )

    def test_field_definition_valid_attr_mode(self):
        """Test valid attr mode with attr_name."""
        field = FieldDefinition(
            name="test_field",
            selector=".test",
            mode="attr",
            attr_name="data-value"
        )
        assert field.mode == "attr"
        assert field.attr_name == "data-value"

    def test_field_definition_normalize_validation(self):
        """Test normalize validation."""
        for normalize in ["trim", "lower", "upper"]:
            field = FieldDefinition(
                name="test_field",
                selector=".test",
                mode="text",
                normalize=normalize
            )
            assert field.normalize == normalize

    def test_field_definition_invalid_normalize(self):
        """Test invalid normalize value."""
        with pytest.raises(ValueError, match="Invalid normalize 'invalid'"):
            FieldDefinition(
                name="test_field",
                selector=".test",
                mode="text",
                normalize="invalid"
            )


class TestExtractionSchema:
    """Test ExtractionSchema class."""

    def test_schema_creation_from_yaml(self):
        """Test schema creation from YAML content."""
        yaml_content = """
version: "1.0"
name: "test_schema"
fields:
  - name: "field1"
    selector: ".field1"
    mode: "text"
    required: true
  - name: "field2"
    selector: ".field2"
    mode: "attr"
    attr_name: "data-value"
    required: false
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            schema = ExtractionSchema(temp_path)

            assert schema.version == "1.0"
            assert schema.name == "test_schema"
            assert len(schema.fields) == 2

            field1 = schema.fields[0]
            assert field1.name == "field1"
            assert field1.mode == "text"
            assert field1.required is True

            field2 = schema.fields[1]
            assert field2.name == "field2"
            assert field2.mode == "attr"
            assert field2.attr_name == "data-value"
            assert field2.required is False

        finally:
            Path(temp_path).unlink()

    def test_schema_validation_missing_required_fields(self):
        """Test schema validation with missing required fields."""
        yaml_content = """
version: "1.0"
fields:
  - name: "field1"
    selector: ".field1"
    # missing mode
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="Field missing required keys"):
                ExtractionSchema(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_schema_get_field(self):
        """Test getting field by name."""
        yaml_content = """
version: "1.0"
fields:
  - name: "field1"
    selector: ".field1"
    mode: "text"
  - name: "field2"
    selector: ".field2"
    mode: "text"
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            schema = ExtractionSchema(temp_path)

            field1 = schema.get_field("field1")
            assert field1 is not None
            assert field1.name == "field1"

            field3 = schema.get_field("field3")
            assert field3 is None

        finally:
            Path(temp_path).unlink()

    def test_schema_to_dict(self):
        """Test schema to_dict conversion."""
        yaml_content = """
version: "1.0"
name: "test_schema"
fields:
  - name: "field1"
    selector: ".field1"
    mode: "text"
    required: true
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            schema = ExtractionSchema(temp_path)
            data = schema.to_dict()

            assert data["version"] == "1.0"
            assert len(data["fields"]) == 1
            assert data["fields"][0]["name"] == "field1"

        finally:
            Path(temp_path).unlink()


class TestFieldExtractor:
    """Test FieldExtractor class."""

    def test_extractor_creation(self):
        """Test FieldExtractor creation."""
        yaml_content = """
version: "1.0"
fields:
  - name: "field1"
    selector: ".field1"
    mode: "text"
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            schema = ExtractionSchema(temp_path)
            extractor = FieldExtractor(schema)

            assert extractor.schema == schema

        finally:
            Path(temp_path).unlink()

    @patch('bs4.BeautifulSoup')
    def test_extract_fields_text_mode(self, mock_bs):
        """Test field extraction in text mode."""
        # Mock BeautifulSoup
        mock_soup = Mock()
        mock_element = Mock()
        mock_element.get_text.return_value = "extracted text"
        mock_soup.select_one.return_value = mock_element
        mock_bs.return_value = mock_soup

        yaml_content = """
version: "1.0"
fields:
  - name: "field1"
    selector: ".field1"
    mode: "text"
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            schema = ExtractionSchema(temp_path)
            extractor = FieldExtractor(schema)

            result = extractor.extract_fields("test_job", 0, "<html></html>")

            assert result.job_id == "test_job"
            assert result.row_index == 0
            assert result.extracted_fields["field1"] == "extracted text"
            assert result.success_count == 1
            assert result.failure_count == 0

        finally:
            Path(temp_path).unlink()

    @patch('bs4.BeautifulSoup')
    def test_extract_fields_attr_mode(self, mock_bs):
        """Test field extraction in attr mode."""
        # Mock BeautifulSoup
        mock_soup = Mock()
        mock_element = Mock()
        mock_element.get.return_value = "attr_value"
        mock_soup.select_one.return_value = mock_element
        mock_bs.return_value = mock_soup

        yaml_content = """
version: "1.0"
fields:
  - name: "field1"
    selector: ".field1"
    mode: "attr"
    attr_name: "data-value"
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            schema = ExtractionSchema(temp_path)
            extractor = FieldExtractor(schema)

            result = extractor.extract_fields("test_job", 0, "<html></html>")

            assert result.extracted_fields["field1"] == "attr_value"
            assert result.success_count == 1

        finally:
            Path(temp_path).unlink()

    @patch('bs4.BeautifulSoup')
    def test_extract_fields_element_not_found(self, mock_bs):
        """Test field extraction when element is not found."""
        # Mock BeautifulSoup
        mock_soup = Mock()
        mock_soup.select_one.return_value = None
        mock_bs.return_value = mock_soup

        yaml_content = """
version: "1.0"
fields:
  - name: "field1"
    selector: ".field1"
    mode: "text"
    required: true
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            schema = ExtractionSchema(temp_path)
            extractor = FieldExtractor(schema)

            result = extractor.extract_fields("test_job", 0, "<html></html>")

            assert result.extracted_fields["field1"] is None
            assert result.success_count == 0
            assert result.failure_count == 1
            assert len(result.warnings) == 1

        finally:
            Path(temp_path).unlink()

    def test_normalize_value(self):
        """Test value normalization."""
        yaml_content = """
version: "1.0"
fields:
  - name: "field1"
    selector: ".field1"
    mode: "text"
    normalize: "trim"
  - name: "field2"
    selector: ".field2"
    mode: "text"
    normalize: "upper"
  - name: "field3"
    selector: ".field3"
    mode: "text"
    normalize: "lower"
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            schema = ExtractionSchema(temp_path)
            extractor = FieldExtractor(schema)

            # Test normalization directly
            assert extractor._normalize_value("  test  ", "trim") == "test"
            assert extractor._normalize_value("test", "upper") == "TEST"
            assert extractor._normalize_value("TEST", "lower") == "test"

        finally:
            Path(temp_path).unlink()

    @patch('bs4.BeautifulSoup')
    def test_extract_fields_with_default_value(self, mock_bs):
        """Test field extraction with default values."""
        # Mock BeautifulSoup
        mock_soup = Mock()
        mock_soup.select_one.return_value = None  # Element not found
        mock_bs.return_value = mock_soup

        yaml_content = """
version: "1.0"
fields:
  - name: "field1"
    selector: ".field1"
    mode: "text"
    required: false
    default_value: "default_value"
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            schema = ExtractionSchema(temp_path)
            extractor = FieldExtractor(schema)

            result = extractor.extract_fields("test_job", 0, "<html></html>")

            assert result.extracted_fields["field1"] == "default_value"
            assert result.success_count == 1  # Default value counts as success
            assert result.failure_count == 0

        finally:
            Path(temp_path).unlink()