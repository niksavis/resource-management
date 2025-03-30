"""
Department CRUD form components.

DEPRECATED: This module is maintained for backward compatibility.
Please use app.ui.forms.department_form instead.
"""

import warnings

warnings.warn(
    "The department_crud_form module is deprecated. Use app.ui.forms.department_form instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export the main function with the same name as the module
from app.ui.forms.department_form import display_department_form as department_crud_form

# Re-export everything else
from app.ui.forms.department_form import *
