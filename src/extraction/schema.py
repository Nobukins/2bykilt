"""
Schema definition and validation for declarative extraction.
"""

import yaml
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class FieldDefinition:
    """Definition of a single field to extract."""
    name: str
    selector: str
    mode: str  # 'text', 'attr', 'html'
    required: bool = True
    attr_name: Optional[str] = None
    normalize: Optional[str] = None  # 'trim', 'lower', 'upper'
    default_value: Optional[Any] = None

    def __post_init__(self):
        # Validate mode
        valid_modes = ['text', 'attr', 'html']
        if self.mode not in valid_modes:
            raise ValueError(f"Invalid mode '{self.mode}'. Must be one of: {valid_modes}")

        # Validate attr_name when mode is 'attr'
        if self.mode == 'attr' and not self.attr_name:
            raise ValueError(f"attr_name is required when mode is 'attr' for field '{self.name}'")

        # Validate normalize
        if self.normalize and self.normalize not in ['trim', 'lower', 'upper']:
            raise ValueError(f"Invalid normalize '{self.normalize}'. Must be one of: trim, lower, upper")


class ExtractionSchema:
    """Schema for declarative field extraction."""

    def __init__(self, schema_path: Union[str, Path]):
        self.schema_path = Path(schema_path)
        self.fields: List[FieldDefinition] = []
        self.version: str = "1.0"
        self.name: str = "unnamed_schema"
        self._load_schema()

    def _load_schema(self):
        """Load and validate schema from YAML file."""
        if not self.schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {self.schema_path}")

        try:
            with open(self.schema_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            if not isinstance(data, dict):
                raise ValueError("Schema must be a dictionary")

            # Extract version and name if present
            self.version = data.get('version', '1.0')
            self.name = data.get('name', self.schema_path.stem)

            # Validate and load fields
            fields_data = data.get('fields', [])
            if not isinstance(fields_data, list):
                raise ValueError("fields must be a list")

            if not fields_data:
                raise ValueError("At least one field must be defined")

            self.fields = []
            for field_data in fields_data:
                if not isinstance(field_data, dict):
                    raise ValueError("Each field must be a dictionary")

                # Validate required fields
                required_keys = ['name', 'selector', 'mode']
                missing_keys = [key for key in required_keys if key not in field_data]
                if missing_keys:
                    raise ValueError(f"Field missing required keys: {missing_keys}")

                # Create field definition
                field = FieldDefinition(
                    name=field_data['name'],
                    selector=field_data['selector'],
                    mode=field_data['mode'],
                    required=field_data.get('required', True),
                    attr_name=field_data.get('attr_name'),
                    normalize=field_data.get('normalize'),
                    default_value=field_data.get('default_value')
                )
                self.fields.append(field)

            logger.info(f"Loaded extraction schema with {len(self.fields)} fields from {self.schema_path}")

        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in schema file: {e}")
        except Exception as e:
            raise ValueError(f"Failed to load schema: {e}")

    def get_field(self, name: str) -> Optional[FieldDefinition]:
        """Get field definition by name."""
        for field in self.fields:
            if field.name == name:
                return field
        return None

    def validate_selectors(self) -> List[str]:
        """Validate all selectors in the schema (basic validation)."""
        warnings = []
        for field in self.fields:
            # Basic selector validation
            if not field.selector or not field.selector.strip():
                warnings.append(f"Empty selector for field '{field.name}'")

            # Check for common issues
            if field.mode == 'attr' and not field.attr_name:
                warnings.append(f"Field '{field.name}' uses 'attr' mode but no attr_name specified")

        return warnings

    def to_dict(self) -> Dict[str, Any]:
        """Convert schema to dictionary."""
        return {
            'version': self.version,
            'fields': [
                {
                    'name': field.name,
                    'selector': field.selector,
                    'mode': field.mode,
                    'required': field.required,
                    'attr_name': field.attr_name,
                    'normalize': field.normalize,
                    'default_value': field.default_value
                }
                for field in self.fields
            ]
        }