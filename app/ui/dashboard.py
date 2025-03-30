"""
Dashboard UI components.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Any, List
from datetime import datetime

from app.utils.ui_components import display_action_bar
from app.services.config_service import (
    load_currency_settings,
    load_display_preferences,
    load_utilization_thresholds,
    load_department_colors,
)
from data_handlers import (
    create_gantt_data,
    calculate_resource_utilization,
    calculate_project_cost,
)


def display_home_tab():
    """Display the main dashboard/home screen."""
    display_action_bar()
    st.subheader("Resource Management Dashboard")

    # Summary metrics
    _display_summary_metrics()

    # Project timeline
    st.markdown("### Project Timeline")
    if st.session_state.data["projects"]:
        _display_project_timeline()
    else:
        st.info("No projects found. Add projects to see a timeline.")

    # Resource overview tabs
    st.markdown("### Resource Overview")
    tabs = st.tabs(["Department Allocation", "Utilization", "Budget Overview"])

    with tabs[0]:
        _display_department_allocation()

    with tabs[1]:
        _display_utilization_summary()

    with tabs[2]:
        _display_budget_overview()


def _display_summary_metrics():
    """Display the summary metrics section of the dashboard."""
    # Count metrics
    people_count = len(st.session_state.data["people"])
    teams_count = len(st.session_state.data["teams"])
    dept_count = len(st.session_state.data["departments"])
    project_count = len(st.session_state.data["projects"])

    # Display in a 4-column layout
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("People", people_count)
    with col2:
        st.metric("Teams", teams_count)
    with col3:
        st.metric("Departments", dept_count)
    with col4:
        st.metric("Projects", project_count)


def _display_project_timeline():
    """Display project timeline visualization."""
    # Create project dataframe for timeline
    projects_df = pd.DataFrame(
        [
            {
                "Project": p["name"],
                "Start": pd.to_datetime(p["start_date"]),
                "End": pd.to_datetime(p["end_date"]),
                "Priority": p["priority"],
                "Resources": len(p.get("assigned_resources", [])),
            }
            for p in st.session_state.data["projects"]
        ]
    )

    # Sort by priority
    projects_df = projects_df.sort_values(by="Priority")

    # Create timeline chart
    fig = px.timeline(
        projects_df,
        x_start="Start",
        x_end="End",
        y="Project",
        color="Priority",
        hover_data=["Resources"],
        labels={"Priority": "Priority (1=Highest)"},
        title="Project Timeline",
    )

    # Add today's date line - Fix for the timestamp handling issue
    today_date = datetime.now().date()

    # Add a simple vertical line annotation without using add_vline
    fig.add_shape(
        type="line",
        x0=today_date,
        x1=today_date,
        y0=0,
        y1=1,
        yref="paper",
        line=dict(color="red", width=2, dash="dash"),
    )

    # Add text annotation for "Today"
    fig.add_annotation(
        x=today_date,
        y=1.0,
        yref="paper",
        text="Today",
        showarrow=False,
        font=dict(color="red"),
        bgcolor="white",
        bordercolor="red",
        borderwidth=1,
    )

    # Display chart
    st.plotly_chart(fig, use_container_width=True)


def _display_department_allocation():
    """Display department allocation pie chart."""
    if not st.session_state.data["people"]:
        st.info("No people data available.")
        return

    # Create department counts
    dept_counts = {}
    for person in st.session_state.data["people"]:
        dept = person["department"]
        dept_counts[dept] = dept_counts.get(dept, 0) + 1

    # Create dataframe
    dept_df = pd.DataFrame(
        {"Department": list(dept_counts.keys()), "People": list(dept_counts.values())}
    )

    # Load department colors
    dept_colors = load_department_colors()
    color_map = {
        dept: color for dept, color in dept_colors.items() if dept in dept_counts
    }

    # Create pie chart
    fig = px.pie(
        dept_df,
        names="Department",
        values="People",
        title="People by Department",
        color="Department",
        color_discrete_map=color_map,
        hole=0.4,
    )

    # Display chart
    st.plotly_chart(fig, use_container_width=True)


def _display_utilization_summary():
    """Display utilization summary chart."""
    if not st.session_state.data["projects"] or not st.session_state.data["people"]:
        st.info("No project or resource data available.")
        return

    # Create Gantt data for utilization calculation
    gantt_data = create_gantt_data(
        st.session_state.data["projects"], st.session_state.data
    )

    if gantt_data.empty:
        st.info("No allocation data available.")
        return

    # Calculate utilization
    utilization_df = calculate_resource_utilization(gantt_data)

    if utilization_df.empty:
        st.info("No utilization data available.")
        return

    # Load thresholds
    thresholds = load_utilization_thresholds()
    under_threshold = thresholds.get("under", 50)
    over_threshold = thresholds.get("over", 100)

    # Create utilization metrics
    avg_utilization = utilization_df["Utilization %"].mean()
    over_utilized = len(
        utilization_df[utilization_df["Utilization %"] > over_threshold]
    )
    under_utilized = len(
        utilization_df[utilization_df["Utilization %"] < under_threshold]
    )

    # Display metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Average Utilization", f"{avg_utilization:.1f}%")
    with col2:
        st.metric(
            "Overutilized Resources",
            over_utilized,
            delta=f"{over_utilized}",
            delta_color="inverse",
        )
    with col3:
        st.metric(
            "Underutilized Resources",
            under_utilized,
            delta=f"{under_utilized}",
            delta_color="inverse",
        )

    # Create bar chart of top 10 most utilized resources
    top_utilized = utilization_df.sort_values("Utilization %", ascending=False).head(10)

    fig = px.bar(
        top_utilized,
        x="Resource",
        y="Utilization %",
        color="Type",
        title="Top 10 Most Utilized Resources",
        labels={"Resource": "Resource", "Utilization %": "Utilization %"},
        color_discrete_map={
            "Person": "#1f77b4",
            "Team": "#ff7f0e",
            "Department": "#2ca02c",
        },
    )

    # Add threshold lines
    fig.add_hline(y=over_threshold, line_width=2, line_dash="dash", line_color="red")
    fig.add_hline(y=under_threshold, line_width=2, line_dash="dash", line_color="blue")

    # Display chart
    st.plotly_chart(fig, use_container_width=True)


def _display_budget_overview():
    """Display budget overview chart."""
    if not st.session_state.data["projects"]:
        st.info("No project data available.")
        return

    # Get currency symbol
    currency, _ = load_currency_settings()

    # Create budget data
    budget_data = []
    for project in st.session_state.data["projects"]:
        if "allocated_budget" in project:
            actual_cost = calculate_project_cost(
                project, st.session_state.data["people"], st.session_state.data["teams"]
            )

            budget_data.append(
                {
                    "Project": project["name"],
                    "Allocated Budget": project["allocated_budget"],
                    "Estimated Cost": actual_cost,
                }
            )

    if not budget_data:
        st.info("No budget data available.")
        return

    # Create dataframe
    budget_df = pd.DataFrame(budget_data)

    # Create grouped bar chart
    fig = go.Figure()

    # Add bars for budget and cost
    fig.add_trace(
        go.Bar(
            x=budget_df["Project"],
            y=budget_df["Allocated Budget"],
            name=f"Allocated Budget ({currency})",
            marker_color="blue",
        )
    )

    fig.add_trace(
        go.Bar(
            x=budget_df["Project"],
            y=budget_df["Estimated Cost"],
            name=f"Estimated Cost ({currency})",
            marker_color="red",
        )
    )

    # Update layout
    fig.update_layout(
        title="Budget vs. Estimated Cost by Project",
        xaxis_title="Project",
        yaxis_title=f"Amount ({currency})",
        barmode="group",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    # Format y-axis with currency symbol and thousands separator
    fig.update_layout(yaxis=dict(tickprefix=f"{currency} ", separatethousands=True))

    # Display chart
    st.plotly_chart(fig, use_container_width=True)
