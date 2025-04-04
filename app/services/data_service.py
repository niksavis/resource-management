"""
Data service for handling data loading, saving, and processing.
"""

import json
import base64
import streamlit as st
import pandas as pd
import numpy as np
import os
from typing import Dict, List, Any, Optional, Tuple
from app.services.config_service import (
    load_display_preferences,
    ensure_department_colors,
)
from app.utils.resource_utils import delete_resource


def load_demo_data() -> Dict[str, List[Dict[str, Any]]]:
    """Load the demo data from the JSON file."""
    try:
        with open("resource_data.json", "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        st.error(f"Error loading demo data: {str(e)}")
        # Return minimal empty data structure
        return {
            "people": [],
            "teams": [],
            "departments": [],
            "projects": [],
        }


def save_data(
    data: Dict[str, List[Dict[str, Any]]], filename: str = "resource_data.json"
) -> bool:
    """Save data to a JSON file."""
    try:
        with open(filename, "w") as file:
            json.dump(data, file, indent=4)
        return True
    except Exception as e:
        st.error(f"Error saving data: {str(e)}")
        return False


def load_json(file) -> Dict[str, Any]:
    """Load data from a JSON file upload."""
    try:
        return json.loads(file.getvalue().decode("utf-8"))
    except json.JSONDecodeError:
        st.error("The uploaded file is not a valid JSON file.")
        return {}


def save_json(data: Dict[str, Any], filename: str) -> str:
    """Save data as a downloadable JSON file."""
    try:
        json_str = json.dumps(data, indent=4)
        b64 = base64.b64encode(json_str.encode()).decode()
        return f'<a href="data:application/json;base64,{b64}" download="{filename}">Download {filename}</a>'
    except Exception as e:
        st.error(f"Error creating download link: {str(e)}")
        return ""


def check_data_integrity():
    """Check and fix data integrity issues."""

    # Check for teams with insufficient members
    invalid_teams = [
        t["name"]
        for t in st.session_state.data["teams"]
        if len(t.get("members", [])) < 2
    ]

    if invalid_teams:
        st.warning(
            f"Found {len(invalid_teams)} teams with fewer than 2 members. These teams will be automatically removed."
        )
        for team_name in invalid_teams:
            delete_resource(st.session_state.data["teams"], team_name, "team")

    # Check for resources assigned to non-existent departments
    valid_departments = {d["name"] for d in st.session_state.data["departments"]}

    for person in st.session_state.data["people"]:
        if person.get("department") not in valid_departments:
            person["department"] = "Unassigned"

    for team in st.session_state.data["teams"]:
        if team.get("department") not in valid_departments:
            team["department"] = "Unassigned"


def create_gantt_data(
    projects: List[Dict[str, Any]], resources: Dict[str, List[Dict[str, Any]]]
) -> pd.DataFrame:
    """
    Create Gantt chart data from projects and resources.

    Args:
        projects: List of project dictionaries
        resources: Dictionary of resource lists (people, teams, departments)

    Returns:
        DataFrame containing Gantt chart data
    """
    gantt_data = []

    for project in projects:
        # Get project details
        project_name = project["name"]
        project_start = pd.to_datetime(project["start_date"])
        project_end = pd.to_datetime(project["end_date"])
        project_priority = project["priority"]

        # Get resource allocation details
        resource_allocations = project.get("resource_allocations", [])

        # If no specific resource allocations, assign default 100% allocation to all resources
        if not resource_allocations:
            for resource_name in project.get("assigned_resources", []):
                resource_type, dept, team = _determine_resource_type(
                    resource_name, resources
                )

                gantt_data.append(
                    {
                        "Project": project_name,
                        "Resource": resource_name,
                        "Type": resource_type,
                        "Department": dept,
                        "Team": team,  # Add team information here
                        "Start": project_start,
                        "End": project_end,
                        "Priority": project_priority,
                        "Allocation %": 100,
                    }
                )
        else:
            # Process specific resource allocations
            for allocation in resource_allocations:
                resource_name = allocation["resource"]
                resource_type, dept, team = _determine_resource_type(
                    resource_name, resources
                )
                alloc_start = pd.to_datetime(allocation["start_date"])
                alloc_end = pd.to_datetime(allocation["end_date"])
                alloc_percentage = allocation["allocation_percentage"]

                gantt_data.append(
                    {
                        "Project": project_name,
                        "Resource": resource_name,
                        "Type": resource_type,
                        "Department": dept,
                        "Team": team,  # Add team information here
                        "Start": alloc_start,
                        "End": alloc_end,
                        "Priority": project_priority,
                        "Allocation %": alloc_percentage,
                    }
                )

    # If no data was generated, return an empty DataFrame with the expected columns
    if not gantt_data:
        return pd.DataFrame(
            columns=[
                "Project",
                "Resource",
                "Type",
                "Department",
                "Team",
                "Start",
                "End",
                "Priority",
                "Allocation %",
            ]
        )

    # Create a DataFrame and calculate duration
    df = pd.DataFrame(gantt_data)
    df["Duration"] = (df["End"] - df["Start"]).dt.days + 1

    return df


def _determine_resource_type(
    resource: str, data: Dict[str, List[Dict[str, Any]]]
) -> Tuple[str, str, Optional[str]]:
    """
    Determine the type, department, and team of a resource.

    Args:
        resource: Resource name
        data: Dictionary containing people, teams, and departments data

    Returns:
        Tuple of (resource_type, department, team)
    """
    # Check if the resource is a person
    for person in data["people"]:
        if person["name"] == resource:
            return (
                "Person",
                person.get("department", "Unknown"),
                person.get("team", None),
            )

    # Check if the resource is a team
    for team in data["teams"]:
        if team["name"] == resource:
            return "Team", team.get("department", "Unknown"), None

    # Check if the resource is a department
    for department in data["departments"]:
        if department["name"] == resource:
            return "Department", department["name"], None

    # Default if resource is not found
    return "Unknown", "Unknown", None


def calculate_resource_utilization(gantt_data: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate resource utilization from Gantt data.

    Args:
        gantt_data: DataFrame containing Gantt chart data

    Returns:
        DataFrame with resource utilization metrics
    """
    if gantt_data.empty:
        return pd.DataFrame(
            columns=[
                "Resource",
                "Type",
                "Department",
                "Total Days",
                "Allocated Days",
                "Utilization %",
            ]
        )

    # Get the date range for the whole period
    min_date = gantt_data["Start"].min()
    max_date = gantt_data["End"].max()
    total_days = (max_date - min_date).days + 1

    # Create a result dataframe
    resources = gantt_data["Resource"].unique()
    result = []

    for resource in resources:
        resource_rows = gantt_data[gantt_data["Resource"] == resource]
        resource_type = resource_rows["Type"].iloc[0]
        department = resource_rows["Department"].iloc[0]

        # Calculate allocation per day
        daily_allocation = {}
        for _, row in resource_rows.iterrows():
            dates = pd.date_range(start=row["Start"], end=row["End"])
            allocation = row["Allocation %"] / 100

            for date in dates:
                daily_allocation[date] = daily_allocation.get(date, 0) + allocation

        # Calculate metrics
        allocated_days = sum(min(alloc, 1) for alloc in daily_allocation.values())
        over_allocated_days = sum(
            max(alloc - 1, 0) for alloc in daily_allocation.values()
        )
        avg_allocation = allocated_days / total_days * 100
        overallocation = over_allocated_days / total_days * 100

        result.append(
            {
                "Resource": resource,
                "Type": resource_type,
                "Department": department,
                "Total Days": total_days,
                "Allocated Days": allocated_days,
                "Utilization %": avg_allocation,
                "Overallocation %": overallocation,
            }
        )

    return pd.DataFrame(result)


def calculate_project_cost(
    project: Dict[str, Any], people: List[Dict[str, Any]], teams: List[Dict[str, Any]]
) -> float:
    """
    Calculate the cost of a project based on assigned resources.

    Args:
        project: Project dictionary
        people: List of people dictionaries
        teams: List of team dictionaries

    Returns:
        Total cost of the project
    """
    # Get project dates
    start_date = pd.to_datetime(project["start_date"])
    end_date = pd.to_datetime(project["end_date"])
    duration_days = (end_date - start_date).days + 1

    # Get resource allocations
    resource_allocations = project.get("resource_allocations", [])

    # If no specific allocations, use default 100% allocation for all resources
    if not resource_allocations:
        assigned_resources = project.get("assigned_resources", [])

        total_cost = 0
        for resource_name in assigned_resources:
            # Calculate cost for a person
            person = next((p for p in people if p["name"] == resource_name), None)
            if person:
                total_cost += person.get("daily_cost", 0) * duration_days
                continue

            # Calculate cost for a team
            team = next((t for t in teams if t["name"] == resource_name), None)
            if team:
                team_cost = sum(
                    person.get("daily_cost", 0)
                    for person in people
                    if person["name"] in team.get("members", [])
                )
                total_cost += team_cost * duration_days
                # Note: We don't handle departments directly in cost calculations

        return total_cost

    # With specific allocations, calculate based on each allocation
    total_cost = 0
    for allocation in resource_allocations:
        resource_name = allocation["resource"]
        allocation_percentage = allocation["allocation_percentage"] / 100
        alloc_start = pd.to_datetime(allocation["start_date"])
        alloc_end = pd.to_datetime(allocation["end_date"])
        alloc_duration_days = (alloc_end - alloc_start).days + 1

        # Calculate cost for a person
        person = next((p for p in people if p["name"] == resource_name), None)
        if person:
            resource_cost = (
                person.get("daily_cost", 0)
                * alloc_duration_days
                * allocation_percentage
            )
            total_cost += resource_cost
            continue

        # Calculate cost for a team
        team = next((t for t in teams if t["name"] == resource_name), None)
        if team:
            team_daily_cost = sum(
                person.get("daily_cost", 0)
                for person in people
                if person["name"] in team.get("members", [])
            )
            resource_cost = (
                team_daily_cost * alloc_duration_days * allocation_percentage
            )
            total_cost += resource_cost

    return total_cost


def parse_resources(resources: List[str]) -> Tuple[List[str], List[str], List[str]]:
    """
    Parse a list of resources into people, teams, and departments.

    Args:
        resources: List of resource names

    Returns:
        Tuple containing (people_list, teams_list, departments_list)
    """
    # Get the actual resource lists
    all_people = {p["name"] for p in st.session_state.data.get("people", [])}
    all_teams = {t["name"] for t in st.session_state.data.get("teams", [])}
    all_departments = {d["name"] for d in st.session_state.data.get("departments", [])}

    # Categorize the resources
    people = [r for r in resources if r in all_people]
    teams = [r for r in resources if r in all_teams]
    departments = [r for r in resources if r in all_departments]

    return people, teams, departments


def calculate_capacity_data(
    filtered_data: pd.DataFrame, start_date: pd.Timestamp, end_date: pd.Timestamp
) -> pd.DataFrame:
    """
    Calculate daily capacity data for each resource in the given date range.

    Args:
        filtered_data: Filtered DataFrame containing resource assignments
        start_date: Start date to calculate from
        end_date: End date to calculate to

    Returns:
        DataFrame with daily capacity data for each resource
    """
    if filtered_data.empty or start_date is None or end_date is None:
        return pd.DataFrame()

    # Create list to hold capacity data rows
    capacity_rows = []

    # Create date range
    date_range = pd.date_range(start=start_date, end=end_date)

    # Get unique resources
    resources = filtered_data["Resource"].unique()

    # Create a team lookup dictionary from the source data
    team_lookup = {}
    for person in st.session_state.data.get("people", []):
        if person.get("team"):
            team_lookup[person["name"]] = person["team"]

    # Create a lookup table for resource attributes
    resource_attributes = {}
    for resource in resources:
        resource_info = filtered_data[filtered_data["Resource"] == resource]
        if not resource_info.empty:
            resource_type = (
                resource_info["Type"].iloc[0]
                if "Type" in resource_info.columns
                else None
            )

            # Determine team value based on resource type and source data
            if resource_type == "Team":
                # For Team resources, set Team to their own name
                team = resource
            elif resource_type == "Person":
                # For Person resources, first check the team lookup (source data)
                team = team_lookup.get(resource)

                # If not found in lookup, fall back to filtered_data
                if team is None and "Team" in resource_info.columns:
                    team = resource_info["Team"].iloc[0]
            else:
                # For other resource types, use what's in the filtered data
                team = (
                    resource_info["Team"].iloc[0]
                    if "Team" in resource_info.columns
                    else None
                )

            department = (
                resource_info["Department"].iloc[0]
                if "Department" in resource_info.columns
                else None
            )

            # Store all attributes for each resource
            resource_attributes[resource] = {
                "Department": department,
                "Team": team,
                "Type": resource_type,
            }

    # For each resource and date, calculate allocation
    for date in date_range:
        for resource in resources:
            # Filter assignments for this resource on this date
            assignments = filtered_data[
                (filtered_data["Resource"] == resource)
                & (filtered_data["Start"] <= date)
                & (filtered_data["End"] >= date)
            ]

            # Calculate allocation for this resource on this date
            if not assignments.empty:
                # Sum all allocations for this resource on this date
                allocation = assignments["Allocation %"].sum()
            else:
                # No assignments for this resource on this date
                allocation = 0

            # Add row to capacity data - use the lookup table to ensure we have all attributes
            attrs = resource_attributes.get(resource, {})
            capacity_rows.append(
                {
                    "Date": date,
                    "Resource": resource,
                    "Allocation": allocation,
                    "Department": attrs.get("Department"),
                    "Team": attrs.get("Team"),
                    "Type": attrs.get("Type"),
                }
            )

    # Create DataFrame from rows
    capacity_df = pd.DataFrame(capacity_rows)
    return capacity_df


def apply_filters(df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
    """
    Apply filters to a DataFrame of Gantt data.

    Args:
        df: DataFrame to filter
        filters: Dictionary of filter conditions

    Returns:
        Filtered DataFrame
    """
    if df.empty:
        return df

    filtered_df = df.copy()

    # Apply search term filter
    if filters.get("search_term"):
        search_term = filters["search_term"].lower()
        mask = np.column_stack(
            [
                filtered_df[col]
                .astype(str)
                .str.lower()
                .str.contains(search_term, na=False)
                for col in ["Resource", "Project", "Type", "Department"]
                if col in filtered_df.columns
            ]
        )
        filtered_df = filtered_df[mask.any(axis=1)]

    # Apply date range filter
    date_range = filters.get("date_range", [])
    if len(date_range) >= 2 and date_range[0] is not None and date_range[1] is not None:
        start_date = pd.Timestamp(date_range[0])
        end_date = pd.Timestamp(date_range[1])
        filtered_df = filtered_df[
            (filtered_df["End"] >= start_date) & (filtered_df["Start"] <= end_date)
        ]

    # Apply resource type filter
    resource_types = filters.get("resource_types", [])
    if resource_types:
        filtered_df = filtered_df[filtered_df["Type"].isin(resource_types)]

    # Apply department filter
    dept_filter = filters.get("dept_filter", [])
    if dept_filter:
        filtered_df = filtered_df[filtered_df["Department"].isin(dept_filter)]

    # Apply project filter
    project_filter = filters.get("project_filter", [])
    if project_filter:
        filtered_df = filtered_df[filtered_df["Project"].isin(project_filter)]

    # Apply utilization threshold filter if this is a utilization dataframe
    if "Utilization %" in filtered_df.columns:
        threshold = filters.get("utilization_threshold", 0)
        if threshold > 0:
            filtered_df = filtered_df[filtered_df["Utilization %"] >= threshold]

    return filtered_df


def sort_projects_by_priority_and_date(
    projects: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Sort projects by priority (ascending) and end date (ascending).
    """
    return sorted(
        projects,
        key=lambda p: (
            p.get("priority", 999),  # Default high priority if missing
            pd.to_datetime(
                p.get("end_date", "2099-12-31")
            ),  # Default far future date if missing
        ),
    )


def paginate_dataframe(
    df: pd.DataFrame, key_prefix: str, items_per_page: Optional[int] = None
) -> pd.DataFrame:
    """
    Paginate a DataFrame and provide navigation.

    Args:
        df: DataFrame to paginate
        key_prefix: Prefix for session state keys
        items_per_page: Number of items per page. If None, uses settings.

    Returns:
        Paginated DataFrame
    """
    if items_per_page is None:
        # Get page size from settings
        display_prefs = load_display_preferences()
        items_per_page = display_prefs.get("page_size", 10)

    # Initialize page number in session state if not exists
    if f"{key_prefix}_page" not in st.session_state:
        st.session_state[f"{key_prefix}_page"] = 0

    # Calculate total pages
    n_pages = max(1, len(df) // items_per_page)

    # Only show pagination if needed
    if len(df) > items_per_page:
        # Create pagination controls
        col1, col2, col3 = st.columns([1, 3, 1])
        with col1:
            if st.button("◀️ Previous", key=f"{key_prefix}_prev"):
                st.session_state[f"{key_prefix}_page"] = max(
                    0, st.session_state[f"{key_prefix}_page"] - 1
                )
        with col2:
            st.write(f"Page {st.session_state[f'{key_prefix}_page'] + 1} of {n_pages}")
        with col3:
            if st.button("Next ▶️", key=f"{key_prefix}_next"):
                st.session_state[f"{key_prefix}_page"] = min(
                    n_pages - 1, st.session_state[f"{key_prefix}_page"] + 1
                )

    # Get current page number
    current_page = st.session_state[f"{key_prefix}_page"]

    # Calculate start and end indices
    start_idx = current_page * items_per_page
    end_idx = min(start_idx + items_per_page, len(df))

    # Return the sliced DataFrame
    return df.iloc[start_idx:end_idx].reset_index(drop=True)


def check_circular_dependencies():
    """
    Check for circular dependencies and other relationship issues in the data.

    Returns:
        Tuple of (cycles, multi_team_members, multi_department_members, multi_department_teams)
    """
    # Get data
    people = st.session_state.data["people"]
    teams = st.session_state.data["teams"]

    # Check for people in multiple teams
    team_memberships = {}
    for team in teams:
        for member in team.get("members", []):
            if member not in team_memberships:
                team_memberships[member] = []
            team_memberships[member].append(team["name"])

    multi_team_members = [
        (person, teams_list)
        for person, teams_list in team_memberships.items()
        if len(teams_list) > 1
    ]

    # Check for people in multiple departments
    department_memberships = {}
    for person in people:
        dept = person.get("department")
        if dept:
            if person["name"] not in department_memberships:
                department_memberships[person["name"]] = []
            department_memberships[person["name"]].append(dept)

    multi_department_members = [
        (person, depts_list)
        for person, depts_list in department_memberships.items()
        if len(depts_list) > 1
    ]

    # Check for teams in multiple departments
    team_departments = {}
    for team in teams:
        dept = team.get("department")
        # Only track teams that have a department assigned
        if dept and dept.strip():
            if team["name"] not in team_departments:
                team_departments[team["name"]] = []
            team_departments[team["name"]].append(dept)

    multi_department_teams = [
        (team, depts_list)
        for team, depts_list in team_departments.items()
        if len(depts_list) > 1
    ]

    # Build dependency graph and check for cycles
    graph = _build_dependency_graph()
    cycles = _find_cycles(graph)

    return cycles, multi_team_members, multi_department_members, multi_department_teams


def _build_dependency_graph():
    """
    Build a dependency graph from the current data.

    Returns:
        Dictionary representing the graph
    """
    graph = {}

    # Get data
    people = st.session_state.data["people"]
    teams = st.session_state.data["teams"]
    departments = st.session_state.data["departments"]

    # Add person → team edges
    for person in people:
        person_name = person["name"]
        team_name = person.get("team")

        if person_name not in graph:
            graph[person_name] = []

        if team_name:
            graph[person_name].append(team_name)

    # Add person → department edges
    for person in people:
        person_name = person["name"]
        dept_name = person.get("department")

        if person_name not in graph:
            graph[person_name] = []

        if dept_name:
            graph[person_name].append(dept_name)

    # Add team → department edges
    for team in teams:
        team_name = team["name"]
        dept_name = team.get("department")

        if team_name not in graph:
            graph[team_name] = []

        # Only add the edge if the department exists
        if dept_name and dept_name.strip():
            # Make sure the department exists in the departments list
            if any(d["name"] == dept_name for d in departments):
                graph[team_name].append(dept_name)

    # Add department → team edges (for teams in departments)
    for dept in departments:
        dept_name = dept["name"]
        teams_list = dept.get("teams", [])

        if dept_name not in graph:
            graph[dept_name] = []

        for team_name in teams_list:
            graph[dept_name].append(team_name)

    return graph


def _find_cycles(graph):
    """
    Find cycles in a directed graph using depth-first search.

    Args:
        graph: Dictionary representing the graph as an adjacency list

    Returns:
        List of cycles found in the graph
    """
    visited = set()  # Nodes visited in current traversal
    rec_stack = set()  # Nodes in current recursion stack
    all_cycles = []  # List to store all cycles found
    path = []  # Current path being explored

    def dfs(node, parent=None):
        # If we've already fully explored this node, no need to revisit
        if node in visited:
            return

        # If we encounter a node already in our recursion stack, we found a cycle
        if node in rec_stack:
            # Extract the cycle from the current path
            cycle_start_idx = path.index(node)
            cycle = path[cycle_start_idx:]
            # Add the starting node again to complete the cycle representation
            cycle.append(node)
            all_cycles.append(cycle)
            return

        # Mark node as visited in current recursion
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        # Visit all adjacent nodes
        for neighbor in graph.get(node, []):
            # Skip the parent to avoid simple back-and-forth cycles
            if neighbor != parent:
                dfs(neighbor, node)

        # Remove node from recursion stack when done
        rec_stack.remove(node)
        path.pop()

    # Start DFS from each node to find all cycles
    for node in graph:
        # Clear the tracking sets for each new starting node
        visited = set()
        rec_stack = set()
        path = []
        dfs(node)

    # De-duplicate cycles (same cycle may be found from different starting points)
    unique_cycles = []
    cycle_sets = set()

    for cycle in all_cycles:
        # Create a canonical representation of the cycle for deduplication
        # Sort the cycle to start with the smallest node
        min_node_idx = cycle.index(min(cycle))
        canonical = tuple(cycle[min_node_idx:-1] + cycle[:min_node_idx])

        if canonical not in cycle_sets:
            cycle_sets.add(canonical)
            unique_cycles.append(cycle)

    return unique_cycles


def get_resource_type(resource_name: str) -> str:
    """
    Determine the type of a resource by name.

    Args:
        resource_name: Name of the resource

    Returns:
        Resource type ('person', 'team', 'department', or 'unknown')
    """
    # Check if it's a person
    if any(p["name"] == resource_name for p in st.session_state.data["people"]):
        return "person"

    # Check if it's a team
    if any(t["name"] == resource_name for t in st.session_state.data["teams"]):
        return "team"

    # Check if it's a department
    if any(d["name"] == resource_name for d in st.session_state.data["departments"]):
        return "department"

    return "unknown"


def _apply_all_filters(
    df: pd.DataFrame,
    search_term: str,
    team_filter: List[str],
    dept_filter: List[str],
    member_filter: List[str],
    distinct_filters: bool,
    data_key: str,
) -> pd.DataFrame:
    """
    Apply all filters to a DataFrame.

    Args:
        df: DataFrame to filter
        search_term: Search term to filter by
        team_filter: List of teams to filter by
        dept_filter: List of departments to filter by
        member_filter: List of members to filter by
        distinct_filters: Whether to use distinct filters
        data_key: Key in session state data

    Returns:
        Filtered DataFrame
    """
    if search_term:
        mask = np.column_stack(
            [
                df[col]
                .fillna("")
                .astype(str)
                .str.contains(search_term, case=False, na=False)
                for col in df.columns
            ]
        )
        df = df[mask.any(axis=1)]

    if team_filter:
        if distinct_filters and data_key == "departments":
            df = df[df["teams"].apply(lambda x: any(team in x for team in team_filter))]
        else:
            df = df[df["team"].isin(team_filter)]

    if distinct_filters and data_key in ["departments", "teams"] and member_filter:
        df = df[
            df["members"].apply(lambda x: any(member in x for member in member_filter))
        ]

    if dept_filter:
        df = df[df["department"].isin(dept_filter)]

    return df


def find_resource_conflicts(
    gantt_data: pd.DataFrame, threshold: float = 1.0
) -> pd.DataFrame:
    """
    Find resource allocation conflicts (overallocations).

    Args:
        gantt_data: DataFrame containing Gantt chart data
        threshold: Allocation threshold above which a conflict is detected (default: 1.0)

    Returns:
        DataFrame with resource conflicts
    """
    if gantt_data.empty:
        return pd.DataFrame(
            columns=["Resource", "Type", "Department", "Date", "Allocation", "Projects"]
        )

    # Get the min and max dates
    min_date = gantt_data["Start"].min()
    max_date = gantt_data["End"].max()

    # Create a date range for all dates
    dates = pd.date_range(start=min_date, end=max_date)
    conflicts = []

    # For each resource, check daily allocations
    for resource in gantt_data["Resource"].unique():
        resource_data = gantt_data[gantt_data["Resource"] == resource]
        resource_type = resource_data["Type"].iloc[0]
        department = resource_data["Department"].iloc[0]

        # For each day, calculate total allocation and collect projects
        for date in dates:
            # Find allocations that include this date
            allocations = resource_data[
                (resource_data["Start"] <= date) & (resource_data["End"] >= date)
            ]
            total_allocation = allocations["Allocation %"].sum() / 100

            # If allocation exceeds threshold, report as conflict
            if total_allocation > threshold:
                conflicts.append(
                    {
                        "Resource": resource,
                        "Type": resource_type,
                        "Department": department,
                        "Date": date,
                        "Allocation": total_allocation * 100,  # As percentage
                        "Projects": ", ".join(allocations["Project"].tolist()),
                    }
                )

    return pd.DataFrame(conflicts)


def load_data() -> Dict[str, List[Dict[str, Any]]]:
    """Load data from the resource data file."""
    try:
        if os.path.exists("resource_data.json"):
            with open("resource_data.json", "r") as file:
                data = json.load(file)
            ensure_department_colors(data.get("departments", []))
            return data
        else:
            data = load_demo_data()
            save_data(data)
            ensure_department_colors(data.get("departments", []))
            return data
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return {"people": [], "teams": [], "departments": [], "projects": []}


def import_data(data: Dict[str, List[Dict[str, Any]]]) -> None:
    """
    Import data from an external source.

    Args:
        data: The data to import
    """
    save_data(data)
    st.session_state.data = data

    # Ensure all departments have colors assigned

    ensure_department_colors(data.get("departments", []))
