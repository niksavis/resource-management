"""
Visualization service for the resource management application.

This module provides data transformation and preparation for visualizations.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List
from datetime import datetime, timedelta


def prepare_gantt_data(
    projects: List[Dict[str, Any]], resources: Dict[str, List[Dict[str, Any]]]
) -> pd.DataFrame:
    """
    Prepare data for Gantt chart visualization.

    Args:
        projects: List of project dictionaries
        resources: Dictionary of resource lists (people, teams, departments)

    Returns:
        DataFrame with Gantt chart data
    """
    gantt_data = []

    for project in projects:
        # Get project details
        project_name = project["name"]
        project_start = pd.to_datetime(project["start_date"])
        project_end = pd.to_datetime(project["end_date"])

        # Process resource allocations
        resource_allocations = project.get("resource_allocations", [])

        # If no specific allocations, use assigned resources with 100% allocation
        if not resource_allocations and "assigned_resources" in project:
            for resource_name in project["assigned_resources"]:
                resource_type, dept = _determine_resource_type(resource_name, resources)

                gantt_data.append(
                    {
                        "Project": project_name,
                        "Resource": resource_name,
                        "Type": resource_type,
                        "Department": dept,
                        "Start": project_start,
                        "End": project_end,
                        "Allocation %": 100,
                    }
                )
        else:
            # Process specific allocations
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
                        "Allocation %": alloc_percentage,
                    }
                )

    # Create DataFrame
    if not gantt_data:
        return pd.DataFrame(
            columns=[
                "Project",
                "Resource",
                "Type",
                "Department",
                "Start",
                "End",
                "Allocation %",
            ]
        )

    df = pd.DataFrame(gantt_data)
    df["Duration"] = (df["End"] - df["Start"]).dt.days + 1
    return df


def prepare_utilization_data(
    projects: List[Dict[str, Any]], resources: Dict[str, List[Dict[str, Any]]]
) -> pd.DataFrame:
    """
    Prepare data for utilization visualization.

    Args:
        projects: List of project dictionaries
        resources: Dictionary of resource lists (people, teams, departments)

    Returns:
        DataFrame with utilization data
    """
    # First create Gantt data
    gantt_data = prepare_gantt_data(projects, resources)

    if gantt_data.empty:
        return pd.DataFrame(columns=["Resource", "Type", "Department", "Utilization %"])

    # Get the min and max dates for the entire period
    min_date = gantt_data["Start"].min()
    max_date = gantt_data["End"].max()
    total_days = (max_date - min_date).days + 1

    # Calculate utilization per resource
    resources = gantt_data["Resource"].unique()
    utilization_data = []

    for resource in resources:
        resource_data = gantt_data[gantt_data["Resource"] == resource]
        resource_type = resource_data["Type"].iloc[0]
        department = resource_data["Department"].iloc[0]

        # Calculate allocation per day
        daily_allocation = {}
        for _, row in resource_data.iterrows():
            dates = pd.date_range(start=row["Start"], end=row["End"])
            allocation = row["Allocation %"] / 100

            for date in dates:
                daily_allocation[date] = daily_allocation.get(date, 0) + allocation

        # Calculate metrics
        allocated_days = sum(min(alloc, 1) for alloc in daily_allocation.values())
        over_allocated_days = sum(
            max(alloc - 1, 0) for alloc in daily_allocation.values()
        )
        utilization_pct = allocated_days / total_days * 100

        utilization_data.append(
            {
                "Resource": resource,
                "Type": resource_type,
                "Department": department,
                "Utilization %": utilization_pct,
                "Overallocation %": over_allocated_days / total_days * 100,
            }
        )

    return pd.DataFrame(utilization_data)


def prepare_capacity_data(
    gantt_data: pd.DataFrame, start_date: pd.Timestamp, end_date: pd.Timestamp
) -> pd.DataFrame:
    """
    Prepare data for capacity visualization.

    Args:
        gantt_data: DataFrame with Gantt chart data
        start_date: Start date for the capacity calculation
        end_date: End date for the capacity calculation

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

    # Create capacity data
    resources = gantt_data["Resource"].unique()
    capacity_data = []

    for resource in resources:
        resource_rows = gantt_data[gantt_data["Resource"] == resource]
        resource_type = resource_rows["Type"].iloc[0]
        department = resource_rows["Department"].iloc[0]

        # For each date, calculate allocation
        for date in all_dates:
            # Get allocations for this resource on this date
            allocations = resource_rows[
                (resource_rows["Start"] <= date) & (resource_rows["End"] >= date)
            ]

            # Calculate total allocation
            total_allocation = allocations["Allocation %"].sum() / 100

            # Calculate availability and overallocation
            available = max(0, 1 - total_allocation)
            overallocated = max(0, total_allocation - 1)

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


def prepare_budget_data(
    projects: List[Dict[str, Any]],
    people: List[Dict[str, Any]],
    teams: List[Dict[str, Any]],
) -> pd.DataFrame:
    """
    Prepare data for budget visualization.

    Args:
        projects: List of project dictionaries
        people: List of people dictionaries
        teams: List of team dictionaries

    Returns:
        DataFrame with budget data
    """
    budget_data = []

    for project in projects:
        if "allocated_budget" in project:
            # Calculate actual cost based on resources
            actual_cost = calculate_project_cost(project, people, teams)

            budget_data.append(
                {
                    "Project": project["name"],
                    "Allocated Budget": project["allocated_budget"],
                    "Estimated Cost": actual_cost,
                    "Variance": project["allocated_budget"] - actual_cost,
                    "Variance %": (project["allocated_budget"] - actual_cost)
                    / project["allocated_budget"]
                    * 100
                    if project["allocated_budget"] > 0
                    else 0,
                }
            )

    if not budget_data:
        return pd.DataFrame(
            columns=[
                "Project",
                "Allocated Budget",
                "Estimated Cost",
                "Variance",
                "Variance %",
            ]
        )

    return pd.DataFrame(budget_data)


def _determine_resource_type(
    resource: str, data: Dict[str, List[Dict[str, Any]]]
) -> tuple:
    """
    Determine the type and department of a resource.

    Args:
        resource: Resource name
        data: Dictionary containing people, teams, and departments data

    Returns:
        Tuple of (resource_type, department)
    """
    # Check if it's a person
    for person in data.get("people", []):
        if person["name"] == resource:
            return "Person", person.get("department", "Unknown")

    # Check if it's a team
    for team in data.get("teams", []):
        if team["name"] == resource:
            return "Team", team.get("department", "Unknown")

    # Check if it's a department
    for department in data.get("departments", []):
        if department["name"] == resource:
            return "Department", department["name"]

    return "Unknown", "Unknown"


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
        Total project cost
    """
    # Get resource allocations
    resource_allocations = project.get("resource_allocations", [])

    # If no specific allocations, use default allocation
    if not resource_allocations:
        start_date = pd.to_datetime(project["start_date"])
        end_date = pd.to_datetime(project["end_date"])
        duration_days = (end_date - start_date).days + 1
        assigned_resources = project.get("assigned_resources", [])

        total_cost = 0
        for resource_name in assigned_resources:
            # Check if it's a person
            person = next((p for p in people if p["name"] == resource_name), None)
            if person:
                total_cost += person.get("daily_cost", 0) * duration_days
                continue

            # Check if it's a team
            team = next((t for t in teams if t["name"] == resource_name), None)
            if team:
                # Sum the daily costs of all team members
                team_cost = sum(
                    next(
                        (p.get("daily_cost", 0) for p in people if p["name"] == member),
                        0,
                    )
                    for member in team.get("members", [])
                )
                total_cost += team_cost * duration_days

        return total_cost

    # Process specific allocations
    total_cost = 0
    for allocation in resource_allocations:
        resource_name = allocation["resource"]
        alloc_start = pd.to_datetime(allocation["start_date"])
        alloc_end = pd.to_datetime(allocation["end_date"])
        duration = (alloc_end - alloc_start).days + 1
        allocation_pct = allocation["allocation_percentage"] / 100

        # Check if it's a person
        person = next((p for p in people if p["name"] == resource_name), None)
        if person:
            resource_cost = person.get("daily_cost", 0) * duration * allocation_pct
            total_cost += resource_cost
            continue

        # Check if it's a team
        team = next((t for t in teams if t["name"] == resource_name), None)
        if team:
            # Sum the daily costs of all team members
            team_cost = sum(
                next((p.get("daily_cost", 0) for p in people if p["name"] == member), 0)
                for member in team.get("members", [])
            )
            resource_cost = team_cost * duration * allocation_pct
            total_cost += resource_cost

    return total_cost
