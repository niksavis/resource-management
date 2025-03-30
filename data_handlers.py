"""
Data handlers for resource management application.

This module contains functions for data loading, saving, and processing.
"""

import base64
import io
import json
import uuid
import numpy as np
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any, Union
from app.services.data_service import paginate_dataframe
from app.services.config_service import load_currency_settings


def load_json(file: Union[io.TextIOWrapper, io.BytesIO]) -> Dict[str, Any]:
    """
    Load data from a JSON file.

    Args:
        file: File object to load data from

    Returns:
        Loaded JSON data as a dictionary
    """
    try:
        if isinstance(file, io.BytesIO):
            return json.loads(file.getvalue().decode("utf-8"))
        else:
            return json.load(file)
    except Exception as e:
        st.error(f"Error loading JSON file: {str(e)}")
        return {}


def save_json(data: Dict[str, Any], filename: str) -> str:
    """
    Save data to a JSON file and return a download link.

    Args:
        data: Dictionary data to save
        filename: Name for the saved file

    Returns:
        HTML string containing a download link
    """
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
            return "Person", person["department"]

    # Check if the resource is a team
    for team in data["teams"]:
        if team["name"] == resource:
            return "Team", team["department"]

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
    # Get resource allocations
    resource_allocations = project.get("resource_allocations", [])

    # If no specific allocations, use default 100% allocation for all resources
    if not resource_allocations:
        assigned_resources = project.get("assigned_resources", [])
        start_date = pd.to_datetime(project["start_date"])
        end_date = pd.to_datetime(project["end_date"])
        duration_days = (end_date - start_date).days + 1

        total_cost = 0
        for resource_name in assigned_resources:
            # Calculate cost for a person
            person = next((p for p in people if p["name"] == resource_name), None)
            if person:
                total_cost += person["daily_cost"] * duration_days
                continue

            # Calculate cost for a team
            team = next((t for t in teams if t["name"] == resource_name), None)
            if team:
                team_cost = sum(
                    person["daily_cost"]
                    for person in people
                    if person["name"] in team["members"]
                )
                total_cost += team_cost * duration_days
                # Note: We don't handle departments directly in cost calculations

        return total_cost

    # With specific allocations, calculate based on each allocation
    total_cost = 0
    for allocation in resource_allocations:
        resource_name = allocation["resource"]
        allocation_percentage = allocation["allocation_percentage"] / 100
        start_date = pd.to_datetime(allocation["start_date"])
        end_date = pd.to_datetime(allocation["end_date"])
        duration_days = (end_date - start_date).days + 1

        # Calculate cost for a person
        person = next((p for p in people if p["name"] == resource_name), None)
        if person:
            resource_cost = person["daily_cost"] * duration_days * allocation_percentage
            total_cost += resource_cost
            continue

        # Calculate cost for a team
        team = next((t for t in teams if t["name"] == resource_name), None)
        if team:
            team_daily_cost = sum(
                person["daily_cost"]
                for person in people
                if person["name"] in team["members"]
            )
            resource_cost = team_daily_cost * duration_days * allocation_percentage
            total_cost += resource_cost

    return total_cost


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
        projects, key=lambda p: (p["priority"], pd.to_datetime(p["end_date"]))
    )


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


def parse_resources(resources: List[str]) -> Tuple[List[str], List[str], List[str]]:
    """
    Parse a list of resources into people, teams, and departments.

    Args:
        resources: List of resource names

    Returns:
        Tuple containing (people_list, teams_list, departments_list)
    """
    # This is a simplified implementation and would need to be adjusted
    # to your specific data structure

    # In an actual implementation, you would check against your data to determine types
    # Here we're just using a placeholder implementation
    people = []
    teams = []
    departments = []

    # For the purpose of this example, we'll parse based on naming conventions
    for resource in resources:
        # Example: Teams often have "Team" in their name
        if "Team" in resource:
            teams.append(resource)
        # Example: Departments might end with "Department"
        elif "Department" in resource:
            departments.append(resource)
        # Default to assuming it's a person
        else:
            people.append(resource)

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
    # Create a date range
    all_dates = pd.date_range(start=start_date, end=end_date)
    date_range = pd.DataFrame({"Date": all_dates})

    # Create a result dataframe with resources and dates
    resources = gantt_data["Resource"].unique()
    capacity_data = []

    for resource in resources:
        resource_rows = gantt_data[gantt_data["Resource"] == resource]
        resource_type = resource_rows["Type"].iloc[0]
        department = resource_rows["Department"].iloc[0]

        # Calculate daily allocation for this resource
        for date in all_dates:
            allocation = 0
            for _, row in resource_rows.iterrows():
                if row["Start"] <= date <= row["End"]:
                    allocation += row["Allocation %"] / 100

            capacity_data.append(
                {
                    "Resource": resource,
                    "Type": resource_type,
                    "Department": department,
                    "Date": date,
                    "Allocation": allocation,
                    "Available": max(0, 1 - allocation),
                    "Overallocated": max(0, allocation - 1),
                }
            )

    return pd.DataFrame(capacity_data)


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
