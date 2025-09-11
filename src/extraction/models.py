"""
Data models for declarative extraction.
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from datetime import datetime


@dataclass
class ExtractionWarning:
    """Warning information for extraction failures."""
    field_name: str
    selector: str
    reason: str
    timestamp: str

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


@dataclass
class ExtractionResult:
    """Result of field extraction for a single row."""
    job_id: str
    row_index: int
    extracted_fields: Dict[str, Any]
    warnings: List[ExtractionWarning]
    success_count: int
    failure_count: int
    total_fields: int
    extracted_at: str

    def __post_init__(self):
        if not self.extracted_at:
            self.extracted_at = datetime.now().isoformat()
        # Calculate success/failure counts
        self.success_count = len([v for v in self.extracted_fields.values() if v is not None])
        self.failure_count = len(self.warnings)
        # Total fields attempted is the number of fields in extracted_fields
        self.total_fields = len(self.extracted_fields)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'job_id': self.job_id,
            'row_index': self.row_index,
            'extracted_fields': self.extracted_fields,
            'warnings': [vars(w) for w in self.warnings],
            'success_count': self.success_count,
            'failure_count': self.failure_count,
            'total_fields': self.total_fields,
            'extracted_at': self.extracted_at
        }