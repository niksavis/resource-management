"""
Validation Module

This module contains validation functions for the resource management
application, including name validation and date range validation.
"""

from typing import Tuple, Dict, List
import streamlit as st


def validate_name_field(name: str, entity_type: str = "resource") -> bool:
    """Validate the name field for a given entity type."""
    if not name.strip():
        st.error(f"{entity_type} name cannot be empty.")
        return False
    if len(name) < 3:
        st.error(f"{entity_type} name must be at least 3 characters long.")
        return False
    if not name.replace(" ", "").isalpha():
        st.error(f"{entity_type} name must contain only alphabetic characters.")
        return False
    return True


def validate_date_range(start_date, end_date) -> bool:
    """
    Validates that the start date is before or equal to the end date.

    Args:
        start_date (datetime.date): The start date.
        end_date (datetime.date): The end date.

    Returns:
        bool: True if the date range is valid, False otherwise.
    """
    if start_date > end_date:
        st.error("Start date must be before or equal to the end date.")
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


def validate_daily_cost(daily_cost: float) -> bool:
    """
    Validates the daily cost field.

    Args:
        daily_cost (float): The daily cost to validate.

    Returns:
        bool: True if the daily cost is valid, False otherwise.
    """
    if daily_cost <= 0:
        st.error("Daily cost must be greater than 0.")
        return False
    if daily_cost > 5000:  # Arbitrary upper limit for validation
        st.warning("Daily cost is unusually high. Please verify the value.")
    return True


def validate_budget(budget: float) -> bool:
    """
    Validates the budget field.

    Args:
        budget (float): The budget to validate.

    Returns:
        bool: True if the budget is valid, False otherwise.
    """
    if budget < 0:
        st.error("Budget cannot be negative.")
        return False
    if budget > 1_000_000:  # Arbitrary upper limit for validation
        st.warning("Budget is unusually high. Please verify the value.")
    return True


def validate_work_days(work_days: List[str]) -> bool:
    """
    Validates the work days field.

    Args:
        work_days (List[str]): The list of selected work days.

    Returns:
        bool: True if the work days are valid, False otherwise.
    """
    if not work_days:
        st.error("At least one work day must be selected.")
        return False
    if len(work_days) > 7:
        st.error("Work days cannot exceed 7 days per week.")
        return False
    return True


def validate_work_hours(work_hours: int) -> bool:
    """
    Validates the daily work hours field.

    Args:
        work_hours (int): The number of daily work hours.

    Returns:
        bool: True if the work hours are valid, False otherwise.
    """
    if work_hours < 1 or work_hours > 24:
        st.error("Daily work hours must be between 1 and 24.")
        return False
    if work_hours > 12:
        st.warning("Daily work hours are unusually high. Please verify the value.")
    return True


def detect_budget_overrun(project_cost: float, allocated_budget: float) -> bool:
    """
    Detects if a project has a budget overrun.

    Args:
        project_cost (float): The calculated project cost.
        allocated_budget (float): The allocated budget for the project.

    Returns:
        bool: True if there is a budget overrun, False otherwise.
    """
    if project_cost > allocated_budget:
        st.warning("Warning: Project cost exceeds the allocated budget!")
        return True
    return False
