"""
Validation module for the resource management application.

DEPRECATED: This module is maintained for backward compatibility.
Please use app.services.validation_service instead.
"""

import warnings

warnings.warn(
    "The validation module is deprecated. Use app.services.validation_service instead.",
    DeprecationWarning,
    stacklevel=2,
)

from app.services.validation_service import *
