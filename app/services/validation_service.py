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


def validate_person_associations(person, existing_data):
    """
    Validate person relationships with teams and departments.

    Args:
        person: Person data to validate
        existing_data: Current application data

    Returns:
        (bool, str): Tuple of (is_valid, error_message)
    """
    team_name = person.get("team")
    department_name = person.get("department")

    # Case 1: No associations - always valid
    if not team_name and not department_name:
        return True, ""

    # Case 2: Person belongs to a team
    if team_name:
        team = next((t for t in existing_data["teams"] if t["name"] == team_name), None)
        if not team:
            return False, f"Team '{team_name}' not found"

        team_department = team.get("department")

        # If person has direct department that doesn't match team's department
        if department_name and team_department and department_name != team_department:
            return (
                False,
                f"Person's department '{department_name}' must match team's department '{team_department}'",
            )

        # If person has no department but team has one, they'll inherit it
        if not department_name and team_department:
            # This is valid - person will inherit team's department
            return True, ""

    # Case 3: Person belongs directly to department (Individual Contributor)
    if department_name and not team_name:
        department = next(
            (d for d in existing_data["departments"] if d["name"] == department_name),
            None,
        )
        if not department:
            return False, f"Department '{department_name}' not found"

    return True, ""


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


def validate_team_associations(team, existing_data):
    """
    Validate team relationships with departments and people.

    Args:
        team: Team data to validate
        existing_data: Current application data

    Returns:
        (bool, str): Tuple of (is_valid, error_message)
    """
    department_name = team.get("department")
    members = team.get("members", [])

    # Check department exists if specified
    if department_name:
        department = next(
            (d for d in existing_data["departments"] if d["name"] == department_name),
            None,
        )
        if not department:
            return False, f"Department '{department_name}' not found"

    # Check each member exists
    for member in members:
        person = next((p for p in existing_data["people"] if p["name"] == member), None)
        if not person:
            return False, f"Person '{member}' not found"

    return True, ""


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
            # Handle both string dates and datetime objects
            if isinstance(project_data["start_date"], str):
                start_date = pd.to_datetime(project_data["start_date"])
            else:
                start_date = pd.to_datetime(project_data["start_date"])

            if isinstance(project_data["end_date"], str):
                end_date = pd.to_datetime(project_data["end_date"])
            else:
                end_date = pd.to_datetime(project_data["end_date"])

            if start_date > end_date:
                errors.append("Start date must be before end date.")
        except ValueError:
            errors.append("Start and end dates must be valid dates.")

    # Validate priority
    if "priority" in project_data:
        try:
            priority = int(project_data["priority"])
            if priority < 1:
                errors.append(
                    "Priority must be a positive integer (1 is highest priority)."
                )

            # Uniqueness of priority is validated at form submission time,
            # as we need to know if we're creating a new project or editing an existing one
        except ValueError:
            errors.append("Priority must be a valid integer.")

    # Validate assigned resources
    if not project_data.get("assigned_resources"):
        errors.append("At least one resource must be assigned to the project.")

    # Validate budget
    if "allocated_budget" in project_data:
        if project_data["allocated_budget"] < 0:
            errors.append("Allocated budget cannot be negative.")

    return (len(errors) == 0, errors)


def validate_project_resource_assignments(project, existing_data):
    """
    Validate project resource assignments to prevent duplications.

    Args:
        project: Project data to validate
        existing_data: Current application data

    Returns:
        (bool, list): Tuple of (is_valid, conflicts)
    """
    resources = project.get("assigned_resources", [])
    conflicts = []

    # Track all people already assigned either directly or via team/department
    assigned_people = set()

    # Check for resource assignment conflicts
    for resource in resources:
        # Check if resource is a person
        person = next(
            (p for p in existing_data["people"] if p["name"] == resource), None
        )
        if person:
            # Direct person assignment
            assigned_people.add(resource)
            continue

        # Check if resource is a team
        team = next((t for t in existing_data["teams"] if t["name"] == resource), None)
        if team:
            # Check team members against already assigned people
            team_members = team.get("members", [])
            for member in team_members:
                if member in assigned_people:
                    conflicts.append(
                        f"Person '{member}' is already assigned directly but also belongs to team '{resource}'"
                    )
                assigned_people.add(member)
            continue

        # Check if resource is a department
        department = next(
            (d for d in existing_data["departments"] if d["name"] == resource), None
        )
        if department:
            # Check for teams in this department that are already assigned
            dept_teams = [
                t["name"]
                for t in existing_data["teams"]
                if t.get("department") == resource
            ]
            dept_team_conflicts = [t for t in dept_teams if t in resources]
            if dept_team_conflicts:
                conflicts.append(
                    f"Department '{resource}' is assigned but its teams {dept_team_conflicts} are also assigned"
                )

            # Check for individual people in this department that are already assigned
            for person in existing_data["people"]:
                person_dept = person.get("department")
                if person_dept == resource and person["name"] in assigned_people:
                    conflicts.append(
                        f"Department '{resource}' is assigned but person '{person['name']}' is already assigned directly"
                    )
                elif person_dept == resource:
                    assigned_people.add(person["name"])

            # Check for people who are in teams belonging to this department
            for team_name in dept_teams:
                team = next(
                    (t for t in existing_data["teams"] if t["name"] == team_name), None
                )
                if team and team_name in resources:
                    for member in team.get("members", []):
                        if member in assigned_people and member not in [
                            p["name"]
                            for p in existing_data["people"]
                            if p.get("team") == team_name
                        ]:
                            conflicts.append(
                                f"Person '{member}' is already assigned but also belongs to team '{team_name}' in department '{resource}'"
                            )

    return len(conflicts) == 0, conflicts


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


def validate_team_department_change(
    team_name: str, new_department: str
) -> Tuple[bool, List[str]]:
    """
    Validate the impact of changing a team's department on team members.

    Args:
        team_name: Name of the team
        new_department: New department name

    Returns:
        Tuple containing (is_valid, affected_members)
    """
    team = next(
        (t for t in st.session_state.data["teams"] if t["name"] == team_name), None
    )
    if not team:
        return True, []

    affected_members = []

    # Find team members who have a direct department assignment different from the new department
    for person in st.session_state.data["people"]:
        if (
            team_name == person.get("team")
            and person.get("department")
            and person["department"] != new_department
        ):
            affected_members.append(person["name"])

    return True, affected_members


def handle_person_team_assignment(person_name: str, team_name: str) -> Tuple[bool, str]:
    """
    Handle assignment of a person to a team, updating department associations as needed.

    Args:
        person_name: Name of the person
        team_name: Name of the team (or None to remove team assignment)

    Returns:
        Tuple of (success, message)
    """
    person = next(
        (p for p in st.session_state.data["people"] if p["name"] == person_name), None
    )
    if not person:
        return False, f"Person '{person_name}' not found"

    if team_name:
        team = next(
            (t for t in st.session_state.data["teams"] if t["name"] == team_name), None
        )
        if not team:
            return False, f"Team '{team_name}' not found"

        # If team has a department, person's department must match or be updated
        if team.get("department"):
            if person.get("department") != team["department"]:
                # Update person's department to match team's department
                person["department"] = team["department"]
                return (
                    True,
                    f"Person's department updated to '{team['department']}' to match team",
                )
    elif person.get("team"):
        # Removing person from team but keeping department assignment
        return True, "Person removed from team but kept department assignment"

    return True, "Assignment handled successfully"


def validate_imported_data(
    data: Dict[str, List[Dict[str, Any]]],
) -> Tuple[bool, Dict[str, List[str]]]:
    """
    Validate imported data against all relationship rules.

    Args:
        data: Dictionary containing people, teams, departments, and projects

    Returns:
        Tuple of (is_valid, validation_errors)
    """
    validation_errors = {
        "people": [],
        "teams": [],
        "departments": [],
        "projects": [],
    }

    # Validate people
    for person in data.get("people", []):
        is_valid, error_msg = validate_person_associations(person, data)
        if not is_valid:
            validation_errors["people"].append(
                f"Person '{person.get('name', 'Unknown')}': {error_msg}"
            )

    # Validate teams
    for team in data.get("teams", []):
        is_valid, error_msg = validate_team_associations(team, data)
        if not is_valid:
            validation_errors["teams"].append(
                f"Team '{team.get('name', 'Unknown')}': {error_msg}"
            )

    # Validate projects
    for project in data.get("projects", []):
        is_valid, conflicts = validate_project_resource_assignments(project, data)
        if not is_valid:
            for conflict in conflicts:
                validation_errors["projects"].append(
                    f"Project '{project.get('name', 'Unknown')}': {conflict}"
                )

    # Check for people in multiple teams
    team_memberships = {}
    for team in data.get("teams", []):
        for member in team.get("members", []):
            if member not in team_memberships:
                team_memberships[member] = []
            team_memberships[member].append(team.get("name", "Unknown"))

    for person, teams in team_memberships.items():
        if len(teams) > 1:
            validation_errors["people"].append(
                f"Person '{person}' belongs to multiple teams: {', '.join(teams)}. Must belong to only one team."
            )

    # Overall validation result
    is_valid = all(len(errors) == 0 for errors in validation_errors.values())

    return is_valid, validation_errors


def suggest_relationship_fixes(
    validation_errors: Dict[str, List[str]],
) -> Dict[str, List[str]]:
    """
    Suggest fixes for relationship validation errors.

    Args:
        validation_errors: Dictionary of validation errors by resource type

    Returns:
        Dictionary of suggested fixes by resource type
    """
    fixes = {
        "people": [],
        "teams": [],
        "departments": [],
        "projects": [],
    }

    # Generate suggested fixes for each type of error
    for resource_type, errors in validation_errors.items():
        for error in errors:
            if "belongs to multiple teams" in error:
                fixes["people"].append(f"Choose only one team for this person. {error}")
            elif "department must match team's department" in error:
                fixes["people"].append(
                    f"Update the person's department to match their team's department. {error}"
                )
            elif "is already assigned directly but also belongs to team" in error:
                fixes["projects"].append(
                    f"Choose either direct assignment or team assignment, not both. {error}"
                )
            elif "is assigned but its teams" in error:
                fixes["projects"].append(
                    f"Choose either department assignment or individual team assignments, not both. {error}"
                )
            elif "is assigned but person" in error:
                fixes["projects"].append(
                    f"Choose either department assignment or individual person assignments, not both. {error}"
                )

    return fixes
