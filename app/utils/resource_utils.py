"""
Resource utility functions for the resource management application.

This module provides utility functions for resource CRUD operations.
"""

import streamlit as st
from typing import List, Dict, Any, Optional


def find_resource_by_name(
    resources: List[Dict[str, Any]], name: str
) -> Optional[Dict[str, Any]]:
    """
    Find a resource by name.

    Args:
        resources: List of resource dictionaries
        name: Name of the resource to find

    Returns:
        Resource dictionary or None if not found
    """
    for resource in resources:
        if resource.get("name") == name:
            return resource
    return None


def add_resource(resource_list: List[Dict[str, Any]], resource: Dict[str, Any]) -> bool:
    """
    Add a resource to the resource list.

    Args:
        resource_list: List of resources to add to
        resource: Resource to add

    Returns:
        True if successful, False otherwise
    """
    # Check if resource with same name already exists
    if any(r.get("name") == resource.get("name") for r in resource_list):
        return False

    resource_list.append(resource)
    return True


def update_resource(
    resource_list: List[Dict[str, Any]],
    resource_name: str,
    updated_resource: Dict[str, Any],
) -> bool:
    """
    Update a resource in the resource list.

    Args:
        resource_list: List of resources to update
        resource_name: Name of the resource to update
        updated_resource: Updated resource data

    Returns:
        True if successful, False otherwise
    """
    for i, resource in enumerate(resource_list):
        if resource.get("name") == resource_name:
            resource_list[i] = updated_resource
            return True
    return False


def delete_resource(
    resource_list: List[Dict[str, Any]], resource_name: str, resource_type: str
) -> bool:
    """
    Delete a resource from the resource list.

    Args:
        resource_list: List of resources to delete from
        resource_name: Name of the resource to delete
        resource_type: Type of the resource (for logging purposes)

    Returns:
        True if successful, False otherwise
    """
    for i, resource in enumerate(resource_list):
        if resource.get("name") == resource_name:
            del resource_list[i]
            st.success(
                f"{resource_type.title()} '{resource_name}' deleted successfully."
            )
            return True

    st.error(f"{resource_type.title()} '{resource_name}' not found.")
    return False


def update_resource_references(
    resource_name: str, new_name: str, resource_type: str
) -> None:
    """
    Update references to a resource across the application when its name changes.

    Args:
        resource_name: Original name of the resource
        new_name: New name of the resource
        resource_type: Type of the resource ('person', 'team', or 'department')
    """
    if resource_name == new_name:
        return

    # Update references in teams
    if resource_type == "person":
        for team in st.session_state.data["teams"]:
            if resource_name in team.get("members", []):
                team["members"].remove(resource_name)
                team["members"].append(new_name)

    # Update references in departments
    if resource_type in ["person", "team"]:
        for dept in st.session_state.data["departments"]:
            if resource_type == "person" and resource_name in dept.get("members", []):
                dept["members"].remove(resource_name)
                dept["members"].append(new_name)
            elif resource_type == "team" and resource_name in dept.get("teams", []):
                dept["teams"].remove(resource_name)
                dept["teams"].append(new_name)

    # Update references in projects
    for project in st.session_state.data["projects"]:
        # Update assigned resources
        if resource_name in project.get("assigned_resources", []):
            project["assigned_resources"].remove(resource_name)
            project["assigned_resources"].append(new_name)

        # Update resource allocations
        for allocation in project.get("resource_allocations", []):
            if allocation.get("resource") == resource_name:
                allocation["resource"] = new_name


def calculate_team_cost(team: Dict[str, Any], people: List[Dict[str, Any]]) -> float:
    """
    Calculate the daily cost of a team based on its members.

    Args:
        team: Team dictionary with at least a 'members' list
        people: List of people dictionaries with at least 'name' and 'daily_cost' fields

    Returns:
        Total daily cost of the team
    """
    if not team or "members" not in team:
        return 0.0

    total_cost = 0.0

    # Sum the daily costs of all team members
    for member_name in team["members"]:
        for person in people:
            if person["name"] == member_name:
                total_cost += person.get("daily_cost", 0.0)
                break

    return total_cost


def calculate_department_cost(
    department: Dict[str, Any],
    teams: List[Dict[str, Any]],
    people: List[Dict[str, Any]],
) -> float:
    """
    Calculate the daily cost of a department based on its members and teams.

    Args:
        department: Department dictionary with at least 'members' and 'teams' lists
        teams: List of team dictionaries
        people: List of people dictionaries

    Returns:
        Total daily cost of the department
    """
    if not department:
        return 0.0

    total_cost = 0.0

    # Sum costs of direct members
    for member_name in department.get("members", []):
        for person in people:
            if person["name"] == member_name:
                total_cost += person.get("daily_cost", 0.0)
                break

    # Sum costs of teams in the department
    for team_name in department.get("teams", []):
        for team in teams:
            if team["name"] == team_name:
                team_cost = calculate_team_cost(team, people)
                total_cost += team_cost
                break

    return total_cost
