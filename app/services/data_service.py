"""
Data service for handling data loading, saving, and processing.
"""

import json
import base64
import streamlit as st
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from configuration import load_display_preferences


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
    from app.utils.resource_utils import delete_resource

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
                resource_type, dept = _determine_resource_type(resource_name, resources)

                gantt_data.append(
                    {
                        "Project": project_name,
                        "Resource": resource_name,
                        "Type": resource_type,
                        "Department": dept,
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
                resource_type, dept = _determine_resource_type(resource_name, resources)
                alloc_start = pd.to_datetime(allocation["start_date"])
                alloc_end = pd.to_datetime(allocation["end_date"])
                alloc_percentage = allocation["allocation_percentage"]

                gantt_data.append(
                    {
                        "Project": project_name,
                        "Resource": resource_name,
                        "Type": resource_type,
                        "Department": dept,
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
) -> Tuple[str, str]:
    """
    Determine the type and department of a resource.

    Args:
        resource: Resource name
        data: Dictionary containing people, teams, and departments data

    Returns:
        Tuple of (resource_type, department)
    """
    # Check if the resource is a person
    for person in data["people"]:
        if person["name"] == resource:
            return "Person", person.get("department", "Unknown")

    # Check if the resource is a team
    for team in data["teams"]:
        if team["name"] == resource:
            return "Team", team.get("department", "Unknown")

    # Check if the resource is a department
    for department in data["departments"]:
        if department["name"] == resource:
            return "Department", department["name"]

    # Default if resource is not found
    return "Unknown", "Unknown"


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

    # Create a date range for the entire period
    all_dates = pd.date_range(start=min_date, end=max_date)

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
    gantt_data: pd.DataFrame, start_date: pd.Timestamp, end_date: pd.Timestamp
) -> pd.DataFrame:
    """
    Calculate capacity data for resources in the given date range.

    Args:
        gantt_data: DataFrame containing Gantt chart data
        start_date: Start date for capacity calculation
        end_date: End date for capacity calculation

    Returns:
        DataFrame with capacity data
    """
    if gantt_data.empty:
        return pd.DataFrame(
            columns=[
                "Resource",
                "Type",
                "Department",
                "Date",
                "Allocation",
                "Available",
                "Overallocated",
            ]
        )

    # Create a date range
    all_dates = pd.date_range(start=start_date, end=end_date)

    # Get all resources from Gantt data
    resources = gantt_data["Resource"].unique()

    # For each resource and date, calculate allocation
    capacity_data = []

    for resource in resources:
        resource_rows = gantt_data[gantt_data["Resource"] == resource]
        resource_type = resource_rows["Type"].iloc[0]
        department = resource_rows["Department"].iloc[0]

        # For each date in range, calculate total allocation
        for date in all_dates:
            # Get allocations for this resource on this date
            allocations = resource_rows[
                (resource_rows["Start"] <= date) & (resource_rows["End"] >= date)
            ]

            # Calculate total allocation percentage
            total_allocation = allocations["Allocation %"].sum() / 100

            # Calculate availability and over-allocation
            available = max(0, 1 - total_allocation)  # Can't be less than 0
            overallocated = max(0, total_allocation - 1)  # Can't be less than 0

            capacity_data.append(
                {
                    "Resource": resource,
                    "Type": resource_type,
                    "Department": department,
                    "Date": date,
                    "Allocation": total_allocation,
                    "Available": available,
                    "Overallocated": overallocated,
                }
            )

    return pd.DataFrame(capacity_data)


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

    Args:
        projects: List of project dictionaries

    Returns:
        Sorted list of projects
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


def check_circular_dependencies() -> Tuple[
    List[str], Dict[str, List[str]], Dict[str, List[str]], Dict[str, List[str]]
]:
    """
    Check for circular dependencies between teams and report individuals in multiple teams,
    multiple departments, and teams in multiple departments.

    Returns:
        Tuple containing:
        - List of circular dependency paths
        - Dict of people in multiple teams
        - Dict of people in multiple departments
        - Dict of teams in multiple departments
    """
    dependency_graph = {}
    multi_team_members = {}
    multi_department_members = {}
    multi_department_teams = {}

    # Build dependency graph and check for multi-team or multi-department members
    team_membership = {}
    department_membership = {}
    team_departments = {}

    for team in st.session_state.data["teams"]:
        dependency_graph[team["name"]] = set()
        team_departments[team["name"]] = team["department"]

        for member in team["members"]:
            if member in team_membership:
                if member not in multi_team_members:
                    multi_team_members[member] = [team_membership[member]]
                multi_team_members[member].append(team["name"])
            team_membership[member] = team["name"]

        for other_team in st.session_state.data["teams"]:
            if team != other_team and any(
                member in other_team["members"] for member in team["members"]
            ):
                dependency_graph[team["name"]].add(other_team["name"])

    for department in st.session_state.data["departments"]:
        for member in department["members"]:
            if member in department_membership:
                if member not in multi_department_members:
                    multi_department_members[member] = [department_membership[member]]
                multi_department_members[member].append(department["name"])
            department_membership[member] = department["name"]

        for team in department["teams"]:
            if team in team_departments:
                if team_departments[team] != department["name"]:
                    if team not in multi_department_teams:
                        multi_department_teams[team] = [team_departments[team]]
                    multi_department_teams[team].append(department["name"])

    # Check for cycles
    visited = set()
    path = set()
    cycle_paths = []

    def dfs(node, current_path=None):
        if current_path is None:
            current_path = []

        if node in path:
            # Cycle detected - capture the full path
            cycle_path = current_path + [node]
            cycle_paths.append(" → ".join(cycle_path))
            return True

        if node in visited:
            return False

        visited.add(node)
        path.add(node)
        current_path.append(node)

        for neighbor in dependency_graph.get(node, []):
            if dfs(neighbor, current_path):
                return True

        path.remove(node)
        current_path.pop()
        return False

    for node in dependency_graph:
        dfs(node, [])

    return (
        cycle_paths,
        multi_team_members,
        multi_department_members,
        multi_department_teams,
    )


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
