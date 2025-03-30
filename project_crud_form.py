"""
Project CRUD form components.

DEPRECATED: This module is maintained for backward compatibility.
Please use app.ui.forms.project_form instead.
"""

import warnings

warnings.warn(
    "The project_crud_form module is deprecated. Use app.ui.forms.project_form instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export the main function with a specific name for backward compatibility
from app.ui.forms.project_form import display_project_form as project_crud_form

# Create aliases for the specific functions being imported in project_management.py
from app.ui.forms.project_form import display_project_form as add_project_form
from app.ui.forms.project_form import display_project_form as edit_project_form
from app.ui.forms.project_form import display_project_form as delete_project_form

# Re-export everything else
from app.ui.forms.project_form import *
