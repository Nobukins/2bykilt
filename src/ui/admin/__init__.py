"""Admin UI components for 2Bykilt application.

This package contains administrative UI panels and tools:
- feature_flag_panel: Feature Flag management and visualization (Issue #272)
"""

from .feature_flag_panel import create_feature_flag_admin_panel

__all__ = [
    "create_feature_flag_admin_panel",
]
