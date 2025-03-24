"""
Validation Module

This module contains functions for validating input data in the resource
management application.
"""

from datetime import date
from typing import Tuple, List
import regex
import streamlit as st
import pandas as pd


def validate_name_field(name: str, field_type: str) -> bool:
    """
    Validates a name field to ensure it meets naming requirements.
    """
    if not name.strip():
        st.error(f"The {field_type} name is required.")
        return False

    if len(name) > 100:
        st.error(
            f"Due to system limitations, {field_type} names cannot exceed 100 characters."
        )
        return False

    # Check if name starts or ends with whitespace
    if name[0].isspace() or name[-1].isspace():
        st.error(f"The {field_type} name must not start or end with spaces.")
        return False

    # Use Unicode properties which are supported in the regex module
    # This allows for international characters in names
    if not regex.match(r"^[\p{L}\p{N} \-\'\.\,_]*$", name):
        st.error(
            f"The {field_type} name contains invalid characters. Please use only letters, numbers, spaces, hyphens, apostrophes, periods, commas, and underscores."
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
        st.error("Budget must be a non-negative number.")
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


def validate_project_input(project_data: dict) -> bool:
    """
    Validates the input data for a project.
    Ensures that all required fields are present and valid.
    """
    required_fields = ["name", "start_date", "end_date", "budget"]

    for field in required_fields:
        if field not in project_data or not project_data[field]:
            return False

    if (
        not isinstance(project_data["name"], str)
        or len(project_data["name"].strip()) == 0
    ):
        return False

    if not isinstance(project_data["start_date"], (str, pd.Timestamp)):
        return False

    if not isinstance(project_data["end_date"], (str, pd.Timestamp)):
        return False

    if project_data["start_date"] > project_data["end_date"]:
        return False

    if (
        not isinstance(project_data["budget"], (int, float))
        or project_data["budget"] < 0
    ):
        return False

    return True


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
