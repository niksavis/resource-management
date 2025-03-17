"""
Data Handlers Module

This module contains functions for loading, parsing, and processing
resource and project data. It serves as the data layer for the
resource management application.

Expected JSON structure:
{
    "people": [...],
    "teams": [...],
    "departments": [...],
    "projects": [...]
}
"""

import io
import json
import base64
import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime
from typing import List, Dict, Tuple
from utils import paginate_dataframe  # Import the new function
from testable_functions import (
    calculate_project_duration,
    is_resource_overallocated,
)  # Import testable functions


def load_json(file: io.TextIOWrapper) -> Dict:
    """
    Loads and returns JSON data from a file safely.
    """
    try:
        data = json.load(file)
        return data
    except Exception as e:
        st.error(f"Error loading JSON file: {e}")
        return None


def save_json(data: Dict, filename: str) -> str:
    """
    Generates a download link for JSON data.
    """
    json_str = json.dumps(data, indent=4)
    b64 = base64.b64encode(json_str.encode()).decode()
    href = f'<a href="data:application/json;base64,{b64}" download="{filename}">Download JSON file</a>'
    return href


def create_gantt_data(projects: List[Dict], resources: Dict) -> pd.DataFrame:
    """
    Converts project and resource data into a DataFrame suitable for Gantt chart visualization.
    """
    df_data = []

    for project in projects:
        for resource in project["assigned_resources"]:
            # Identify resource type once
            r_type, department = _determine_resource_type(resource, resources)
            df_data.append(
                {
                    "Resource": resource,
                    "Type": r_type,
                    "Department": department,
                    "Project": project["name"],
                    "Start": pd.to_datetime(project["start_date"]),
                    "Finish": pd.to_datetime(project["end_date"]),
                    "Priority": project["priority"],
                    "Duration": calculate_project_duration(
                        pd.to_datetime(project["start_date"]),
                        pd.to_datetime(project["end_date"]),
                    ),
                }
            )

    return pd.DataFrame(df_data)


def _determine_resource_type(resource: str, data: Dict) -> Tuple[str, str]:
    """
    Identifies whether the resource is a person, team, or department.
    Uses dictionary lookups for better performance.

    Args:
        resource: Name of the resource
        data: Dictionary containing people, teams, and departments

    Returns:
        Tuple of (resource_type, department)
    """
    # Create dictionaries for faster lookups
    people_dict = {p["name"]: p["department"] for p in data["people"]}
    team_dict = {t["name"]: t["department"] for t in data["teams"]}
    dept_set = {d["name"] for d in data["departments"]}

    # Check resource type using dictionary lookups
    if resource in people_dict:
        return ("Person", people_dict[resource])
    elif resource in team_dict:
        return ("Team", team_dict[resource])
    elif resource in dept_set:
        return ("Department", resource)

    return ("Unknown", "Unknown")


def calculate_date_range(gantt_data: pd.DataFrame, start_date=None, end_date=None):
    """Determines the date range for utilization calculation."""
    if start_date is None:
        start_date = gantt_data["Start"].min()
    if end_date is None:
        end_date = gantt_data["Finish"].max()

    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

    # Avoid division by zero
    total_period_days = max(1, (end_date - start_date).days + 1)

    return start_date, end_date, total_period_days


def calculate_resource_allocation(resource_df: pd.DataFrame, start_date, end_date):
    """Calculates allocation metrics for a single resource."""
    resources_per_day = {}

    for _, row in resource_df.iterrows():
        project_start = max(row["Start"], start_date)
        project_end = min(row["Finish"], end_date)

        # Create date range once
        project_dates = pd.date_range(start=project_start, end=project_end)

        # Add dates to dictionary in one go
        for date in project_dates:
            resources_per_day[date] = resources_per_day.get(date, 0) + 1

    # Calculate metrics
    days_utilized = len(resources_per_day)
    days_overallocated = sum(1 for count in resources_per_day.values() if count > 1)

    return days_utilized, days_overallocated


@st.cache_data(ttl=3600)
def calculate_resource_utilization(
    gantt_data: pd.DataFrame, start_date: datetime = None, end_date: datetime = None
) -> pd.DataFrame:
    """
    Computes utilization metrics for each resource.
    """
    if gantt_data.empty:
        return pd.DataFrame()

    # Get date range for calculation
    start_date, end_date, total_period_days = calculate_date_range(
        gantt_data, start_date, end_date
    )

    # Calculate utilization for each resource
    resource_utilization = []

    for resource in gantt_data["Resource"].unique():
        resource_df = gantt_data[gantt_data["Resource"] == resource]

        # Safeguard against empty dataframes
        if resource_df.empty:
            continue

        resource_type = resource_df["Type"].iloc[0]
        department = resource_df["Department"].iloc[0]

        # Calculate allocation for this resource
        days_utilized, days_overallocated = calculate_resource_allocation(
            resource_df, start_date, end_date
        )

        # Calculate metrics with safeguards
        utilization_percentage = (days_utilized / total_period_days) * 100
        overallocation_percentage = (
            (days_overallocated / total_period_days) * 100 if days_utilized > 0 else 0
        )

        resource_utilization.append(
            {
                "Resource": resource,
                "Type": resource_type,
                "Department": department,
                "Days Utilized": days_utilized,
                "Total Period Days": total_period_days,
                "Utilization %": utilization_percentage,
                "Days Overallocated": days_overallocated,
                "Overallocation %": overallocation_percentage,
                "Projects": len(resource_df),
                "Overallocated": is_resource_overallocated(
                    days_overallocated, total_period_days
                ),  # Use the new function
            }
        )

    return pd.DataFrame(resource_utilization)


def filter_dataframe(
    df: pd.DataFrame, key: str, columns: List[str] = None
) -> pd.DataFrame:
    """
    Enhances a DataFrame with search, sort, and pagination capabilities.
    """
    if columns is None:
        columns = df.columns

    # Ensure columns with lists are converted to strings to avoid unhashable type errors
    for col in df.columns:
        if df[col].apply(lambda v: isinstance(v, list)).any():
            df[col] = df[col].apply(
                lambda v: ", ".join(map(str, v)) if isinstance(v, list) else str(v)
            )

    with st.expander(f"Search and Filter {key}", expanded=False):
        search_term = st.text_input(f"Search {key}", key=f"search_{key}")

        # Create filter for each column
        col_filters = st.columns(min(4, len(columns)))
        active_filters = {}

        for i, col in enumerate(columns):
            with col_filters[i % 4]:
                if df[col].dtype == "object" or df[col].dtype == "string":
                    unique_values = sorted(df[col].dropna().unique())
                    if len(unique_values) < 15:
                        selected = st.multiselect(
                            f"Filter {col}",
                            options=unique_values,
                            default=[],
                            key=f"filter_{key}_{col}",
                        )
                        if selected:
                            active_filters[col] = selected

        # Apply search term across all columns
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

        # Apply column filters
        for col, values in active_filters.items():
            df = df[df[col].isin(values)]

        # Sorting
        if not df.empty:
            sort_options = ["None"] + list(df.columns)
            sort_col = st.selectbox("Sort by", options=sort_options, key=f"sort_{key}")
            if sort_col != "None":
                ascending = st.checkbox("Ascending", True, key=f"asc_{key}")
                df = df.sort_values(
                    by=sort_col, ascending=ascending, na_position="first"
                )

        # Pagination
        df = paginate_dataframe(df, key)

    return df


def find_resource_conflicts(df: pd.DataFrame) -> List[Dict]:
    """
    Identifies and returns a list of resource conflicts in the data.
    """
    conflicts = []
    for resource in df["Resource"].unique():
        resource_df = df[df["Resource"] == resource]
        if len(resource_df) > 1:
            # Check for date overlaps
            for i, row1 in resource_df.iterrows():
                for j, row2 in resource_df.iterrows():
                    if i < j:  # Avoid comparing the same pair twice
                        if (row1["Start"] <= row2["Finish"]) and (
                            row1["Finish"] >= row2["Start"]
                        ):
                            conflicts.append(
                                {
                                    "resource": resource,
                                    "project1": row1["Project"],
                                    "project2": row2["Project"],
                                    "overlap_start": max(row1["Start"], row2["Start"]),
                                    "overlap_end": min(row1["Finish"], row2["Finish"]),
                                    "overlap_days": (
                                        min(row1["Finish"], row2["Finish"])
                                        - max(row1["Start"], row2["Start"])
                                    ).days
                                    + 1,
                                }
                            )
    return conflicts


def parse_resources(resources_list):
    """
    Parses the assigned resources into people, teams, and departments.

    Args:
        resources_list: List of resource names (e.g., ["John Smith", "Backend Team"])

    Returns:
        Tuple of (assigned_people, assigned_teams, assigned_departments)

    Example:
        >>> parse_resources(["John Smith", "Backend Team"])
        (["John Smith"], ["Backend Team"], ["Software Development"])
    """
    people_names = [person["name"] for person in st.session_state.data["people"]]
    team_names = [team["name"] for team in st.session_state.data["teams"]]

    assigned_people = []
    assigned_teams = []
    assigned_departments = set()

    for r in resources_list:
        if r in people_names:
            assigned_people.append(r)
            # Add the person's department
            person_data = next(
                (p for p in st.session_state.data["people"] if p["name"] == r),
                None,
            )
            if person_data and person_data["department"]:
                assigned_departments.add(person_data["department"])
        elif r in team_names:
            assigned_teams.append(r)
            # Add the departments of all team members
            team_data = next(
                (t for t in st.session_state.data["teams"] if t["name"] == r),
                None,
            )
            if team_data and team_data["members"]:
                for member in team_data["members"]:
                    person_data = next(
                        (
                            p
                            for p in st.session_state.data["people"]
                            if p["name"] == member
                        ),
                        None,
                    )
                    if person_data and person_data["department"]:
                        assigned_departments.add(person_data["department"])

    return assigned_people, assigned_teams, list(assigned_departments)
