"""
Visualization module for the resource management application.

DEPRECATED: This module is maintained for backward compatibility.
Please use app.ui.visualizations and app.services.visualization_service instead.
"""

import warnings

warnings.warn(
    "The visualization module is deprecated. Use app.ui.visualizations and "
    "app.services.visualization_service instead.",
    DeprecationWarning,
    stacklevel=2,
)

from app.ui.visualizations import *
from app.services.visualization_service import *
