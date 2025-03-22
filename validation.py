"""
Validation Module

This module contains functions for validating input data in the resource
management application.
"""

from datetime import date
from typing import Tuple, List
import streamlit as st


def validate_name_field(name: str, field_type: str) -> bool:
    """
    Validates a name field to ensure it is not empty and does not contain invalid characters.
    """
    if not name.strip():
        st.error(f"{field_type} name cannot be empty.")
        return False
    if len(name) > 50:
        st.error(f"{field_type} name cannot exceed 50 characters.")
        return False
    if not name.replace(" ", "").isalpha():
        st.error(
            f"{field_type} name can only contain alphabetic characters and spaces."
        )
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


def validate_project_dates(start_date: date, end_date: date, project_name: str) -> bool:
    """
    Validates project start and end dates to ensure the start date is before the end date.
    """
    if start_date > end_date:
        st.error(
            f"Start date must be before the end date for project '{project_name}'."
        )
        return False
    return True


def validate_daily_cost(daily_cost: float) -> bool:
    """
    Validates the daily cost to ensure it is a positive number.
    """
    if daily_cost <= 0:
        st.error("Daily cost must be greater than 0.")
        return False
    return True


def validate_budget(budget: float) -> bool:
    """
    Validates a budget to ensure it is a positive number.
    """
    if budget < 0:
        st.error("Budget must be a positive number.")
        return False
    return True


def validate_work_days(work_days: List[str]) -> bool:
    """
    Validates the selected work days to ensure at least one day is selected.
    """
    if not work_days:
        st.error("At least one work day must be selected.")
        return False
    return True


def validate_work_hours(work_hours: int) -> bool:
    """
    Validates the daily work hours to ensure they are within a reasonable range.
    """
    if work_hours < 1 or work_hours > 24:
        st.error("Daily work hours must be between 1 and 24.")
        return False
    return True


def validate_project_input(project_data: dict) -> Tuple[bool, List[str]]:
    """
    Validates the entire project input data.
    """
    errors = []
    if not project_data.get("name"):
        errors.append("Project name cannot be empty.")
    if project_data.get("priority") < 1:
        errors.append("Priority must be a positive integer.")
    if project_data.get("allocated_budget") < 0:
        errors.append("Allocated budget must be a positive number.")
    if project_data.get("start_date") > project_data.get("end_date"):
        errors.append("Start date must be before the end date.")
    return len(errors) == 0, errors


def detect_budget_overrun(
    project_cost: float, allocated_budget: float, threshold: float = 0.9
) -> Tuple[str, str]:
    """
    Detects if a project has a budget overrun or is approaching its limit.
    """
    if allocated_budget <= 0:
        return "error", "Budget must be greater than zero."

    if project_cost > allocated_budget:
        overrun_percent = ((project_cost - allocated_budget) / allocated_budget) * 100
        return "error", f"Budget overrun: Cost exceeds budget by {overrun_percent:.1f}%"

    if project_cost > allocated_budget * threshold:
        remaining = allocated_budget - project_cost
        remaining_percent = (remaining / allocated_budget) * 100
        return (
            "warning",
            f"Approaching budget limit: {remaining_percent:.1f}% of budget remaining",
        )

    return "success", "Project is within budget"
