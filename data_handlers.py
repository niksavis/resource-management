"""
Data Handlers Module

This module contains functions for loading, parsing, and processing
resource and project data. It serves as the data layer for the
resource management application.
"""

# Standard library imports
import base64
import io
import json
import uuid
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# Third-party imports
import numpy as np
import pandas as pd
import streamlit as st

# Local module imports
from calculation_helpers import calculate_project_duration, is_resource_overallocated
from utils import paginate_dataframe


def load_json(file: io.TextIOWrapper) -> Dict[str, any]:
    """Loads and returns JSON data from a file safely."""
    try:
        return json.load(file)
    except json.JSONDecodeError as e:
        st.error(f"Invalid JSON format: {e}")
        return None
    except IOError as e:
        st.error(f"File I/O error: {e}")
        return None
    except Exception as e:
        st.error(f"Unexpected error while loading JSON: {e}")
        return None


def save_json(data: Dict[str, any], filename: str) -> str:
    """Generates a download link for JSON data."""
    try:
        json_str = json.dumps(data, indent=4)
        b64 = base64.b64encode(json_str.encode()).decode()
        return f'<a href="data:application/json;base64,{b64}" download="{filename}">Download JSON file</a>'
    except (TypeError, ValueError) as e:
        st.error(f"Error serializing JSON data: {e}")
        return ""
    except Exception as e:
        st.error(f"Unexpected error while saving JSON: {e}")
        return ""


def create_gantt_data(
    projects: List[Dict[str, any]], resources: Dict[str, any]
) -> pd.DataFrame:
    """Converts project and resource data into a DataFrame for Gantt chart visualization."""
    try:
        df_data = []
        for project in projects:
            for resource in project["assigned_resources"]:
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
    except KeyError as e:
        st.error(f"Missing key in project or resource data: {e}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Unexpected error while creating Gantt data: {e}")
        return pd.DataFrame()


def _determine_resource_type(resource: str, data: Dict[str, any]) -> Tuple[str, str]:
    """Identifies whether the resource is a person, team, or department."""
    people_dict = {p["name"]: p["department"] for p in data["people"]}
    team_dict = {t["name"]: t["department"] for t in data["teams"]}
    dept_set = {d["name"] for d in data["departments"]}

    if resource in people_dict:
        return "Person", people_dict[resource]
    elif resource in team_dict:
        return "Team", team_dict[resource]
    elif resource in dept_set:
        return "Department", resource
    return "Unknown", "Unknown"


def calculate_date_range(
    gantt_data: pd.DataFrame,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> Tuple[datetime, datetime, int]:
    """Determines the date range for utilization calculation."""
    if start_date is None:
        start_date = gantt_data["Start"].min()
    if end_date is None:
        end_date = gantt_data["Finish"].max()

    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

    total_period_days = max(1, (end_date - start_date).days + 1)

    return start_date, end_date, total_period_days


def calculate_resource_allocation(
    resource_df: pd.DataFrame, start_date: datetime, end_date: datetime
) -> Tuple[int, int]:
    """Calculates allocation metrics for a single resource."""
    resources_per_day = {}

    for _, row in resource_df.iterrows():
        project_start = max(row["Start"], start_date)
        project_end = min(row["Finish"], end_date)

        project_dates = pd.date_range(start=project_start, end=project_end)

        for date in project_dates:
            resources_per_day[date] = resources_per_day.get(date, 0) + 1

    days_utilized = len(resources_per_day)
    days_overallocated = sum(1 for count in resources_per_day.values() if count > 1)

    return days_utilized, days_overallocated


@st.cache_data(ttl=3600)
def calculate_resource_utilization(
    gantt_data: pd.DataFrame,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> pd.DataFrame:
    """Computes utilization metrics for each resource."""
    if gantt_data.empty:
        return pd.DataFrame()

    start_date, end_date, total_period_days = calculate_date_range(
        gantt_data, start_date, end_date
    )

    resource_utilization = []

    for resource in gantt_data["Resource"].unique():
        resource_df = gantt_data[gantt_data["Resource"] == resource]

        if resource_df.empty:
            continue

        resource_type = resource_df["Type"].iloc[0]
        department = resource_df["Department"].iloc[0]

        days_utilized, days_overallocated = calculate_resource_allocation(
            resource_df, start_date, end_date
        )

        utilization_percentage = (days_utilized / total_period_days) * 100
        overallocation_percentage = (
            (days_overallocated / total_period_days) * 100 if days_utilized > 0 else 0
        )

        if resource_type == "Person":
            person = next(
                (p for p in st.session_state.data["people"] if p["name"] == resource),
                None,
            )
            cost = calculate_person_cost(person) if person else 0.0
        elif resource_type == "Team":
            team = next(
                (t for t in st.session_state.data["teams"] if t["name"] == resource),
                None,
            )
            cost = (
                calculate_team_cost(team, st.session_state.data["people"])
                if team
                else 0.0
            )
        else:
            cost = 0.0

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
                ),
                "Cost (€)": f"{cost:,.2f}",
            }
        )

    return pd.DataFrame(resource_utilization)


def filter_dataframe(
    df: pd.DataFrame, key: str, columns: Optional[List[str]] = None
) -> pd.DataFrame:
    """Enhances a DataFrame with search, sort, and pagination capabilities."""
    if columns is None:
        columns = df.columns

    # Generate a unique prefix for this instance of filter_dataframe
    unique_prefix = f"{key}_{uuid.uuid4().hex[:8]}"

    for col in df.columns:
        if df[col].apply(lambda v: isinstance(v, list)).any():
            df[col] = df[col].apply(
                lambda v: ", ".join(map(str, v)) if isinstance(v, list) else str(v)
            )

    with st.expander(
        f"Search and Filter {key.replace('_', ' ').title()}", expanded=False
    ):
        search_term = st.text_input(
            f"Search {key.replace('_', ' ').title()}", key=f"search_{unique_prefix}"
        )

        col_filters = st.columns(min(4, len(columns)))
        active_filters = {}

        for i, col in enumerate(columns):
            with col_filters[i % 4]:
                if df[col].dtype == "object" or df[col].dtype == "string":
                    unique_col_key = f"filter_{unique_prefix}_{col}"  # Unique key for each column filter
                    unique_values = sorted(df[col].dropna().unique())
                    if len(unique_values) < 15:
                        selected = st.multiselect(
                            f"Filter {col}",
                            options=unique_values,
                            default=[],
                            key=unique_col_key,
                        )
                        if selected:
                            active_filters[col] = selected

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

        for col, values in active_filters.items():
            df = df[df[col].isin(values)]

        if not df.empty:
            sort_options = ["None"] + list(df.columns)
            sort_col = st.selectbox(
                "Sort by", options=sort_options, key=f"sort_{unique_prefix}"
            )
            if sort_col != "None":
                ascending = st.checkbox("Ascending", True, key=f"asc_{unique_prefix}")
                df = df.sort_values(
                    by=sort_col, ascending=ascending, na_position="first"
                )

        df = paginate_dataframe(df, unique_prefix)  # Use unique prefix for pagination

    return df


def find_resource_conflicts(df: pd.DataFrame) -> List[Dict[str, any]]:
    """Identifies and returns a list of resource conflicts in the data."""
    conflicts = []
    for resource in df["Resource"].unique():
        resource_df = df[df["Resource"] == resource]
        if len(resource_df) > 1:
            for i, row1 in resource_df.iterrows():
                for j, row2 in resource_df.iterrows():
                    if i < j:
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


def parse_resources(
    resources_list: List[str],
) -> Tuple[List[str], List[str], List[str]]:
    """Parses the assigned resources into people, teams, and departments."""
    people_names = [person["name"] for person in st.session_state.data["people"]]
    team_names = [team["name"] for team in st.session_state.data["teams"]]

    assigned_people = []
    assigned_teams = []
    assigned_departments = set()

    for r in resources_list:
        if r in people_names:
            assigned_people.append(r)
            person_data = next(
                (p for p in st.session_state.data["people"] if p["name"] == r),
                None,
            )
            if person_data and person_data["department"]:
                assigned_departments.add(person_data["department"])
        elif r in team_names:
            assigned_teams.append(r)
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


@st.cache_data
def calculate_person_cost(person: Dict[str, any]) -> float:
    """Calculate the cost of a person based on their daily cost, work days, and daily work hours."""
    if not person.get("daily_cost") or not person.get("work_days"):
        return 0.0

    work_days_per_week = len(person["work_days"])
    daily_cost = person["daily_cost"]
    return daily_cost * work_days_per_week * 4.33


@st.cache_data
def calculate_team_cost(team: Dict[str, any], people: List[Dict[str, any]]) -> float:
    """Calculate the cost of a team by summing the costs of its members."""
    member_costs = [
        calculate_person_cost(person)
        for person in people
        if person["name"] in team["members"]
    ]
    return sum(member_costs)


@st.cache_data
def calculate_department_cost(
    department: Dict[str, any],
    people: List[Dict[str, any]],
    teams: List[Dict[str, any]],
) -> float:
    """Calculate the cost of a department by summing the costs of its people and teams."""
    people_cost = sum(
        calculate_person_cost(person)
        for person in people
        if person["department"] == department["name"]
    )

    team_cost = sum(
        calculate_team_cost(team, people)
        for team in teams
        if team["department"] == department["name"]
    )

    return people_cost + team_cost


@st.cache_data
def calculate_project_cost(
    project: Dict[str, any], people: List[Dict[str, any]], teams: List[Dict[str, any]]
) -> float:
    """Calculate the cost of a project based on its assigned resources and duration."""
    try:
        start_date = (
            project["start_date"].strftime("%Y-%m-%d")
            if isinstance(project["start_date"], pd.Timestamp)
            else project["start_date"]
        )
        end_date = (
            project["end_date"].strftime("%Y-%m-%d")
            if isinstance(project["end_date"], pd.Timestamp)
            else project["end_date"]
        )

        start_date = datetime.strptime(start_date, "%Y-%m-%d")
        end_date = datetime.strptime(end_date, "%Y-%m-%d")
        duration_days = (end_date - start_date).days + 1

        resource_costs = 0.0
        for resource in project["assigned_resources"]:
            person = next((p for p in people if p["name"] == resource), None)
            if person:
                resource_costs += calculate_person_cost(person)

            team = next((t for t in teams if t["name"] == resource), None)
            if team:
                resource_costs += calculate_team_cost(team, people)

        return resource_costs * duration_days
    except KeyError as e:
        st.error(f"Missing key in project data: {e}")
        return 0.0
    except ValueError as e:
        st.error(f"Invalid date format in project data: {e}")
        return 0.0
    except Exception as e:
        st.error(f"Unexpected error while calculating project cost: {e}")
        return 0.0
