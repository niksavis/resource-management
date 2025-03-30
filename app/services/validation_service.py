"""
Validation service for the resource management application.

This module provides validation functions for resource data.
"""

from typing import Dict, Any, List, Tuple
import re
import pandas as pd


def validate_person(person_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate person data.

    Args:
        person_data: Dictionary containing person data

    Returns:
        Tuple containing (is_valid, error_messages)
    """
    errors = []

    # Validate name
    if not person_data.get("name"):
        errors.append("Name is required.")
    elif not re.match(r"^[a-zA-Z\s]+$", person_data["name"]):
        errors.append("Name must contain only letters and spaces.")

    # Validate department
    if not person_data.get("department"):
        errors.append("Department is required.")

    # Validate work days
    if not person_data.get("work_days"):
        errors.append("At least one work day must be selected.")

    # Validate work hours
    if person_data.get("daily_work_hours", 0) <= 0:
        errors.append("Daily work hours must be greater than zero.")

    return (len(errors) == 0, errors)


def validate_team(team_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate team data.

    Args:
        team_data: Dictionary containing team data

    Returns:
        Tuple containing (is_valid, error_messages)
    """
    errors = []

    # Validate name
    if not team_data.get("name"):
        errors.append("Team name is required.")
    elif not re.match(r"^[a-zA-Z\s]+$", team_data["name"]):
        errors.append("Team name must contain only letters and spaces.")

    # Validate department
    if not team_data.get("department"):
        errors.append("Department is required.")

    # Validate members
    if not team_data.get("members"):
        errors.append("Team must have at least one member.")
    elif not isinstance(team_data["members"], list):
        errors.append("Members must be a list.")

    return (len(errors) == 0, errors)


def validate_project(project_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate project data.

    Args:
        project_data: Dictionary containing project data

    Returns:
        Tuple containing (is_valid, error_messages)
    """
    errors = []

    # Validate name
    if not project_data.get("name"):
        errors.append("Project name is required.")
    elif not re.match(r"^[a-zA-Z0-9\s]+$", project_data["name"]):
        errors.append("Project name must contain only letters, numbers, and spaces.")

    # Validate start and end dates
    if not project_data.get("start_date"):
        errors.append("Start date is required.")
    if not project_data.get("end_date"):
        errors.append("End date is required.")
    elif project_data.get("start_date") and project_data.get("end_date"):
        try:
            start_date = pd.to_datetime(project_data["start_date"])
            end_date = pd.to_datetime(project_data["end_date"])
            if start_date > end_date:
                errors.append("Start date must be before end date.")
        except ValueError:
            errors.append("Start and end dates must be valid dates.")

    # Validate priority
    if "priority" in project_data:
        try:
            priority = int(project_data["priority"])
            if priority < 1 or priority > 10:
                errors.append("Priority must be between 1 and 10.")
        except ValueError:
            errors.append("Priority must be a valid integer.")

    return (len(errors) == 0, errors)
