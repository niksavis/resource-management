"""
Validation Module

This module contains validation functions for the resource management
application, including name validation and date range validation.
"""

import streamlit as st
from typing import Dict, Tuple, List


def validate_name_field(name, entity_type="resource"):
    """Validate that a name field is not empty."""
    if not name.strip():
        st.error(f"{entity_type} name cannot be empty.")
        return False
    return True


def validate_date_range(start_date, end_date):
    """Validate that end date is after start date."""
    if start_date > end_date:
        st.error("End date must be after start date.")
        return False
    return True


def validate_project_dates(start_date, end_date, project_name=None):
    """Validate project dates with detailed error messages."""
    if start_date > end_date:
        error_msg = "End date must be after start date"
        if project_name:
            error_msg += f" for project '{project_name}'"
        st.error(f"{error_msg}.")
        return False

    # Check if duration is realistic
    duration_days = (end_date - start_date).days
    if duration_days > 365 * 2:  # More than 2 years
        st.warning(
            f"Project duration is very long ({duration_days} days). Consider breaking into phases."
        )

    return True


def validate_project_input(project_data: Dict) -> Tuple[bool, List[str]]:
    """Validate project input data with detailed error messages."""
    errors = []

    if not project_data.get("name"):
        errors.append("Project name is required")

    if not project_data.get("start_date"):
        errors.append("Start date is required")

    if not project_data.get("end_date"):
        errors.append("End date is required")

    if errors:
        return False, errors

    return True, []
