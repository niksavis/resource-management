"""
Team CRUD form components.

DEPRECATED: This module is maintained for backward compatibility.
Please use app.ui.forms.team_form instead.
"""

import warnings

warnings.warn(
    "The team_crud_form module is deprecated. Use app.ui.forms.team_form instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export the main function with the same name as the module
from app.ui.forms.team_form import display_team_form as team_crud_form

# Re-export everything else
from app.ui.forms.team_form import *
