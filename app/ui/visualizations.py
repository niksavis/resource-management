"""
Visualization components for the resource management application.

This module provides UI components for data visualization.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Any, List
from app.services.visualization_service import (
    prepare_gantt_data,
    prepare_utilization_data,
)
from app.services.config_service import (
    load_department_colors,
    load_currency_settings,
    load_heatmap_colorscale,
)


def display_gantt_chart(
    projects: List[Dict[str, Any]], resources: Dict[str, List[Dict[str, Any]]]
) -> None:
    """
    Display a Gantt chart for projects and resources.

    Args:
        projects: List of project dictionaries
        resources: Dictionary of resource lists (people, teams, departments)
    """
    gantt_data = prepare_gantt_data(projects, resources)

    if gantt_data.empty:
        st.info("No Gantt chart data available.")
        return

    fig = px.timeline(
        gantt_data,
        x_start="Start",
        x_end="End",
        y="Resource",
        color="Project",
        title="Gantt Chart",
        labels={"Resource": "Resource", "Project": "Project"},
    )

    st.plotly_chart(fig, use_container_width=True)


def display_utilization_chart(
    projects: List[Dict[str, Any]], resources: Dict[str, List[Dict[str, Any]]]
) -> None:
    """
    Display a utilization chart for resources.

    Args:
        projects: List of project dictionaries
        resources: Dictionary of resource lists (people, teams, departments)
    """
    utilization_data = prepare_utilization_data(projects, resources)

    if utilization_data.empty:
        st.info("No utilization data available.")
        return

    fig = px.bar(
        utilization_data,
        x="Resource",
        y="Utilization %",
        color="Type",
        title="Resource Utilization",
        labels={"Resource": "Resource", "Utilization %": "Utilization %"},
    )

    st.plotly_chart(fig, use_container_width=True)


def display_sunburst_organization(data: Dict[str, List[Dict[str, Any]]]) -> None:
    """
    Display organizational structure as a sunburst chart.

    Args:
        data: Dictionary containing people, teams, and departments data
    """
    # Get department colors from settings
    dept_colors = load_department_colors()

    # Create a flattened DataFrame for the visualization
    rows = []

    # Add department level
    for dept in data["departments"]:
        dept_name = dept["name"]
        dept_color = dept_colors.get(dept_name, "#1f77b4")

        rows.append(
            {
                "id": dept_name,
                "parent": "",
                "name": dept_name,  # Add name field for departments
                "value": 1,
                "color": dept_color,
                "type": "Department",
            }
        )

        # Add teams level (children of departments)
        for team_name in dept.get("teams", []):
            rows.append(
                {
                    "id": f"{dept_name}-{team_name}",
                    "parent": dept_name,
                    "name": team_name,
                    "value": 1,
                    "color": dept_color,
                    "type": "Team",
                }
            )

    # Add people (children of teams or departments)
    for person in data["people"]:
        person_name = person["name"]
        dept_name = person.get("department", "Unassigned")
        team_name = person.get("team")

        # Get the appropriate parent
        if team_name:
            parent = f"{dept_name}-{team_name}"
        else:
            parent = dept_name

        rows.append(
            {
                "id": f"{parent}-{person_name}",
                "parent": parent,
                "name": person_name,
                "value": person.get("daily_cost", 1),
                "color": dept_colors.get(dept_name, "#1f77b4"),
                "type": "Person",
            }
        )

    # Create the DataFrame
    if not rows:
        st.info("No data available for organization chart.")
        return

    df = pd.DataFrame(rows)

    # Create a color map dictionary from the DataFrame
    color_map = {row["id"]: row["color"] for _, row in df.iterrows() if "color" in row}

    # Create the sunburst chart
    fig = px.sunburst(
        df,
        ids="id",
        names="name",
        parents="parent",
        values="value",
        color="id",
        title="Organization Structure",
        # Use actual dictionary instead of string "identity"
        color_discrete_map=color_map,
    )

    # Update layout
    fig.update_layout(
        margin=dict(t=30, l=0, r=0, b=0),
        height=600,
    )

    # Display the chart
    st.plotly_chart(fig, use_container_width=True)


def display_department_distribution(
    departments: List[Dict[str, Any]], department_colors: Dict[str, str] = None
) -> None:
    """
    Display department distribution visualization.

    Args:
        departments: List of department dictionaries
        department_colors: Dictionary mapping department names to colors
    """
    if not departments:
        st.info("No department data available for visualization.")
        return

    # Get department colors if not provided
    if department_colors is None:
        department_colors = load_department_colors()

    # Calculate department stats
    dept_stats = []
    for dept in departments:
        dept_name = dept["name"]
        team_count = len(dept.get("teams", []))
        member_count = len(dept.get("members", []))

        dept_stats.append(
            {
                "Department": dept_name,
                "Teams": team_count,
                "Members": member_count,
                "Color": department_colors.get(dept_name, "#1f77b4"),
            }
        )

    if not dept_stats:
        st.info("No department data to display.")
        return

    # Create DataFrame
    dept_df = pd.DataFrame(dept_stats)

    # Create visualization
    fig = px.bar(
        dept_df,
        x="Department",
        y=["Teams", "Members"],
        title="Department Distribution",
        labels={"value": "Count", "variable": "Type"},
        color="Department",
        color_discrete_map={
            dept: color for dept, color in zip(dept_df["Department"], dept_df["Color"])
        },
    )

    st.plotly_chart(fig, use_container_width=True)
