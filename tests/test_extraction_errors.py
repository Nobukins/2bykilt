"""
Enhanced error case tests for the extraction module.

This module tests edge cases, error handling, and failure scenarios
to improve coverage from 61% to 80%+.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from bs4 import BeautifulSoup

from src.extraction.models import ExtractionResult, ExtractionWarning
from src.extraction.schema import ExtractionSchema, FieldDefinition
from src.extraction.extractor import FieldExtractor


@pytest.mark.local_only
class TestFieldExtractorErrorCases:
    """Test FieldExtractor error handling."""

    @pytest.fixture
    def basic_schema(self):
        """Create a basic extraction schema for testing."""
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

        schema = ExtractionSchema(temp_path)
        Path(temp_path).unlink()
        return schema

    def test_extract_fields_no_content_or_browser(self, basic_schema):
        """Test extraction with neither page_content nor browser_context provided."""
        extractor = FieldExtractor(basic_schema)
        
        # Should handle gracefully and add warning instead of raising
        result = extractor.extract_fields("test_job", 0, page_content=None, browser_context=None)
        
        # Field extraction should fail and create warnings
        assert result.extracted_fields["field1"] is None
        assert result.failure_count == 1
        assert len(result.warnings) > 0

    def test_extract_fields_with_browser_context(self, basic_schema):
        """Test extraction with browser context (mock mode)."""
        extractor = FieldExtractor(basic_schema)
        mock_browser = Mock()
        
        result = extractor.extract_fields("test_job", 0, browser_context=mock_browser)
        
        assert result.job_id == "test_job"
        # Browser extraction returns mock data
        assert "mock_text_for_field1" in str(result.extracted_fields.get("field1", ""))

    @patch('src.extraction.extractor.BeautifulSoup')
    def test_extract_fields_malformed_html(self, mock_bs, basic_schema):
        """Test extraction with malformed HTML."""
        # Mock BeautifulSoup to raise exception
        mock_bs.side_effect = Exception("Invalid HTML")
        
        extractor = FieldExtractor(basic_schema)
        
        result = extractor.extract_fields("test_job", 0, "<html>malformed")
        
        # Should handle gracefully and return None for failed fields
        assert result.extracted_fields["field1"] is None
        assert result.failure_count > 0
        assert len(result.warnings) > 0

    @patch('src.extraction.extractor.BeautifulSoup')
    def test_extract_fields_selector_exception(self, mock_bs, basic_schema):
        """Test extraction when selector raises exception."""
        mock_soup = Mock()
        mock_soup.select_one.side_effect = Exception("Invalid selector")
        mock_bs.return_value = mock_soup
        
        extractor = FieldExtractor(basic_schema)
        
        result = extractor.extract_fields("test_job", 0, "<html></html>")
        
        assert result.extracted_fields["field1"] is None
        assert result.failure_count > 0

    def test_extract_from_html_attr_mode_no_attr_value(self):
        """Test attr mode extraction when attribute doesn't exist."""
        yaml_content = """
version: "1.0"
fields:
  - name: "field1"
    selector: ".field1"
    mode: "attr"
    attr_name: "data-missing"
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            schema = ExtractionSchema(temp_path)
            extractor = FieldExtractor(schema)
            
            # HTML with element but without the requested attribute
            html = '<div class="field1">text</div>'
            result = extractor.extract_fields("test_job", 0, html)
            
            # Should return None when attribute not found
            assert result.extracted_fields["field1"] is None

        finally:
            Path(temp_path).unlink()

    def test_extract_from_html_html_mode(self):
        """Test HTML mode extraction returns full element HTML."""
        yaml_content = """
version: "1.0"
fields:
  - name: "field1"
    selector: ".field1"
    mode: "html"
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            schema = ExtractionSchema(temp_path)
            extractor = FieldExtractor(schema)
            
            html = '<div class="field1"><span>nested</span></div>'
            result = extractor.extract_fields("test_job", 0, html)
            
            # Should return full HTML of element
            assert '<div class="field1">' in result.extracted_fields["field1"]
            assert '<span>nested</span>' in result.extracted_fields["field1"]

        finally:
            Path(temp_path).unlink()

    def test_normalize_unknown_type(self, basic_schema):
        """Test normalization with unknown type returns unchanged value."""
        extractor = FieldExtractor(basic_schema)
        
        # Unknown normalization type should return unchanged
        result = extractor._normalize_value("Test Value", "unknown_type")
        assert result == "Test Value"

    def test_multiple_fields_partial_failure(self):
        """Test extraction with multiple fields where some fail."""
        yaml_content = """
version: "1.0"
fields:
  - name: "existing"
    selector: ".exists"
    mode: "text"
    required: true
  - name: "missing"
    selector: ".missing"
    mode: "text"
    required: true
  - name: "optional"
    selector: ".optional"
    mode: "text"
    required: false
    default_value: "default"
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            schema = ExtractionSchema(temp_path)
            extractor = FieldExtractor(schema)
            
            html = '<div class="exists">found</div>'
            result = extractor.extract_fields("test_job", 0, html)
            
            # One success, one failure, one default
            assert result.extracted_fields["existing"] == "found"
            assert result.extracted_fields["missing"] is None
            assert result.extracted_fields["optional"] == "default"
            assert result.success_count == 2  # existing + optional default
            assert result.failure_count == 1  # missing

        finally:
            Path(temp_path).unlink()

    def test_extract_optional_field_no_default_not_found(self):
        """Test optional field without default when element not found."""
        yaml_content = """
version: "1.0"
fields:
  - name: "optional"
    selector: ".optional"
    mode: "text"
    required: false
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            schema = ExtractionSchema(temp_path)
            extractor = FieldExtractor(schema)
            
            html = '<div></div>'
            result = extractor.extract_fields("test_job", 0, html)
            
            # Optional field without default should be None, counted as neither success nor failure
            assert result.extracted_fields["optional"] is None
            assert result.total_fields == 1

        finally:
            Path(temp_path).unlink()

    def test_save_result_creates_directory(self, basic_schema):
        """Test that save_result creates output directory if it doesn't exist."""
        extractor = FieldExtractor(basic_schema)
        
        result = ExtractionResult(
            job_id="test_job",
            row_index=0,
            extracted_fields={"field1": "value1"},
            warnings=[],
            success_count=1,
            failure_count=0,
            total_fields=1,
            extracted_at="2024-01-01T00:00:00Z"
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "nested" / "output"
            output_file = extractor.save_result(result, output_dir)
            
            assert output_file.exists()
            assert output_file.parent == output_dir
            assert output_file.name == "extraction_result_test_job.json"


@pytest.mark.local_only
class TestExtractionSchemaErrorCases:
    """Test ExtractionSchema error handling."""

    def test_schema_load_nonexistent_file(self):
        """Test loading schema from non-existent file."""
        with pytest.raises(FileNotFoundError):
            ExtractionSchema("/nonexistent/path/schema.yml")

    def test_schema_invalid_yaml(self):
        """Test loading schema with invalid YAML syntax."""
        yaml_content = """
version: "1.0"
fields:
  - name: "field1"
    selector: [invalid yaml syntax
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            with pytest.raises(Exception):  # YAML parsing error
                ExtractionSchema(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_schema_missing_fields_key(self):
        """Test schema without fields key."""
        yaml_content = """
version: "1.0"
name: "test"
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="At least one field must be defined"):
                ExtractionSchema(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_schema_empty_fields(self):
        """Test schema with empty fields list."""
        yaml_content = """
version: "1.0"
fields: []
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="At least one field must be defined"):
                ExtractionSchema(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_schema_field_missing_name(self):
        """Test schema with field missing name."""
        yaml_content = """
version: "1.0"
fields:
  - selector: ".field1"
    mode: "text"
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="Field missing required keys"):
                ExtractionSchema(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_schema_field_missing_selector(self):
        """Test schema with field missing selector."""
        yaml_content = """
version: "1.0"
fields:
  - name: "field1"
    mode: "text"
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="Field missing required keys"):
                ExtractionSchema(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_schema_duplicate_field_names(self):
        """Test schema with duplicate field names."""
        yaml_content = """
version: "1.0"
fields:
  - name: "field1"
    selector: ".field1"
    mode: "text"
  - name: "field1"
    selector: ".field1-alt"
    mode: "text"
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            # Should still load, but might want to add validation
            schema = ExtractionSchema(temp_path)
            # Verify last one wins or both exist
            assert len(schema.fields) == 2
        finally:
            Path(temp_path).unlink()


@pytest.mark.local_only
class TestFieldDefinitionEdgeCases:
    """Test FieldDefinition edge cases."""

    def test_field_definition_with_all_parameters(self):
        """Test FieldDefinition with all parameters specified."""
        field = FieldDefinition(
            name="complete_field",
            selector=".complete",
            mode="attr",
            required=False,
            attr_name="data-value",
            normalize="trim",
            default_value="default"
        )
        
        assert field.name == "complete_field"
        assert field.selector == ".complete"
        assert field.mode == "attr"
        assert field.required is False
        assert field.attr_name == "data-value"
        assert field.normalize == "trim"
        assert field.default_value == "default"

    def test_field_definition_mode_case_sensitivity(self):
        """Test that mode validation is case-sensitive."""
        # Lowercase should work
        field = FieldDefinition(name="f1", selector=".f1", mode="text")
        assert field.mode == "text"
        
        # Uppercase should fail
        with pytest.raises(ValueError, match="Invalid mode"):
            FieldDefinition(name="f2", selector=".f2", mode="TEXT")

    def test_field_definition_normalize_case_sensitivity(self):
        """Test that normalize validation is case-sensitive."""
        # Lowercase should work
        field = FieldDefinition(name="f1", selector=".f1", mode="text", normalize="trim")
        assert field.normalize == "trim"
        
        # Uppercase should fail
        with pytest.raises(ValueError, match="Invalid normalize"):
            FieldDefinition(name="f2", selector=".f2", mode="text", normalize="TRIM")

    def test_field_definition_default_values(self):
        """Test FieldDefinition default values."""
        field = FieldDefinition(
            name="minimal",
            selector=".minimal",
            mode="text"
        )
        
        # Check defaults - required defaults to True in the schema loader
        assert field.required is True
        assert field.attr_name is None
        assert field.normalize is None
        assert field.default_value is None

    def test_field_definition_attr_mode_with_none_attr_name(self):
        """Test attr mode with explicitly None attr_name."""
        with pytest.raises(ValueError, match="attr_name is required"):
            FieldDefinition(
                name="field",
                selector=".field",
                mode="attr",
                attr_name=None
            )

    def test_field_definition_attr_mode_with_empty_attr_name(self):
        """Test attr mode with empty string attr_name."""
        with pytest.raises(ValueError, match="attr_name is required"):
            FieldDefinition(
                name="field",
                selector=".field",
                mode="attr",
                attr_name=""
            )


@pytest.mark.local_only
class TestExtractionResultEdgeCases:
    """Test ExtractionResult edge cases."""

    def test_extraction_result_auto_counts(self):
        """Test that ExtractionResult automatically calculates counts."""
        warnings = [
            ExtractionWarning("f2", ".f2", "Not found", "2024-01-01T00:00:00Z")
        ]
        
        result = ExtractionResult(
            job_id="test",
            row_index=0,
            extracted_fields={"f1": "v1", "f2": None, "f3": "v3"},
            warnings=warnings,
            extracted_at="2024-01-01T00:00:00Z"
        )
        
        # Counts should be auto-calculated in __post_init__
        assert result.total_fields == 3
        assert result.success_count == 2  # f1, f3
        assert result.failure_count == 1  # f2 (based on warnings)

    def test_extraction_result_empty_fields(self):
        """Test ExtractionResult with no fields."""
        result = ExtractionResult(
            job_id="test",
            row_index=0,
            extracted_fields={},
            warnings=[],
            extracted_at="2024-01-01T00:00:00Z"
        )
        
        assert result.total_fields == 0
        assert result.success_count == 0
        assert result.failure_count == 0

    def test_extraction_result_all_failures(self):
        """Test ExtractionResult with all fields failing."""
        warnings = [
            ExtractionWarning("f1", ".f1", "Not found", "2024-01-01T00:00:00Z"),
            ExtractionWarning("f2", ".f2", "Not found", "2024-01-01T00:00:00Z")
        ]
        
        result = ExtractionResult(
            job_id="test",
            row_index=0,
            extracted_fields={"f1": None, "f2": None},
            warnings=warnings,
            extracted_at="2024-01-01T00:00:00Z"
        )
        
        assert result.total_fields == 2
        assert result.success_count == 0
        assert result.failure_count == 2
        assert len(result.warnings) == 2


@pytest.mark.local_only
class TestBrowserExtractionModes:
    """Test browser extraction mock modes."""

    @pytest.fixture
    def multi_mode_schema(self):
        """Schema with different extraction modes."""
        yaml_content = """
version: "1.0"
fields:
  - name: "text_field"
    selector: ".text"
    mode: "text"
  - name: "attr_field"
    selector: ".attr"
    mode: "attr"
    attr_name: "data-value"
  - name: "html_field"
    selector: ".html"
    mode: "html"
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        schema = ExtractionSchema(temp_path)
        Path(temp_path).unlink()
        return schema

    def test_browser_extraction_all_modes(self, multi_mode_schema):
        """Test browser extraction returns appropriate mock data for each mode."""
        extractor = FieldExtractor(multi_mode_schema)
        mock_browser = Mock()
        
        result = extractor.extract_fields("test_job", 0, browser_context=mock_browser)
        
        # Check each mode returns appropriate mock
        assert "mock_text_for_text_field" in str(result.extracted_fields["text_field"])
        assert "mock_attr_for_attr_field" in str(result.extracted_fields["attr_field"])
        assert "mock_html_for_html_field" in str(result.extracted_fields["html_field"])


@pytest.mark.local_only
class TestNormalizationEdgeCases:
    """Test normalization edge cases."""

    @pytest.fixture
    def normalization_schema(self):
        """Schema with normalization."""
        yaml_content = """
version: "1.0"
fields:
  - name: "trim_field"
    selector: ".trim"
    mode: "text"
    normalize: "trim"
  - name: "upper_field"
    selector: ".upper"
    mode: "text"
    normalize: "upper"
  - name: "lower_field"
    selector: ".lower"
    mode: "text"
    normalize: "lower"
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        schema = ExtractionSchema(temp_path)
        Path(temp_path).unlink()
        return schema

    def test_normalization_with_real_html(self, normalization_schema):
        """Test normalization with actual HTML extraction."""
        extractor = FieldExtractor(normalization_schema)
        
        html = '''
        <div class="trim">  whitespace  </div>
        <div class="upper">lowercase</div>
        <div class="lower">UPPERCASE</div>
        '''
        
        result = extractor.extract_fields("test_job", 0, html)
        
        assert result.extracted_fields["trim_field"] == "whitespace"
        assert result.extracted_fields["upper_field"] == "LOWERCASE"
        assert result.extracted_fields["lower_field"] == "uppercase"

    def test_normalization_on_none_value(self, normalization_schema):
        """Test that normalization is skipped for None values."""
        extractor = FieldExtractor(normalization_schema)
        
        # HTML without the elements
        html = '<div></div>'
        
        result = extractor.extract_fields("test_job", 0, html)
        
        # All should be None or default values, not raise errors during normalization
        for field_name, value in result.extracted_fields.items():
            field = normalization_schema.get_field(field_name)
            assert value in [None, field.default_value if field else None]
