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
