"""
Validation utilities for resource management application.

This module provides validation functions used throughout the application.
"""

import streamlit as st
from datetime import datetime
from typing import Dict, Any, List, Union
import pandas as pd


def validate_name_field(name: str, resource_type: str) -> bool:
    """
    Validate a name field for a resource.

    Args:
        name: The name to validate
        resource_type: The type of resource (e.g., 'person', 'team', 'department', 'project')

    Returns:
        True if the name is valid, False otherwise
    """
    if not name or not name.strip():
        return False

    # Check minimum length (2 characters)
    if len(name.strip()) < 2:
        return False

    # Check for disallowed characters
    disallowed_chars = ["/", "\\", "*", "?", ":", '"', "<", ">", "|"]
    if any(char in name for char in disallowed_chars):
        return False

    # Check for duplicate names
    if resource_type == "person":
        if any(
            p["name"] == name
            for p in st.session_state.data["people"]
            if p.get("name") != name
        ):
            return False
    elif resource_type == "team":
        if any(
            t["name"] == name
            for t in st.session_state.data["teams"]
            if t.get("name") != name
        ):
            return False
    elif resource_type == "department":
        if any(
            d["name"] == name
            for d in st.session_state.data["departments"]
            if d.get("name") != name
        ):
            return False
    elif resource_type == "project":
        if any(
            p["name"] == name
            for p in st.session_state.data["projects"]
            if p.get("name") != name
        ):
            return False

    return True


def validate_date_range(
    start_date: Union[str, datetime, pd.Timestamp],
    end_date: Union[str, datetime, pd.Timestamp],
) -> bool:
    """
    Validate a date range.

    Args:
        start_date: The start date
        end_date: The end date

    Returns:
        True if the date range is valid, False otherwise
    """
    # Convert to pandas Timestamp for consistent comparison
    if isinstance(start_date, str):
        start_date = pd.to_datetime(start_date)
    if isinstance(end_date, str):
        end_date = pd.to_datetime(end_date)

    # Start date must be before or equal to end date
    return start_date <= end_date


def validate_project_input(project_data: Dict[str, Any]) -> bool:
    """
    Validate project data.

    Args:
        project_data: Dictionary containing project data

    Returns:
        True if the project data is valid, False otherwise
    """
    # Required fields
    if not all(field in project_data for field in ["name", "start_date", "end_date"]):
        return False

    # Name validation
    if not validate_name_field(project_data["name"], "project"):
        return False

    # Date range validation
    if not validate_date_range(project_data["start_date"], project_data["end_date"]):
        return False

    # Budget validation if present
    if "allocated_budget" in project_data and project_data["allocated_budget"] < 0:
        return False

    return True


def validate_daily_cost(cost: float) -> bool:
    """
    Validate daily cost for resources.

    Args:
        cost: The daily cost to validate

    Returns:
        True if the cost is valid, False otherwise
    """
    from app.services.config_service import load_daily_cost_settings

    max_cost = load_daily_cost_settings()
    return 0 <= cost <= max_cost


def validate_work_days(work_days: List[str]) -> bool:
    """
    Validate work days for resources.

    Args:
        work_days: List of work days

    Returns:
        True if the work days are valid, False otherwise
    """
    valid_days = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
        "MO",
        "TU",
        "WE",
        "TH",
        "FR",
        "SA",
        "SU",
    ]
    return len(work_days) > 0 and all(day in valid_days for day in work_days)


def validate_work_hours(hours: float) -> bool:
    """
    Validate daily work hours.

    Args:
        hours: The number of daily work hours

    Returns:
        True if the hours are valid, False otherwise
    """
    return 0 < hours <= 24


def validate_resource_allocation(
    allocation: Dict[str, Any],
    project_start: Union[str, datetime, pd.Timestamp],
    project_end: Union[str, datetime, pd.Timestamp],
) -> bool:
    """
    Validate resource allocation data.

    Args:
        allocation: Resource allocation data
        project_start: Project start date
        project_end: Project end date

    Returns:
        True if the allocation is valid, False otherwise
    """
    # Required fields
    required_fields = ["resource", "allocation_percentage", "start_date", "end_date"]
    if not all(field in allocation for field in required_fields):
        return False

    # Allocation percentage must be between 0 and 100
    if not 0 < allocation["allocation_percentage"] <= 100:
        return False

    # Valid date range
    if not validate_date_range(allocation["start_date"], allocation["end_date"]):
        return False

    # Allocation dates must be within project dates
    alloc_start = pd.to_datetime(allocation["start_date"])
    alloc_end = pd.to_datetime(allocation["end_date"])
    proj_start = pd.to_datetime(project_start)
    proj_end = pd.to_datetime(project_end)

    return proj_start <= alloc_start and alloc_end <= proj_end


def validate_team_integrity(team_name: str) -> bool:
    """
    Validate that a team has the minimum required number of members.

    Args:
        team_name: Name of the team to validate

    Returns:
        True if the team has at least 2 members, False otherwise
    """
    min_members = 2
    team = next(
        (t for t in st.session_state.data["teams"] if t["name"] == team_name), None
    )

    if not team or len(team.get("members", [])) < min_members:
        return False

    return True
