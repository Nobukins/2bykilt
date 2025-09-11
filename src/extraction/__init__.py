"""
Declarative extraction schema implementation.

This module provides functionality for defining and executing
field extraction from web pages using YAML-based schemas.
"""

from .schema import ExtractionSchema, FieldDefinition
from .extractor import FieldExtractor
from .models import ExtractionResult, ExtractionWarning

__all__ = [
    'ExtractionSchema',
    'FieldDefinition',
    'FieldExtractor',
    'ExtractionResult',
    'ExtractionWarning'
]