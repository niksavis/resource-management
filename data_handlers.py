import io
import json
import base64
import pandas as pd
import numpy as np
import math
import streamlit as st
from datetime import datetime
from typing import List, Dict, Tuple


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
                    "Duration": (
                        pd.to_datetime(project["end_date"])
                        - pd.to_datetime(project["start_date"])
                    ).days
                    + 1,
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
    date_range = pd.date_range(start=start_date, end=end_date)
    resource_dates = pd.DataFrame(0, index=date_range, columns=["count"])

    for _, row in resource_df.iterrows():
        project_start = max(row["Start"], start_date)
        project_end = min(row["Finish"], end_date)
        project_dates = pd.date_range(start=project_start, end=project_end)

        for date in project_dates:
            if date in resource_dates.index:
                resource_dates.loc[date, "count"] += 1

    days_utilized = (resource_dates["count"] > 0).sum()
    days_overallocated = (resource_dates["count"] > 1).sum()

    return days_utilized, days_overallocated


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
        if len(df) > 20:
            page_size = st.slider(
                "Rows per page",
                min_value=10,
                max_value=100,
                value=20,
                step=10,
                key=f"page_size_{key}",
            )
            total_pages = math.ceil(len(df) / page_size)
            page_num = st.number_input(
                "Page",
                min_value=1,
                max_value=total_pages,
                value=1,
                step=1,
                key=f"page_num_{key}",
            )
            start_idx = (page_num - 1) * page_size
            end_idx = min(start_idx + page_size, len(df))
            st.write(f"Showing {start_idx + 1} to {end_idx} of {len(df)} entries")
            df = df.iloc[start_idx:end_idx]

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
        resources_list: List of resource names

    Returns:
        Tuple of (assigned_people, assigned_teams, assigned_departments)
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
