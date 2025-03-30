"""
Person CRUD form components.

DEPRECATED: This module is maintained for backward compatibility.
Please use app.ui.forms.person_form instead.
"""

import warnings

warnings.warn(
    "The person_crud_form module is deprecated. Use app.ui.forms.person_form instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export the main function with the same name as the module
from app.ui.forms.person_form import display_person_form as person_crud_form

# Re-export everything else
from app.ui.forms.person_form import *
