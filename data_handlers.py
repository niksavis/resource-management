import base64
import io
import json
import uuid
from datetime import datetime
from typing import Dict, List, Tuple, Optional

import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px

from utils import paginate_dataframe
from configuration import load_currency_settings


def load_json(file: io.TextIOWrapper) -> Dict[str, any]:
    """Loads and returns JSON data from a file safely."""
    try:
        data = json.load(file)
        for person in data.get("people", []):
            person["capacity_hours_per_week"] = person["daily_work_hours"] * len(
                person["work_days"]
            )
            person["capacity_hours_per_month"] = (
                person["capacity_hours_per_week"] * 4.33
            )
        return data
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


@st.cache_data(ttl=3600)
def calculate_resource_utilization(
    gantt_data: pd.DataFrame,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> pd.DataFrame:
    """Computes utilization metrics for each resource."""
    if gantt_data.empty:  # Explicitly check if DataFrame is empty
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

        # Calculate days utilized by summing overlapping days for all projects
        days_utilized = 0
        for _, row in resource_df.iterrows():
            overlap_start = max(start_date, row["Start"])
            overlap_end = min(end_date, row["Finish"])
            if overlap_start <= overlap_end:
                days_utilized += (overlap_end - overlap_start).days + 1

        utilization_percentage = (days_utilized / total_period_days) * 100
        overallocation_percentage = max(0, utilization_percentage - 100)

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

        # Load currency settings
        currency, _ = load_currency_settings()
        resource_utilization.append(
            {
                "Resource": resource,
                "Type": resource_type,
                "Department": department,
                "Days Utilized": days_utilized,
                "Total Period Days": total_period_days,
                "Utilization %": utilization_percentage,
                "Overallocation %": overallocation_percentage,
                f"Cost ({currency})": cost,  # Dynamically set column name
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


def display_gantt_chart(gantt_data):
    """
    Displays a Gantt chart using the provided data.
    """
    if gantt_data.empty:
        st.warning("No data available to display the Gantt chart.")
        return

    # Sort resources by type and name
    gantt_data = gantt_data.sort_values(by=["Type", "Resource"])

    # Create the Gantt chart
    fig = px.timeline(
        gantt_data,
        x_start="Start",
        x_end="Finish",
        y="Resource",
        color="Project",
        title="Gantt Chart",
        hover_data=["Type", "Department", "Duration", "Priority"],
    )

    # Add a vertical line for today's date
    fig.add_vline(
        x=pd.Timestamp.now(), line_width=2, line_dash="dash", line_color="red"
    )

    # Update layout
    fig.update_layout(
        xaxis_title="Timeline",
        yaxis_title="Resources",
        legend_title="Projects",
        height=600,
    )

    # Display the chart
    st.plotly_chart(fig, use_container_width=True)


def display_utilization_dashboard(gantt_data: pd.DataFrame, start_date, end_date):
    """
    Displays a dashboard for resource utilization based on the provided Gantt data.
    """
    if gantt_data.empty:
        st.warning("No data available for utilization dashboard.")
        return

    # Calculate utilization metrics
    utilization_df = calculate_resource_utilization(gantt_data, start_date, end_date)

    if utilization_df.empty:
        st.warning("No utilization data available for the selected period.")
        return

    # Display summary metrics
    st.subheader("Utilization Summary")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Resources", len(utilization_df))
    col2.metric(
        "Average Utilization (%)", f"{utilization_df['Utilization %'].mean():.1f}"
    )
    col3.metric(
        "Average Overallocation (%)", f"{utilization_df['Overallocation %'].mean():.1f}"
    )

    # Display utilization chart
    st.subheader("Utilization by Resource")
    fig = px.bar(
        utilization_df,
        x="Resource",
        y="Utilization %",
        color="Type",
        hover_data=["Department", "Projects", "Cost"],
        title="Resource Utilization",
    )
    st.plotly_chart(fig, use_container_width=True)

    # Display overallocation chart
    st.subheader("Overallocation by Resource")
    overallocation_fig = px.bar(
        utilization_df,
        x="Resource",
        y="Overallocation %",
        color="Type",
        hover_data=["Department", "Projects", "Cost"],
        title="Resource Overallocation",
    )
    st.plotly_chart(overallocation_fig, use_container_width=True)

    # Display detailed utilization table
    st.subheader("Detailed Utilization Data")
    st.dataframe(utilization_df, use_container_width=True)


def sort_projects_by_priority_and_date(projects):
    """Sort projects by priority (ascending) and end date (ascending)."""
    return sorted(
        projects,
        key=lambda p: (p["priority"], pd.to_datetime(p["end_date"])),
    )


def calculate_resource_capacity(resource_name, resource_type, start_date, end_date):
    """Calculate total capacity hours for a resource over a date range."""
    if resource_type == "Person":
        person = next(
            (p for p in st.session_state.data["people"] if p["name"] == resource_name),
            None,
        )
        if not person:
            return 0

        # Calculate work days in the period
        date_range = pd.date_range(start=start_date, end=end_date)
        work_days_in_period = sum(
            1 for d in date_range if d.strftime("%a")[:2].upper() in person["work_days"]
        )

        # Calculate capacity
        return work_days_in_period * person["daily_work_hours"]

    elif resource_type == "Team":
        team = next(
            (t for t in st.session_state.data["teams"] if t["name"] == resource_name),
            None,
        )
        if not team:
            return 0

        # Sum capacity of all team members
        return sum(
            calculate_resource_capacity(member, "Person", start_date, end_date)
            for member in team["members"]
        )

    return 0


def calculate_resource_allocation(resource_name, start_date, end_date):
    """Calculate allocated hours for a resource across all projects."""
    total_allocated_hours = 0
    for project in st.session_state.data["projects"]:
        project_start = pd.to_datetime(project["start_date"])
        project_end = pd.to_datetime(project["end_date"])

        if project_end >= pd.Timestamp(start_date) and project_start <= pd.Timestamp(
            end_date
        ):
            assigned_resources = project["assigned_resources"]

            # Check if assigned_resources is a list or string
            if isinstance(assigned_resources, (list, str)):
                if resource_name in assigned_resources:
                    allocation = next(
                        (
                            a
                            for a in project.get("resource_allocations", [])
                            if a["resource"] == resource_name
                        ),
                        {"allocation_percentage": 100},
                    )
                    resource_type = (
                        "Person"
                        if resource_name
                        in [p["name"] for p in st.session_state.data["people"]]
                        else "Team"
                    )
                    capacity = calculate_resource_capacity(
                        resource_name, resource_type, project_start, project_end
                    )
                    allocated_hours = capacity * (
                        allocation["allocation_percentage"] / 100
                    )
                    total_allocated_hours += allocated_hours

            # Check if assigned_resources is a DataFrame or Series
            elif isinstance(assigned_resources, (pd.DataFrame, pd.Series)):
                if resource_name in assigned_resources.values:
                    allocation = next(
                        (
                            a
                            for a in project.get("resource_allocations", [])
                            if a["resource"] == resource_name
                        ),
                        {"allocation_percentage": 100},
                    )
                    resource_type = (
                        "Person"
                        if resource_name
                        in [p["name"] for p in st.session_state.data["people"]]
                        else "Team"
                    )
                    capacity = calculate_resource_capacity(
                        resource_name, resource_type, project_start, project_end
                    )
                    allocated_hours = capacity * (
                        allocation["allocation_percentage"] / 100
                    )
                    total_allocated_hours += allocated_hours

            # If assigned_resources is neither a list/string nor a DataFrame/Series
            else:
                st.warning(
                    f"Unexpected type for assigned_resources in project {project['name']}"
                )

    return total_allocated_hours


def calculate_capacity_data(start_date, end_date):
    """Calculate capacity and allocation data for all resources."""
    capacity_data = []

    # Calculate for people
    for person in st.session_state.data["people"]:
        capacity = calculate_resource_capacity(
            person["name"], "Person", start_date, end_date
        )
        allocation = calculate_resource_allocation(person["name"], start_date, end_date)

        capacity_data.append(
            {
                "Resource": person["name"],
                "Type": "Person",
                "Department": person["department"],
                "Capacity (hours)": capacity,
                "Allocated (hours)": allocation,
                "Utilization %": (allocation / capacity * 100) if capacity > 0 else 0,
                "Available (hours)": max(0, capacity - allocation),
            }
        )

    # Calculate for teams
    for team in st.session_state.data["teams"]:
        capacity = calculate_resource_capacity(
            team["name"], "Team", start_date, end_date
        )
        allocation = calculate_resource_allocation(team["name"], start_date, end_date)

        capacity_data.append(
            {
                "Resource": team["name"],
                "Type": "Team",
                "Department": team["department"],
                "Capacity (hours)": capacity,
                "Allocated (hours)": allocation,
                "Utilization %": (allocation / capacity * 100) if capacity > 0 else 0,
                "Available (hours)": max(0, capacity - allocation),
            }
        )

    return pd.DataFrame(capacity_data)


def calculate_project_duration(start_date: datetime, end_date: datetime) -> int:
    """Calculate project duration in days."""
    return (end_date - start_date).days + 1


def is_resource_overallocated(
    allocation_days: int, total_days: int, threshold: float = 0.8
) -> bool:
    """Determine if a resource is overallocated based on percentage."""
    return (allocation_days / total_days) > threshold
