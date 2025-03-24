"""
Visualizations Module

This module contains functions for creating visualizations using Plotly
and Streamlit, including Gantt charts and resource utilization dashboards.
"""

# Standard library imports
from datetime import datetime
from typing import Dict, List, Optional

# Third-party imports
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Local module imports
from color_management import manage_visualization_colors, load_currency_settings
from data_handlers import (
    calculate_project_cost,
    calculate_resource_utilization,
    calculate_capacity_data,
    find_resource_conflicts,
)


def display_gantt_chart(df: pd.DataFrame) -> None:
    """
    Displays an interactive Gantt chart using Plotly.
    """
    if df.empty:
        st.warning("No data available to visualize.")
        return

    df_with_utilization = _prepare_gantt_data(df)

    department_colors = {
        dept: color.lower()
        for dept, color in manage_visualization_colors(
            df_with_utilization["Department"].unique()
        ).items()
    }

    fig = px.timeline(
        df_with_utilization,
        x_start="Start",
        x_end="Finish",
        y="Resource",
        color="Department",
        hover_data=[
            "Type",
            "Department",
            "Priority",
            "Duration (days)",
            "Utilization %",
            "Overallocation %",
            "Cost (€)",
        ],
        labels={"Resource": "Resource Name"},
        height=600,
        color_discrete_map=department_colors,
    )

    fig = _add_today_marker(fig)
    fig = _highlight_overallocated_resources(fig, df_with_utilization)

    st.plotly_chart(fig, use_container_width=True)
    _display_chart_legend()


def _prepare_gantt_data(df: pd.DataFrame) -> pd.DataFrame:
    """Prepare data for Gantt chart by adding utilization and cost information."""
    # Calculate utilization for coloring
    utilization_df = calculate_resource_utilization(df)

    # Check if 'Overallocation %' column exists, if not, create it with default values
    if "Overallocation %" not in utilization_df.columns:
        utilization_df["Overallocation %"] = 0

    # Create utilization mappings
    utilization_map = utilization_df.set_index("Resource")["Utilization %"].to_dict()
    overallocation_map = utilization_df.set_index("Resource")[
        "Overallocation %"
    ].to_dict()

    # Add utilization data to the dataframe
    df = df.copy()
    df["Utilization %"] = df["Resource"].map(utilization_map)
    df["Overallocation %"] = df["Resource"].map(overallocation_map)
    df["Duration (days)"] = (df["Finish"] - df["Start"]).dt.days + 1

    # Ensure the Cost (€) column is calculated
    if "Cost (€)" not in df.columns:
        df["Cost (€)"] = df.apply(
            lambda row: calculate_project_cost(
                {
                    "start_date": row["Start"].strftime(
                        "%Y-%m-%d"
                    ),  # Convert to string
                    "end_date": row["Finish"].strftime("%Y-%m-%d"),  # Convert to string
                    "assigned_resources": [row["Resource"]],
                },
                st.session_state.data["people"],
                st.session_state.data["teams"],
            ),
            axis=1,
        )

    return df


def _add_today_marker(fig: go.Figure) -> go.Figure:
    """Add a vertical line for today's date to the Gantt chart."""
    today = pd.Timestamp.now()
    fig.add_vline(x=today, line_width=2, line_dash="dash", line_color="gray")
    return fig


def _highlight_overallocated_resources(fig: go.Figure, df: pd.DataFrame) -> go.Figure:
    """Highlight overallocated resources in the Gantt chart."""
    overallocation_map = df.set_index("Resource")["Overallocation %"].to_dict()

    for i, resource in enumerate(df["Resource"].unique()):
        overallocation = overallocation_map.get(resource, 0)
        if overallocation > 0:  # Highlight only if Overallocation % > 0
            fig.add_shape(
                type="rect",
                x0=df[df["Resource"] == resource]["Start"].min(),
                x1=df[df["Resource"] == resource]["Finish"].max(),
                y0=i - 0.4,
                y1=i + 0.4,
                line=dict(color="rgba(255,0,0,0.1)", width=0),
                fillcolor="rgba(255,0,0,0.1)",
                layer="below",
            )

    return fig


def _display_chart_legend() -> None:
    """Display the legend for the Gantt chart."""
    with st.expander("Chart Legend"):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Visual Indicators:**")
            st.markdown(
                "- Red background: Resources with overlapping project assignments"
            )
            st.markdown("- Dashed vertical line: Today's date")
        with col2:
            st.markdown("**Interactive Features:**")
            st.markdown("- Zoom: Use the range selector or slider at the bottom")
            st.markdown(
                "- Details: Hover over bars to see project and resource details"
            )
            st.markdown("- Pan: Click and drag on the timeline")


def display_utilization_dashboard(
    gantt_data: pd.DataFrame,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> None:
    """
    Displays a dashboard with resource utilization metrics.
    """
    # Add a tab for capacity-based utilization
    utilization_tabs = st.tabs(
        ["Project-Based Utilization", "Capacity-Based Utilization"]
    )

    with utilization_tabs[0]:
        # Existing utilization code
        if gantt_data.empty:
            st.warning("No data available for utilization metrics.")
            return

        # Calculate utilization metrics
        utilization_df = calculate_resource_utilization(
            gantt_data, start_date, end_date
        )

        if utilization_df.empty:
            st.warning("No utilization data available for the selected period.")
            return

        # Display summary metrics
        st.subheader("Project-Based Utilization Summary")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Resources", len(utilization_df))
        col2.metric(
            "Average Utilization (%)", f"{utilization_df['Utilization %'].mean():.1f}"
        )
        col3.metric(
            "Average Overallocation (%)",
            f"{utilization_df['Overallocation %'].mean():.1f}",
        )

        # Display utilization chart
        st.subheader("Utilization by Resource")
        currency, _ = load_currency_settings()
        fig = px.bar(
            utilization_df,
            x="Resource",
            y="Utilization %",
            color="Type",
            hover_data={
                "Department": True,
                "Days Utilized": True,
                f"Cost ({currency})": ":,.2f",  # Dynamically set column name
            },
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
            hover_data=["Department", "Days Utilized", f"Cost ({currency})"],
            title="Resource Overallocation",
        )
        st.plotly_chart(overallocation_fig, use_container_width=True)

        # Display detailed utilization table
        st.subheader("Detailed Utilization Data")
        st.dataframe(utilization_df, use_container_width=True)

    with utilization_tabs[1]:
        # Use the new capacity planning dashboard
        display_capacity_planning_dashboard(start_date, end_date)


def display_budget_vs_actual_cost(projects: List[Dict]) -> None:
    """
    Displays a budget vs. actual cost visualization for all projects.
    """
    st.subheader("Budget vs. Actual Cost")

    # Prepare data for visualization
    data = []
    for project in projects:
        actual_cost = calculate_project_cost(
            project, st.session_state.data["people"], st.session_state.data["teams"]
        )
        data.append(
            {
                "Project": project["name"],
                "Allocated Budget (€)": project["allocated_budget"],
                "Actual Cost (€)": actual_cost,
            }
        )

    df = pd.DataFrame(data)

    # Create bar chart for budget vs. actual cost
    fig = px.bar(
        df,
        x="Project",
        y=["Allocated Budget (€)", "Actual Cost (€)"],
        barmode="group",
        title="Budget vs. Actual Cost by Project",
        labels={"value": "Cost (€)", "variable": "Cost Type"},
    )

    st.plotly_chart(fig, use_container_width=True)

    # Highlight projects with cost overruns
    overruns = df[df["Actual Cost (€)"] > df["Allocated Budget (€)"]]
    if not overruns.empty:
        overruns["Allocated Budget (€)"] = overruns["Allocated Budget (€)"].apply(
            lambda x: f"{x:,.2f}"  # Format with commas
        )
        overruns["Actual Cost (€)"] = overruns["Actual Cost (€)"].apply(
            lambda x: f"{x:,.2f}"  # Format with commas
        )
        st.warning("The following projects have cost overruns:")
        st.dataframe(overruns, use_container_width=True)


def _display_resource_conflicts(gantt_data):
    """Check and display resource conflicts."""
    conflicts = find_resource_conflicts(gantt_data)
    if conflicts:
        st.subheader("Resource Conflicts")

        conflict_summary = {}
        for conflict in conflicts:
            resource = conflict["resource"]
            if resource not in conflict_summary:
                conflict_summary[resource] = 0
            conflict_summary[resource] += 1

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Conflicts", len(conflicts))
        with col2:
            st.metric("Affected Resources", len(conflict_summary))

        conflicts_df = pd.DataFrame(conflicts)
        conflicts_df["overlap_start"] = pd.to_datetime(conflicts_df["overlap_start"])
        conflicts_df["overlap_end"] = pd.to_datetime(conflicts_df["overlap_end"])

        fig = px.timeline(
            conflicts_df,
            x_start="overlap_start",
            x_end="overlap_end",
            y="resource",
            color="overlap_days",
            hover_data=["project1", "project2", "overlap_days"],
            color_continuous_scale="Reds",
            title="Resource Conflict Timeline",
        )
        st.plotly_chart(fig, use_container_width=True)
        _display_resource_conflicts_chart_legend()

        st.subheader("Conflict Details")

        # Add search and filter inputs
        with st.expander("Search and Filter Conflicts", expanded=False):
            search_term = st.text_input("Search Conflicts", key="search_conflicts")
            resource_filter = st.multiselect(
                "Filter Resource",
                options=conflicts_df["resource"].unique(),
                key="filter_resource",
            )
            project1_filter = st.multiselect(
                "Filter Project 1",
                options=conflicts_df["project1"].unique(),
                key="filter_project1",
            )
            project2_filter = st.multiselect(
                "Filter Project 2",
                options=conflicts_df["project2"].unique(),
                key="filter_project2",
            )

        # Apply search and filters
        filtered_conflicts = conflicts_df.rename(
            columns={
                "resource": "Resource",
                "project1": "Project 1",
                "project2": "Project 2",
                "overlap_start": "Overlap Start",
                "overlap_end": "Overlap End",
                "overlap_days": "Overlapping Days",
            }
        )

        if search_term:
            mask = filtered_conflicts.apply(
                lambda row: search_term.lower()
                in row.astype(str).str.lower().to_string(),
                axis=1,
            )
            filtered_conflicts = filtered_conflicts[mask]

        if resource_filter:
            filtered_conflicts = filtered_conflicts[
                filtered_conflicts["Resource"].isin(resource_filter)
            ]
        if project1_filter:
            filtered_conflicts = filtered_conflicts[
                filtered_conflicts["Project 1"].isin(project1_filter)
            ]
        if project2_filter:
            filtered_conflicts = filtered_conflicts[
                filtered_conflicts["Project 2"].isin(project2_filter)
            ]

        st.dataframe(filtered_conflicts, use_container_width=True)
    else:
        st.success("No resource conflicts detected")


def _display_resource_conflicts_chart_legend():
    with st.expander("Chart Legend", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Visual Indicators:**")
            st.markdown("- **Red Bars**: Duration of overlapping assignments.")
            st.markdown("- **Hover Details**: Shows overlapping projects and days.")
        with col2:
            st.markdown("**Interactive Features:**")
            st.markdown("- **Zoom**: Use the range selector or slider at the bottom.")
            st.markdown("- **Details**: Hover over bars to see conflict details.")
            st.markdown("- **Pan**: Click and drag on the timeline.")


def display_capacity_planning_dashboard(start_date=None, end_date=None):
    """Display capacity planning dashboard with visualizations."""
    st.subheader("Availability Forecast")

    # Date range selector
    col1, col2 = st.columns(2)
    with col1:
        if start_date is None:
            start_date = st.date_input("Start Date", value=pd.to_datetime("today"))
        else:
            start_date = st.date_input("Start Date", value=start_date)

    with col2:
        if end_date is None:
            end_date = st.date_input(
                "End Date", value=pd.to_datetime("today") + pd.Timedelta(days=90)
            )
        else:
            end_date = st.date_input("End Date", value=end_date)

    # Calculate capacity data
    capacity_data = calculate_capacity_data(start_date, end_date)

    if capacity_data.empty:
        st.warning("No capacity data available for the selected period.")
        return

    # Display capacity overview
    st.subheader("Capacity Overview")
    col1, col2, col3 = st.columns(3)

    with col1:
        total_capacity = capacity_data["Capacity (hours)"].sum()
        st.metric("Total Capacity (hours)", f"{total_capacity:,.1f}")

    with col2:
        total_allocated = capacity_data["Allocated (hours)"].sum()
        st.metric("Total Allocated (hours)", f"{total_allocated:,.1f}")

    with col3:
        overall_utilization = (
            (total_allocated / total_capacity * 100) if total_capacity > 0 else 0
        )
        st.metric("Overall Utilization", f"{overall_utilization:.1f}%")

    # Capacity vs Allocation chart
    st.subheader("Capacity vs Allocation by Resource")

    # Sort by utilization for better visualization
    capacity_data = capacity_data.sort_values(by="Utilization %", ascending=False)

    fig = px.bar(
        capacity_data,
        x="Resource",
        y=["Capacity (hours)", "Allocated (hours)"],
        barmode="overlay",
        title="Resource Capacity vs Allocation",
        color_discrete_map={
            "Capacity (hours)": "cyan",
            "Allocated (hours)": "orange",
        },
        labels={"value": "Hours", "variable": "Metric"},
    )

    st.plotly_chart(fig, use_container_width=True)

    # Resource availability heatmap
    st.subheader("Resource Availability")

    # Display detailed capacity table
    st.subheader("Detailed Capacity Data")
    st.dataframe(
        capacity_data,
        column_config={
            "Resource": st.column_config.TextColumn("Resource"),
            "Type": st.column_config.TextColumn("Type"),
            "Department": st.column_config.TextColumn("Department"),
            "Capacity (hours)": st.column_config.NumberColumn(
                "Capacity (Hours)", format="%.1f"
            ),
            "Allocated (hours)": st.column_config.NumberColumn(
                "Allocated (Hours)", format="%.1f"
            ),
            "Utilization %": st.column_config.ProgressColumn(
                "Utilization (%)", format="%.1f%%", min_value=0, max_value=100
            ),
            "Available (hours)": st.column_config.NumberColumn(
                "Available (Hours)", format="%.1f"
            ),
        },
        use_container_width=True,
    )


def identify_overallocated_resources(capacity_data, threshold=100):
    """Identify resources that are overallocated based on a utilization threshold."""
    overallocated = capacity_data[capacity_data["Utilization %"] > threshold]
    return overallocated


def display_overallocation_warnings(capacity_data):
    """Display warnings for overallocated resources."""
    overallocated = identify_overallocated_resources(capacity_data)

    if not overallocated.empty:
        st.warning(f"⚠️ {len(overallocated)} resources are overallocated:")

        for _, row in overallocated.iterrows():
            st.markdown(
                f"**{row['Resource']}** ({row['Type']}) - "
                f"Utilization: {row['Utilization %']:.1f}% - "
                f"Allocated: {row['Allocated (hours)']:.1f} hours / "
                f"Capacity: {row['Capacity (hours)']:.1f} hours"
            )
