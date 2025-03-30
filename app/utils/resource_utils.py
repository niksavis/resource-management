"""
Resource-specific utility functions for resource management application.
"""

import streamlit as st
from typing import List, Dict, Any, Tuple, Optional


def delete_resource(
    resource_list: List[Dict[str, Any]],
    resource_name: str,
    resource_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Delete a resource from the given resource list by name.

    Optionally, handles additional cleanup based on the resource type.

    Args:
        resource_list: List of resource dictionaries
        resource_name: Name of the resource to delete
        resource_type: Type of resource ('team', 'department', etc.)

    Returns:
        Updated resource list with the resource removed
    """
    # Filter out the resource to delete
    updated_list = [r for r in resource_list if r.get("name") != resource_name]

    # Update related entities based on resource type
    if resource_type == "team":
        # Remove the team from all people
        for person in st.session_state.data["people"]:
            if person.get("team") == resource_name:
                person["team"] = None

        # Remove the team from all departments
        for dept in st.session_state.data["departments"]:
            if "teams" in dept and resource_name in dept["teams"]:
                dept["teams"].remove(resource_name)

    elif resource_type == "department":
        # Remove the department from all people
        for person in st.session_state.data["people"]:
            if person.get("department") == resource_name:
                person["department"] = "Unassigned"  # Default value

        # Remove the department from all teams
        for team in st.session_state.data["teams"]:
            if team.get("department") == resource_name:
                team["department"] = "Unassigned"  # Default value

    elif resource_type == "person":
        # Remove the person from all teams
        for team in st.session_state.data["teams"]:
            if "members" in team and resource_name in team["members"]:
                team["members"].remove(resource_name)

        # Remove the person from all projects
        for project in st.session_state.data["projects"]:
            if (
                "assigned_resources" in project
                and resource_name in project["assigned_resources"]
            ):
                project["assigned_resources"].remove(resource_name)

    return updated_list


def get_resource_projects(resource_name: str) -> List[str]:
    """
    Get all projects that a resource is assigned to.

    Args:
        resource_name: Name of the resource

    Returns:
        List of project names
    """
    projects = []

    for project in st.session_state.data["projects"]:
        if resource_name in project.get("assigned_resources", []):
            projects.append(project["name"])

    return projects


def get_resource_by_name(resource_name: str) -> Tuple[Dict[str, Any], str]:
    """
    Find a resource by name and determine its type.

    Args:
        resource_name: Name of the resource to find

    Returns:
        Tuple of (resource_dict, resource_type) where resource_type is 'person', 'team', or 'department'.
        Returns ({}, 'unknown') if not found.
    """
    # Check people
    for person in st.session_state.data["people"]:
        if person["name"] == resource_name:
            return person, "person"

    # Check teams
    for team in st.session_state.data["teams"]:
        if team["name"] == resource_name:
            return team, "team"

    # Check departments
    for dept in st.session_state.data["departments"]:
        if dept["name"] == resource_name:
            return dept, "department"

    # Not found
    return {}, "unknown"


def find_resources_by_skill(skill: str) -> List[Dict[str, Any]]:
    """
    Find all resources that have a specific skill.

    Args:
        skill: Skill to search for

    Returns:
        List of resources with the specified skill
    """
    resources = []

    for person in st.session_state.data["people"]:
        if "skills" in person and skill in person["skills"]:
            resources.append(person)

    return resources


def calculate_team_cost(team_name: str) -> float:
    """
    Calculate the total daily cost of a team.

    Args:
        team_name: Name of the team

    Returns:
        Total daily cost of the team
    """
    team = next(
        (t for t in st.session_state.data["teams"] if t["name"] == team_name), None
    )

    if not team:
        return 0.0

    total_cost = 0.0
    for member_name in team.get("members", []):
        person = next(
            (p for p in st.session_state.data["people"] if p["name"] == member_name),
            None,
        )
        if person:
            total_cost += person.get("daily_cost", 0.0)

    return total_cost


def calculate_department_cost(department_name: str) -> float:
    """
    Calculate the total daily cost of a department.

    Args:
        department_name: Name of the department

    Returns:
        Total daily cost of the department
    """
    total_cost = 0.0

    # Add costs of all people in the department
    for person in st.session_state.data["people"]:
        if person.get("department") == department_name:
            total_cost += person.get("daily_cost", 0.0)

    return total_cost
