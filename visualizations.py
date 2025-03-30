"""
Visualization functions for resource management application.

This module provides functions for creating visual representations of resource data.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime, timedelta

from data_handlers import (
    calculate_resource_utilization,
    calculate_capacity_data,
    find_resource_conflicts,
)
from configuration import (
    load_utilization_thresholds,
    load_display_preferences,
    load_heatmap_colorscale,
    load_department_colors,
    load_currency_settings,
)


def _prepare_gantt_data(df: pd.DataFrame, projects_to_include=None) -> pd.DataFrame:
    """
    Prepare data for Gantt chart visualization from a DataFrame.

    Args:
        df: DataFrame containing resource allocation data
        projects_to_include: List of project names to include (if None, include all)

    Returns:
        DataFrame formatted for Gantt chart visualization
    """
    if df.empty:
        return pd.DataFrame()

    # Filter by projects if specified
    if projects_to_include is not None:
        df = df[df["Project"].isin(projects_to_include)]

    # Create a copy to avoid modifying the original
    gantt_df = df.copy()

    # Format for Gantt chart:
    # - Task: Resource name
    # - Start: Start date
    # - Finish: End date
    # - Resource: Resource name
    # - Project: Project name
    # - Allocation: Allocation percentage

    # Rename columns to match Plotly Gantt chart expectations
    gantt_df = gantt_df.rename(
        columns={
            "Resource": "Task",
            "Start": "Start",
            "End": "Finish",
            "Allocation %": "Allocation",
        }
    )

    # Add color column based on resource type
    gantt_df["Color"] = gantt_df["Type"].map(
        {
            "Person": "#1f77b4",  # Blue
            "Team": "#ff7f0e",  # Orange
            "Department": "#2ca02c",  # Green
        }
    )

    # Sort by resource type, department, then resource name
    gantt_df = gantt_df.sort_values(
        by=["Type", "Department", "Task"], ascending=[True, True, True]
    )

    # Format tooltip content
    gantt_df["Tooltip"] = gantt_df.apply(
        lambda row: (
            f"<b>{row['Task']}</b> ({row['Type']})<br>"
            f"Project: {row['Project']}<br>"
            f"Allocation: {row['Allocation']}%<br>"
            f"Period: {row['Start'].strftime('%Y-%m-%d')} to {row['Finish'].strftime('%Y-%m-%d')}"
        ),
        axis=1,
    )

    return gantt_df


def _add_today_marker(fig: go.Figure) -> go.Figure:
    """
    Add a vertical line marker for today's date on a Gantt chart.

    Args:
        fig: Plotly figure object (Gantt chart)

    Returns:
        Updated figure with today's marker
    """
    # Get today's date as a string to avoid timestamp arithmetic issues
    today = pd.Timestamp.now().strftime("%Y-%m-%d")

    # Add a shape (vertical line) for today's date
    fig.add_shape(
        type="line",
        x0=today,
        x1=today,
        y0=0,
        y1=1,
        yref="paper",
        line=dict(color="red", width=2, dash="dash"),
    )

    # Add text annotation for "Today"
    fig.add_annotation(
        x=today,
        y=1.0,
        yref="paper",
        text="Today",
        showarrow=False,
        font=dict(color="red"),
        bgcolor="white",
        bordercolor="red",
        borderwidth=1,
    )

    return fig


def _highlight_overallocated_resources(fig: go.Figure, df: pd.DataFrame) -> go.Figure:
    """
    Highlight resources that are overallocated on a Gantt chart.

    Args:
        fig: Plotly figure object (Gantt chart)
        df: DataFrame containing resource allocation data

    Returns:
        Updated figure with overallocated resources highlighted
    """
    if df.empty:
        return fig

    # Calculate daily allocation per resource
    resource_conflicts = find_resource_conflicts(df)

    if resource_conflicts.empty:
        return fig

    # Get utilization thresholds
    thresholds = load_utilization_thresholds()
    over_threshold = thresholds.get("over", 100)

    # Filter for overallocated resources (over the threshold)
    overallocated = resource_conflicts[
        resource_conflicts["Allocation"] > over_threshold
    ]

    if overallocated.empty:
        return fig

    # For each overallocated resource, add a highlight
    for _, row in overallocated.iterrows():
        # Convert date to string to avoid timestamp arithmetic issues
        date_str = row["Date"]
        if isinstance(date_str, pd.Timestamp):
            date_str = date_str.strftime("%Y-%m-%d")

        # Add a shape instead of using add_vline
        fig.add_shape(
            type="line",
            x0=date_str,
            x1=date_str,
            y0=0,
            y1=1,
            yref="paper",
            line=dict(color="rgba(255, 0, 0, 0.3)", width=10),
            layer="below",
        )

        # Add annotation for the overallocation
        fig.add_annotation(
            x=date_str,
            y=1.0,
            yref="paper",
            text=f"Overallocated: {row['Resource']}",
            showarrow=False,
            font=dict(color="red", size=10),
            bgcolor="rgba(255, 255, 255, 0.8)",
            bordercolor="red",
            borderwidth=1,
        )

    return fig


def display_resource_matrix_view(
    df: pd.DataFrame,
    start_date: Optional[pd.Timestamp] = None,
    end_date: Optional[pd.Timestamp] = None,
) -> None:
    """
    Display a matrix view of resource allocations across projects and time.

    Args:
        df: DataFrame containing resource allocation data
        start_date: Start date for the analysis period (optional)
        end_date: End date for the analysis period (optional)
    """
    if df.empty:
        st.warning("No data available for the selected filters.")
        return

    # Get display preferences
    display_prefs = load_display_preferences()
    chart_height = display_prefs.get("chart_height", 600)

    # Prepare data for Gantt chart
    gantt_data = _prepare_gantt_data(df)

    if gantt_data.empty:
        st.warning("No resource allocation data available for the selected period.")
        return

    # Create Gantt chart
    fig = px.timeline(
        gantt_data,
        x_start="Start",
        x_end="Finish",
        y="Task",
        color="Project",
        hover_name="Task",
        hover_data={"Task": False, "Start": False, "Finish": False, "Tooltip": True},
        labels={"Task": "Resource", "Start": "Start Date", "Finish": "End Date"},
        title="Resource Allocation Matrix",
        height=max(500, min(len(gantt_data["Task"].unique()) * 30, chart_height * 1.5)),
    )

    # Update layout
    fig.update_layout(
        xaxis_title="Timeline",
        yaxis_title="Resource",
        xaxis=dict(
            type="date",
            tickformat="%b %d\n%Y",
            tickmode="auto",
            nticks=20,
        ),
        yaxis=dict(
            autorange="reversed",  # Reverse y-axis to match project plan view
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
        margin=dict(
            l=200, r=50, t=50, b=50
        ),  # Increase left margin for long resource names
    )

    # Add today marker
    fig = _add_today_marker(fig)

    # Highlight overallocated resources
    fig = _highlight_overallocated_resources(fig, df)

    # Show the chart
    st.plotly_chart(fig, use_container_width=True)


def display_utilization_dashboard(
    df: pd.DataFrame,
    start_date: Optional[pd.Timestamp] = None,
    end_date: Optional[pd.Timestamp] = None,
) -> None:
    """
    Display a dashboard for resource utilization metrics.

    Args:
        df: DataFrame containing resource allocation data
        start_date: Start date for the analysis period (optional)
        end_date: End date for the analysis period (optional)
    """
    # Calculate utilization
    utilization_df = calculate_resource_utilization(df)

    if utilization_df.empty:
        st.warning("No utilization data available for the selected period.")
        return

    # Get preferences and thresholds
    display_prefs = load_display_preferences()
    chart_height = display_prefs.get("chart_height", 600)
    thresholds = load_utilization_thresholds()
    under_threshold = thresholds.get("under", 50)
    over_threshold = thresholds.get("over", 100)

    # Add utilization category based on thresholds
    utilization_df["Category"] = pd.cut(
        utilization_df["Utilization %"],
        bins=[0, under_threshold, over_threshold, float("inf")],
        labels=["Underutilized", "Optimal", "Overutilized"],
    )

    # Dashboard layout with metrics and charts
    col1, col2, col3 = st.columns(3)

    with col1:
        avg_utilization = utilization_df["Utilization %"].mean()
        st.metric(
            "Average Utilization",
            f"{avg_utilization:.1f}%",
            delta=f"{avg_utilization - 75:.1f}%" if 75 != avg_utilization else None,
            delta_color="normal",
        )

    with col2:
        over_utilized = len(
            utilization_df[utilization_df["Category"] == "Overutilized"]
        )
        st.metric(
            "Overutilized Resources",
            f"{over_utilized}",
            delta=None,
            delta_color="inverse",
        )

    with col3:
        under_utilized = len(
            utilization_df[utilization_df["Category"] == "Underutilized"]
        )
        st.metric(
            "Underutilized Resources",
            f"{under_utilized}",
            delta=None,
            delta_color="inverse",
        )

    # Create utilization distribution chart
    st.subheader("Utilization Distribution")

    # Histogram of utilization percentages
    fig = px.histogram(
        utilization_df,
        x="Utilization %",
        color="Category",
        barmode="overlay",
        nbins=20,
        title="Resource Utilization Distribution",
        color_discrete_map={
            "Underutilized": "teal",
            "Optimal": "green",
            "Overutilized": "crimson",
        },
        height=chart_height // 2,
    )

    # Add threshold lines
    fig.add_vline(
        x=under_threshold,
        line_dash="dash",
        line_color="blue",
        annotation_text=f"{under_threshold}%",
    )
    fig.add_vline(
        x=over_threshold,
        line_dash="dash",
        line_color="red",
        annotation_text=f"{over_threshold}%",
    )

    st.plotly_chart(fig, use_container_width=True)

    # Resource utilization by type
    st.subheader("Resource Utilization by Type")

    # Horizontal bar chart of resources sorted by utilization
    fig = px.bar(
        utilization_df.sort_values("Utilization %", ascending=False),
        y="Resource",
        x="Utilization %",
        color="Category",
        orientation="h",
        title="Resource Utilization (Sorted)",
        color_discrete_map={
            "Underutilized": "teal",
            "Optimal": "green",
            "Overutilized": "crimson",
        },
        height=max(400, min(len(utilization_df) * 25, chart_height)),
    )

    # Add threshold lines
    fig.add_vline(x=under_threshold, line_dash="dash", line_color="blue")
    fig.add_vline(x=over_threshold, line_dash="dash", line_color="red")

    st.plotly_chart(fig, use_container_width=True)

    # Display a table of utilization data
    st.subheader("Utilization Details")

    table_data = utilization_df[
        ["Resource", "Type", "Department", "Utilization %", "Category"]
    ].sort_values("Utilization %", ascending=False)

    # Format the table data
    table_data["Utilization %"] = table_data["Utilization %"].map("{:.1f}%".format)

    st.dataframe(
        table_data,
        use_container_width=True,
        column_config={
            "Resource": "Resource",
            "Type": "Type",
            "Department": "Department",
            "Utilization %": "Utilization %",
            "Category": st.column_config.SelectboxColumn(
                "Status",
                help="Utilization status",
                width="medium",
                options=["Underutilized", "Optimal", "Overutilized"],
                required=True,
            ),
        },
    )


def display_capacity_planning_dashboard(
    df: pd.DataFrame, start_date: pd.Timestamp, end_date: pd.Timestamp
) -> None:
    """
    Display a dashboard for capacity planning and availability forecasting.

    Args:
        df: DataFrame containing resource allocation data
        start_date: Start date for the forecast period
        end_date: End date for the forecast period
    """
    if df.empty or start_date is None or end_date is None:
        st.warning("Please provide resource data and date range for capacity planning.")
        return

    # Calculate capacity data
    capacity_data = calculate_capacity_data(df, start_date, end_date)

    if capacity_data.empty:
        st.warning("No capacity data available for the selected period.")
        return

    # Get display preferences
    display_prefs = load_display_preferences()
    chart_height = display_prefs.get("chart_height", 600)

    # Dashboard layout with metrics and charts
    st.subheader("Resource Capacity Overview")

    # Calculate summary metrics
    total_resources = capacity_data["Resource"].nunique()
    avg_allocation = capacity_data["Allocation"].mean() * 100
    over_allocated_days = capacity_data[capacity_data["Overallocated"] > 0][
        "Date"
    ].nunique()
    total_days = capacity_data["Date"].nunique()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total Resources", f"{total_resources}", delta=None)

    with col2:
        st.metric("Avg. Allocation", f"{avg_allocation:.1f}%", delta=None)

    with col3:
        st.metric(
            "Overallocated Days",
            f"{over_allocated_days}/{total_days}",
            delta=None,
            delta_color="inverse",
        )

    # Capacity heatmap by resource and date
    st.subheader("Resource Allocation Heatmap")

    # Pivot capacity data for heatmap
    pivot_data = capacity_data.pivot_table(
        index="Resource", columns="Date", values="Allocation", aggfunc="sum"
    )

    # Get color scale for heatmap
    colorscale = load_heatmap_colorscale()

    # Create heatmap
    fig = px.imshow(
        pivot_data.values,
        x=pivot_data.columns,
        y=pivot_data.index,
        color_continuous_scale=colorscale,
        labels=dict(x="Date", y="Resource", color="Allocation"),
        title="Resource Allocation Heatmap",
        height=max(400, min(len(pivot_data) * 25, chart_height)),
        aspect="auto",
    )

    # Update layout for better readability
    fig.update_layout(
        xaxis_nticks=20,
        yaxis_nticks=min(40, len(pivot_data)),
    )

    # Add colorbar title
    fig.update_coloraxes(colorbar_title="Allocation %", colorbar_tickformat=".0%")

    st.plotly_chart(fig, use_container_width=True)

    # Resource availability forecast
    st.subheader("Resource Availability Forecast")

    # Calculate daily availability per resource type
    resource_types = capacity_data["Type"].unique()
    availability_by_type = {}

    for resource_type in resource_types:
        type_data = capacity_data[capacity_data["Type"] == resource_type]
        daily_avail = type_data.groupby("Date")["Available"].mean()
        availability_by_type[resource_type] = daily_avail

    # Create availability chart
    fig = go.Figure()

    for resource_type, avail_data in availability_by_type.items():
        fig.add_trace(
            go.Scatter(
                x=avail_data.index,
                y=avail_data.values * 100,  # Convert to percentage
                mode="lines",
                name=resource_type,
                line=dict(
                    width=2,
                    dash="solid" if resource_type == "Person" else "dash",
                ),
            )
        )

    # Update layout
    fig.update_layout(
        title="Average Resource Availability by Type",
        xaxis_title="Date",
        yaxis_title="Available Capacity (%)",
        height=chart_height // 2,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
    )

    # Add a reference line at 0%
    fig.add_hline(y=0, line_dash="dot", line_color="red")

    # Add today marker
    fig = _add_today_marker(fig)

    st.plotly_chart(fig, use_container_width=True)


def display_resource_calendar(
    df: pd.DataFrame, start_date: pd.Timestamp, end_date: pd.Timestamp
) -> None:
    """
    Display a calendar view of resource allocations.

    Args:
        df: DataFrame containing resource allocation data
        start_date: Start date for the calendar
        end_date: End date for the calendar
    """
    if df.empty or start_date is None or end_date is None:
        st.warning("Please provide resource data and date range for the calendar view.")
        return

    # Calculate daily allocation per resource
    capacity_data = calculate_capacity_data(df, start_date, end_date)

    if capacity_data.empty:
        st.warning("No capacity data available for the selected period.")
        return

    # Get display preferences and department colors
    display_prefs = load_display_preferences()
    chart_height = display_prefs.get("chart_height", 600)
    dept_colors = load_department_colors()

    # Filter for selected resources if any
    if "selected_resources" in st.session_state and st.session_state.selected_resources:
        selected_resources = st.session_state.selected_resources
        capacity_data = capacity_data[
            capacity_data["Resource"].isin(selected_resources)
        ]

    # Resource selection
    st.subheader("Select Resources to View")
    resources = sorted(capacity_data["Resource"].unique())

    # Initialize selected resources if not already done
    if "selected_resources" not in st.session_state:
        # Default to showing first 5 resources
        st.session_state.selected_resources = resources[: min(5, len(resources))]

    # Allow multiple resource selection
    selected_resources = st.multiselect(
        "Select Resources",
        options=resources,
        default=st.session_state.selected_resources,
        key="calendar_resource_select",
    )

    # Update session state
    st.session_state.selected_resources = selected_resources

    if not selected_resources:
        st.warning("Please select at least one resource to view in the calendar.")
        return

    # Filter data for selected resources
    filtered_data = capacity_data[capacity_data["Resource"].isin(selected_resources)]

    # Create a calendar view for each selected resource
    for resource in selected_resources:
        resource_data = filtered_data[filtered_data["Resource"] == resource]

        # Get resource type and department
        resource_type = resource_data["Type"].iloc[0]
        department = resource_data["Department"].iloc[0]

        # Get department color
        dept_color = dept_colors.get(department, "#1f77b4")

        # Create a calendar heatmap
        st.subheader(f"{resource} ({resource_type}, {department})")

        # Pivot data for heatmap - group by week and day of week
        resource_data["Week"] = resource_data["Date"].dt.isocalendar().week
        resource_data["Day"] = resource_data["Date"].dt.day_name()

        # Order days
        day_order = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]

        pivot_data = resource_data.pivot_table(
            index="Week", columns="Day", values="Allocation", aggfunc="mean"
        )

        # Reorder columns by day of week
        pivot_data = pivot_data.reindex(columns=day_order)

        # Get color scale
        colorscale = load_heatmap_colorscale()

        # Create heatmap
        fig = px.imshow(
            pivot_data.values,
            x=pivot_data.columns,
            y=pivot_data.index,
            color_continuous_scale=colorscale,
            labels=dict(x="Day", y="Week", color="Allocation"),
            title=f"Calendar View: {resource}",
            height=chart_height // 2,
        )

        # Add text annotations with allocation percentages
        for i in range(len(pivot_data.index)):
            for j in range(len(pivot_data.columns)):
                if not pd.isna(pivot_data.values[i, j]):
                    fig.add_annotation(
                        x=j,
                        y=i,
                        text=f"{pivot_data.values[i, j] * 100:.0f}%",
                        showarrow=False,
                        font=dict(
                            color="black" if pivot_data.values[i, j] < 0.7 else "white",
                            size=10,
                        ),
                    )

        # Update layout
        fig.update_layout(
            xaxis_title="Day of Week",
            yaxis_title="Week Number",
        )

        # Add colorbar title
        fig.update_coloraxes(colorbar_title="Allocation %", colorbar_tickformat=".0%")

        st.plotly_chart(fig, use_container_width=True)


def display_sunburst_organization(data: Dict[str, List[Dict[str, Any]]]) -> None:
    """
    Display a sunburst chart showing the organizational structure.

    Args:
        data: Dictionary containing people, teams, and departments
    """
    # Prepare data for sunburst chart
    sunburst_data = []

    # Add departments
    for dept in data["departments"]:
        sunburst_data.append(
            {"id": dept["name"], "parent": "", "value": 1, "type": "Department"}
        )

        # Add teams in departments
        for team_name in dept.get("teams", []):
            sunburst_data.append(
                {"id": team_name, "parent": dept["name"], "value": 1, "type": "Team"}
            )

    # Add people to teams or departments
    for person in data["people"]:
        if person.get("team"):
            parent = person["team"]
        else:
            parent = person.get("department", "")

        sunburst_data.append(
            {
                "id": person["name"],
                "parent": parent,
                "value": person.get("daily_cost", 300),  # Size by cost
                "type": "Person",
            }
        )

    # Create DataFrame from sunburst data
    sunburst_df = pd.DataFrame(sunburst_data)

    # Department colors
    dept_colors = load_department_colors()

    # Create sunburst chart
    fig = px.sunburst(
        sunburst_df,
        ids="id",
        parents="parent",
        values="value",
        color="type",
        color_discrete_map={
            "Department": "#636EFA",
            "Team": "#EF553B",
            "Person": "#00CC96",
        },
        title="Organizational Structure",
    )

    # Update layout
    fig.update_layout(
        margin=dict(t=0, l=0, r=0, b=0),
    )

    # Show the chart
    st.plotly_chart(fig, use_container_width=True)


def _display_resource_conflicts(filtered_data: pd.DataFrame) -> None:
    """
    Display a section showing resource allocation conflicts.

    Args:
        filtered_data: DataFrame containing resource allocation data
    """
    # Find resource conflicts
    conflicts = find_resource_conflicts(filtered_data)

    if conflicts.empty:
        st.success("No resource conflicts detected in the selected time period.")
        return

    # Display conflicts in an expander
    with st.expander("Resource Conflicts Detected", expanded=True):
        st.warning(
            f"Found {len(conflicts)} potential resource conflicts. "
            "These occur when a resource is allocated more than 100% on a given day."
        )

        # Group conflicts by resource
        resource_conflicts = conflicts.groupby("Resource").size().reset_index()
        resource_conflicts.columns = ["Resource", "Conflict Days"]
        resource_conflicts = resource_conflicts.sort_values(
            "Conflict Days", ascending=False
        )

        # Display conflict summary
        col1, col2 = st.columns([2, 3])

        with col1:
            st.subheader("Resources with Conflicts")
            st.dataframe(resource_conflicts, use_container_width=True)

        with col2:
            st.subheader("Conflict Calendar")

            # Create a calendar view of conflicts
            # Group by date and count conflicts
            date_conflicts = conflicts.groupby("Date").size().reset_index()
            date_conflicts.columns = ["Date", "Conflicts"]

            # Create bar chart by date
            fig = px.bar(
                date_conflicts,
                x="Date",
                y="Conflicts",
                title="Resource Conflicts by Date",
                color="Conflicts",
                color_continuous_scale="Reds",
            )

            # Update layout
            fig.update_layout(
                xaxis_title="Date",
                yaxis_title="Number of Conflicts",
            )

            # Add today marker
            fig = _add_today_marker(fig)

            st.plotly_chart(fig, use_container_width=True)

        # Display conflict details
        st.subheader("Conflict Details")

        # Convert date to string for display
        if "Date" in conflicts.columns:
            if pd.api.types.is_datetime64_any_dtype(conflicts["Date"]):
                conflicts["Date"] = conflicts["Date"].dt.strftime("%Y-%m-%d")

        # Round allocation percentage for display
        if "Allocation" in conflicts.columns:
            conflicts["Allocation"] = conflicts["Allocation"].round(1)

        # Sort by date and allocation
        conflicts = conflicts.sort_values(
            ["Date", "Allocation"], ascending=[True, False]
        )

        # Show the conflict details
        st.dataframe(
            conflicts[
                ["Resource", "Type", "Department", "Date", "Allocation", "Projects"]
            ],
            use_container_width=True,
        )
