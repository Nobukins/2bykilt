"""
Field extraction executor for declarative schemas.
"""

import logging
import json
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from datetime import datetime

from .models import ExtractionResult, ExtractionWarning
from .schema import ExtractionSchema, FieldDefinition

logger = logging.getLogger(__name__)


class FieldExtractor:
    """
    Executor for declarative field extraction.

    This class handles the actual extraction of fields from web pages
    based on the provided schema definitions.
    """

    def __init__(self, schema: ExtractionSchema):
        self.schema = schema
        self.logger = logging.getLogger(f"{__name__}.FieldExtractor")

    def extract_fields(self, job_id: str, row_index: int,
                      page_content: Optional[str] = None,
                      browser_context: Optional[Any] = None) -> ExtractionResult:
        """
        Extract fields from the current page or provided content.

        Args:
            job_id: Job identifier
            row_index: Row index in the batch
            page_content: Optional HTML content to extract from
            browser_context: Optional browser context for live extraction

        Returns:
            ExtractionResult with extracted data and warnings
        """
        extracted_fields = {}
        warnings = []

        for field in self.schema.fields:
            try:
                value = self._extract_single_field(field, page_content, browser_context)
                if value is not None:
                    extracted_fields[field.name] = value
                elif field.required:
                    # Required field not found - set to None and add warning
                    extracted_fields[field.name] = None
                    warnings.append(ExtractionWarning(
                        field_name=field.name,
                        selector=field.selector,
                        reason="Required field not found",
                        timestamp=datetime.now().isoformat()
                    ))
                else:
                    # Use default value for non-required fields
                    extracted_fields[field.name] = field.default_value

            except Exception as e:
                error_msg = f"Failed to extract field '{field.name}': {str(e)}"
                self.logger.warning(error_msg)

                if field.required:
                    warnings.append(ExtractionWarning(
                        field_name=field.name,
                        selector=field.selector,
                        reason=error_msg,
                        timestamp=datetime.now().isoformat()
                    ))
                else:
                    # For non-required fields, use default value if available
                    if field.default_value is not None:
                        extracted_fields[field.name] = field.default_value
                        # This counts as a success since we provided a default value
                    else:
                        extracted_fields[field.name] = None
                        # This counts as a failure for non-required fields without defaults
                        warnings.append(ExtractionWarning(
                            field_name=field.name,
                            selector=field.selector,
                            reason="Required field not found",
                            timestamp=datetime.now().isoformat()
                        ))

        result = ExtractionResult(
            job_id=job_id,
            row_index=row_index,
            extracted_fields=extracted_fields,
            warnings=warnings,
            success_count=0,  # Will be calculated in __post_init__
            failure_count=0,  # Will be calculated in __post_init__
            total_fields=0,   # Will be calculated in __post_init__
            extracted_at=datetime.now().isoformat()
        )

        self.logger.info(
            f"Extracted {result.success_count}/{result.total_fields} fields for job {job_id}",
            extra={
                "job_id": job_id,
                "row_index": row_index,
                "success_count": result.success_count,
                "warning_count": result.failure_count
            }
        )

        return result

    def _extract_single_field(self, field: FieldDefinition,
                            page_content: Optional[str],
                            browser_context: Optional[Any]) -> Optional[Any]:
        """
        Extract a single field based on its definition.

        Args:
            field: Field definition
            page_content: Optional HTML content
            browser_context: Optional browser context

        Returns:
            Extracted value or None if not found
        """
        if browser_context:
            # Live extraction from browser
            return self._extract_from_browser(field, browser_context)
        elif page_content:
            # Extraction from HTML content
            return self._extract_from_html(field, page_content)
        else:
            raise ValueError("Either page_content or browser_context must be provided")

    def _extract_from_browser(self, field: FieldDefinition, browser_context: Any) -> Optional[Any]:
        """
        Extract field from live browser context.

        This is a placeholder for actual browser integration.
        In production, this would use Playwright or Selenium.
        """
        # TODO: Implement actual browser extraction
        # For now, return mock data based on field type for testing
        self.logger.debug(f"Mock extraction for field '{field.name}' from browser")

        # Generic mock implementation based on field mode
        if field.mode == "text":
            return f"mock_text_for_{field.name}"
        elif field.mode == "attr":
            return f"mock_attr_for_{field.name}"
        elif field.mode == "html":
            return f"<div>mock_html_for_{field.name}</div>"
        else:
            return f"mock_value_for_{field.name}"

    def _extract_from_html(self, field: FieldDefinition, html_content: str) -> Optional[Any]:
        """
        Extract field from HTML content using BeautifulSoup.

        This provides proper CSS selector support and robust HTML parsing.
        """
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html_content, 'html.parser')

            # Find element using CSS selector
            element = soup.select_one(field.selector)
            if not element:
                return None

            # Extract based on mode
            if field.mode == 'text':
                value = element.get_text(strip=True)
            elif field.mode == 'attr':
                if field.attr_name:
                    value = element.get(field.attr_name)
                else:
                    value = None
            elif field.mode == 'html':
                value = str(element)
            else:
                value = None

            # Apply normalization if specified
            if value and field.normalize:
                value = self._normalize_value(value, field.normalize)

            return value

        except Exception as e:
            self.logger.debug(f"HTML extraction failed for field '{field.name}': {e}")
            return None

    def _normalize_value(self, value: str, normalize_type: str) -> str:
        """Normalize extracted value."""
        if normalize_type == 'trim':
            return value.strip()
        elif normalize_type == 'lower':
            return value.lower()
        elif normalize_type == 'upper':
            return value.upper()
        else:
            return value

    def save_result(self, result: ExtractionResult, output_dir: Path) -> Path:
        """
        Save extraction result to file.

        Args:
            result: Extraction result to save
            output_dir: Directory to save the result

        Returns:
            Path to the saved file
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"extraction_result_{result.job_id}.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)

        self.logger.info(f"Saved extraction result to {output_file}")
        return output_file