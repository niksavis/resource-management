"""
Utility functions for the resource management application.

This module provides common utility functions used across the application.
This is a compatibility layer that re-exports functions from their new locations.
DEPRECATED: Please import directly from app.services.data_service, app.ui.components,
or app.utils.formatting instead.
"""

import warnings
import functools


def deprecated(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        warnings.warn(
            f"Function {func.__name__} imported from utils is deprecated. "
            f"Please import from {func.__module__} instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return func(*args, **kwargs)

    return wrapper


# Re-export UI components
from app.ui.components import (
    display_filtered_resource as _display_filtered_resource,
    filter_dataframe as _filter_dataframe,
    confirm_action as _confirm_action,
    _display_filters as __display_filters,
)

# Apply deprecation warnings
display_filtered_resource = deprecated(_display_filtered_resource)
filter_dataframe = deprecated(_filter_dataframe)
confirm_action = deprecated(_confirm_action)
_display_filters = deprecated(__display_filters)

# Re-export data services
from app.services.data_service import (
    paginate_dataframe as _paginate_dataframe,
    check_circular_dependencies as _check_circular_dependencies,
    get_resource_type as _get_resource_type,
    _apply_all_filters as __apply_all_filters,
)

# Apply deprecation warnings
paginate_dataframe = deprecated(_paginate_dataframe)
check_circular_dependencies = deprecated(_check_circular_dependencies)
get_resource_type = deprecated(_get_resource_type)
_apply_all_filters = deprecated(__apply_all_filters)

# Re-export formatting utilities
from app.utils.formatting import (
    format_circular_dependency_message as _format_circular_dependency_message,
    format_currency as _format_currency,
)

# Apply deprecation warnings
format_circular_dependency_message = deprecated(_format_circular_dependency_message)
format_currency = deprecated(_format_currency)

# For backwards compatibility, maintain all imports used in the original file
import uuid
import numpy as np
import pandas as pd
import streamlit as st
from typing import List, Dict, Any, Optional, Tuple, Union
from configuration import load_currency_settings, load_display_preferences
