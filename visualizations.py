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
from color_management import load_utilization_colorscale, manage_visualization_colors
from data_handlers import (
    calculate_project_cost,
    calculate_resource_utilization,
    filter_dataframe,
    find_resource_conflicts,  # Added missing import
)
from utils import paginate_dataframe


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
        if overallocation > 0:
            fig.add_shape(
                type="rect",
                x0=df["Start"].min(),
                x1=df["Finish"].max(),
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
    if gantt_data.empty:
        st.warning("No data available for utilization metrics.")
        return

    # Calculate utilization metrics
    utilization_df = calculate_resource_utilization(gantt_data, start_date, end_date)

    if utilization_df.empty:
        st.warning("No utilization data available for the selected period.")
        return

    # Ensure "Cost (€)" is numeric for calculations
    utilization_df["Cost (€)"] = (
        utilization_df["Cost (€)"].replace(",", "", regex=True).astype(float)
    )

    # Load utilization colorscale dynamically
    utilization_colorscale = load_utilization_colorscale()
    if not utilization_colorscale:
        st.warning("Utilization colorscale is not defined. Using default colorscale.")
        utilization_colorscale = px.colors.sequential.Viridis  # Default colorscale

    # Display summary metrics
    st.subheader("Resource Utilization Summary")

    avg_utilization = utilization_df["Utilization %"].mean()
    avg_overallocation = utilization_df["Overallocation %"].mean()
    total_resources = len(utilization_df)
    overallocated_resources = (utilization_df["Overallocation %"] > 0).sum()
    total_cost = utilization_df["Cost (€)"].sum()  # Ensure numeric sum

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Average Utilization", f"{avg_utilization:.1f}%")
    col2.metric(
        "Overallocated Resources", f"{overallocated_resources}/{total_resources}"
    )
    col3.metric("Average Overallocation", f"{avg_overallocation:.1f}%")
    col4.metric("Total Resources", total_resources)
    col5.metric("Total Cost (€)", f"{total_cost:,.2f}")  # Format with commas

    # Add utilization charts
    st.subheader("Resource Utilization Breakdown")

    # Sort utilization data for better visualization
    utilization_df = utilization_df.sort_values(by="Utilization %", ascending=False)

    # Display utilization by resource type
    col1, col2 = st.columns(2)

    with col1:
        # Utilization by Resource Type
        type_util = utilization_df.groupby("Type")["Utilization %"].mean().reset_index()
        fig = px.bar(
            type_util,
            x="Type",
            y="Utilization %",
            color="Type",
            title="Average Utilization by Resource Type",
            labels={"Utilization %": "Utilization Percentage (%)"},
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Utilization by Department
        dept_util = (
            utilization_df.groupby("Department")["Utilization %"].mean().reset_index()
        )
        fig = px.bar(
            dept_util,
            x="Department",
            y="Utilization %",
            color="Department",
            title="Average Utilization by Department",
            labels={"Utilization %": "Utilization Percentage (%)"},
        )
        st.plotly_chart(fig, use_container_width=True)

    # Display resource utilization heatmap
    st.subheader("Resource Utilization Heatmap")

    # Prepare data for heatmap - top 20 resources by utilization
    top_resources = utilization_df.head(20)

    # Create heatmap data
    heatmap_data = pd.DataFrame(
        {
            "Resource": top_resources["Resource"],
            "Utilization": top_resources["Utilization %"],
            "Overallocation": top_resources["Overallocation %"],
        }
    )

    # Create a wide-format dataframe for the heatmap
    heatmap_wide = pd.DataFrame()
    heatmap_wide["Resource"] = heatmap_data["Resource"]
    heatmap_wide["Utilization %"] = heatmap_data["Utilization"]
    heatmap_wide["Overallocation %"] = heatmap_data["Overallocation"]

    # Create heatmap
    fig = go.Figure()

    fig.add_trace(
        go.Heatmap(
            z=heatmap_wide[["Utilization %", "Overallocation %"]].values.T,
            x=heatmap_wide["Resource"],
            y=["Utilization %", "Overallocation %"],
            colorscale=utilization_colorscale,  # Use dynamically loaded or default colorscale
            showscale=True,
            hoverongaps=False,
            text=[
                [f"Utilization: {val:.1f}%" for val in heatmap_wide["Utilization %"]],
                [
                    f"Overallocation: {val:.1f}%"
                    for val in heatmap_wide["Overallocation %"]
                ],
            ],
            hoverinfo="text+x+y",
        )
    )

    fig.update_layout(
        title="Resource Utilization and Overallocation Heatmap",
        xaxis_title="Resource",
        yaxis_title="Metric",
        height=400,
    )

    st.plotly_chart(fig, use_container_width=True)

    # Display detailed utilization table
    st.subheader("Detailed Resource Utilization")

    # Format the utilization dataframe for display
    display_df = utilization_df.copy()
    display_df["Utilization %"] = display_df["Utilization %"].round(1).astype(str) + "%"
    display_df["Overallocation %"] = (
        display_df["Overallocation %"].round(1).astype(str) + "%"
    )
    display_df["Cost (€)"] = display_df["Cost (€)"].apply(
        lambda x: f"{x:,.2f}"  # Format with commas
    )

    # Apply search and filtering
    filtered_df = filter_dataframe(
        display_df,
        key="Utilization",  # Corrected name
        columns=[
            "Resource",
            "Type",
            "Department",
            "Projects",
            "Utilization %",
            "Overallocation %",
            "Cost (€)",  # Include cost in the table
        ],
    )

    # Pagination
    filtered_df = paginate_dataframe(
        filtered_df,
        "Utilization",  # Corrected name
    )

    st.dataframe(filtered_df, use_container_width=True)


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
    conflicts = find_resource_conflicts(gantt_data)  # Now correctly defined
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

        st.subheader("Conflict Details")
        filtered_conflicts = filter_dataframe(
            conflicts_df[["resource", "project1", "project2", "overlap_days"]],
            key="Conflicts",
        )
        st.dataframe(filtered_conflicts, use_container_width=True)
    else:
        st.success("No resource conflicts detected")
