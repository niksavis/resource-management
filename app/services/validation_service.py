"""
Validation service for the resource management application.

This module provides validation functions for resource data.
"""

from typing import Dict, Any, List, Tuple
import re
import pandas as pd
import streamlit as st  # Add this import for session state access


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

    # Validate team - if team is specified, ensure it belongs to the selected department
    if person_data.get("team"):
        teams = [
            t
            for t in st.session_state.data["teams"]
            if t["name"] == person_data["team"]
        ]
        if teams and teams[0]["department"] != person_data["department"]:
            errors.append(
                f"Team '{person_data['team']}' does not belong to department '{person_data['department']}'."
            )

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
    elif len(team_data.get("members", [])) < 2:
        errors.append("Team must have at least two members.")

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


def validate_project_resources(
    resources: List[str], allocations: List[Dict[str, Any]]
) -> Tuple[bool, List[str]]:
    """
    Validate project resource allocations.

    Args:
        resources: List of resource names
        allocations: List of resource allocation dictionaries

    Returns:
        Tuple containing (is_valid, error_messages)
    """
    errors = []

    # Check that all resources have allocations
    allocation_resources = [a["resource"] for a in allocations]
    missing_allocations = [r for r in resources if r not in allocation_resources]
    if missing_allocations:
        errors.append(f"Missing allocations for: {', '.join(missing_allocations)}")

    # Check for allocations with invalid dates
    for allocation in allocations:
        try:
            start_date = pd.to_datetime(allocation["start_date"])
            end_date = pd.to_datetime(allocation["end_date"])

            if start_date > end_date:
                errors.append(
                    f"Start date must be before end date for {allocation['resource']}"
                )
        except (ValueError, KeyError):
            errors.append(f"Invalid dates for {allocation.get('resource', 'unknown')}")

    # Check allocation percentages
    for allocation in allocations:
        try:
            percentage = allocation["allocation_percentage"]
            if not (10 <= percentage <= 100):
                errors.append(
                    f"Allocation percentage must be between 10% and 100% for {allocation['resource']}"
                )
        except (KeyError, ValueError):
            errors.append(
                f"Invalid allocation percentage for {allocation.get('resource', 'unknown')}"
            )

    return (len(errors) == 0, errors)


def validate_department(
    department_data: Dict[str, Any],
) -> Tuple[bool, List[str], List[Dict[str, Any]]]:
    """
    Validate department data.

    Args:
        department_data: Dictionary containing department data

    Returns:
        Tuple containing (is_valid, error_messages, conflict_data)
    """
    errors = []
    conflicts = []

    # Validate name
    if not department_data.get("name"):
        errors.append("Department name is required")

    # Check for member-team conflicts
    members = department_data.get("members", [])
    teams = department_data.get("teams", [])

    if members and teams:
        # Check if any direct member is also part of a team in this department
        team_members = []
        for team_name in teams:
            team = next(
                (t for t in st.session_state.data["teams"] if t["name"] == team_name),
                None,
            )
            if team:
                team_members.extend(team.get("members", []))

        for member in members:
            if member in team_members:
                # Find which teams this member belongs to
                member_teams = []
                for team_name in teams:
                    team = next(
                        (
                            t
                            for t in st.session_state.data["teams"]
                            if t["name"] == team_name
                        ),
                        None,
                    )
                    if team and member in team.get("members", []):
                        member_teams.append(team_name)

                if member_teams:
                    conflicts.append({"member": member, "teams": member_teams})

    return (len(errors) == 0, errors, conflicts)
