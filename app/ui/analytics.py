"""
Analytics UI module.

This module provides the UI components for analytics and data visualization.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import calendar
from typing import List, Dict, Any, Optional, Tuple

from app.services.config_service import (
    load_currency_settings,
    load_department_colors,
    load_utilization_thresholds,
    load_heatmap_colorscale,
    load_date_range_settings,
    load_display_preferences,
)

from app.ui.visualizations import (
    display_gantt_chart,
    display_utilization_chart,
)
from app.services.visualization_service import (
    prepare_gantt_data,
    prepare_utilization_data,
    prepare_capacity_data,
    prepare_budget_data,
)
from app.utils.ui_components import display_action_bar
from app.services.data_service import (
    sort_projects_by_priority_and_date,
    create_gantt_data,
    apply_filters,
    calculate_resource_utilization,
    calculate_capacity_data,
    find_resource_conflicts,
)


def create_resource_analytics_filters(page_key: str) -> Dict[str, Any]:
    """
    Create standardized filters for resource analytics pages.

    Args:
        page_key: Unique key for the page to avoid session state conflicts

    Returns:
        Dictionary of filter settings
    """
    with st.expander("Search and Filter", expanded=False):
        # First row: Search and Date Range
        col1, col3 = st.columns([1, 1])

        with col1:
            search_term = st.text_input(
                "Search Resources/Projects", key=f"search_{page_key}"
            )

        with col3:
            # Load date range settings
            date_ranges = load_date_range_settings()
            short_range = date_ranges.get("short", 30)
            medium_range = date_ranges.get("medium", 90)
            long_range = date_ranges.get("long", 180)

            # Date range selection with predefined options from settings
            date_options = {
                f"Next {short_range} days": (
                    pd.to_datetime("today"),
                    pd.to_datetime("today") + pd.Timedelta(days=short_range),
                ),
                f"Next {medium_range} days": (
                    pd.to_datetime("today"),
                    pd.to_datetime("today") + pd.Timedelta(days=medium_range),
                ),
                f"Next {long_range} days": (
                    pd.to_datetime("today"),
                    pd.to_datetime("today") + pd.Timedelta(days=long_range),
                ),
                "All time": (None, None),
                "Custom range": (None, None),
            }

            date_selection = st.selectbox(
                "Date Range",
                options=list(date_options.keys()),
                index=1,  # Default to medium range
                key=f"date_range_{page_key}",
            )

            start_date, end_date = date_options[date_selection]

            # Show custom date inputs if custom range selected
            if date_selection == "Custom range":
                date_col1, date_col2 = st.columns(2)
                with date_col1:
                    start_date = pd.to_datetime(
                        st.date_input(
                            "From",
                            value=pd.to_datetime("today"),
                            key=f"start_date_{page_key}",
                        )
                    )
                with date_col2:
                    end_date = pd.to_datetime(
                        st.date_input(
                            "To",
                            value=pd.to_datetime("today") + pd.Timedelta(days=90),
                            key=f"end_date_{page_key}",
                        )
                    )
            elif date_selection == "All time":
                # Get min/max dates from projects
                if st.session_state.data["projects"]:
                    start_date = min(
                        [
                            pd.to_datetime(p["start_date"])
                            for p in st.session_state.data["projects"]
                        ]
                    )
                    end_date = max(
                        [
                            pd.to_datetime(p["end_date"])
                            for p in st.session_state.data["projects"]
                        ]
                    )
                else:
                    # If no projects, use default range
                    start_date = pd.to_datetime("today")
                    end_date = pd.to_datetime("today") + pd.Timedelta(days=medium_range)

        # Second row: Resource filters
        col4, col5, col6 = st.columns(3)

        with col4:
            resource_types = st.multiselect(
                "Resource Types",
                options=["Person", "Team", "Department"],
                default=[],  # Changed from ["Person", "Team", "Department"] to empty list
                key=f"resource_types_{page_key}",
            )

        with col5:
            dept_filter = st.multiselect(
                "Filter by Department",
                options=[d["name"] for d in st.session_state.data["departments"]],
                default=[],
                key=f"dept_filter_{page_key}",
            )

        with col6:
            project_filter = st.multiselect(
                "Filter by Project",
                options=[p["name"] for p in st.session_state.data["projects"]],
                default=[],
                key=f"project_filter_{page_key}",
            )

        # Third row: Additional metrics filters
        utilization_threshold = st.slider(
            "Minimum Utilization %",
            min_value=0,
            max_value=100,
            value=0,
            step=5,
            key=f"utilization_{page_key}",
        )

        # Assemble filters into a dictionary
        filters = {
            "search_term": search_term,
            "date_range": [start_date, end_date],
            "resource_types": resource_types,
            "dept_filter": dept_filter,
            "project_filter": project_filter,
            "utilization_threshold": utilization_threshold,
        }

        return filters


def display_visualize_data_tab():
    """Display the workload distribution visualization tab."""
    display_action_bar()
    st.subheader("Workload Distribution")

    if not st.session_state.data["projects"]:
        st.warning("No projects found. Please add projects first.")
        return

    if not (
        st.session_state.data["people"]
        or st.session_state.data["teams"]
        or st.session_state.data["departments"]
    ):
        st.warning(
            "No resources found. Please add people, teams, or departments first."
        )
        return

    # Get filters using the standardized filter component
    filters = create_resource_analytics_filters("workload")

    # Sort projects by priority and end date
    sorted_projects = sort_projects_by_priority_and_date(
        st.session_state.data["projects"]
    )
    gantt_data = create_gantt_data(sorted_projects, st.session_state.data)

    # Ensure the DataFrame has the required columns
    if gantt_data.empty or "Resource" not in gantt_data.columns:
        st.error(
            "Failed to generate Gantt data. Please check your project and resource configurations."
        )
        return

    # Apply filters to data
    filtered_data = apply_filters(gantt_data, filters)

    # Extract date range from filters
    start_date = filters["date_range"][0] if len(filters["date_range"]) > 0 else None
    end_date = filters["date_range"][1] if len(filters["date_range"]) > 1 else None

    # Display workload summary metrics
    display_workload_summary_metrics(filtered_data)

    # Display workload distribution chart
    display_workload_distribution_chart(filtered_data)

    # Display project breakdown
    display_project_workload_breakdown(filtered_data)

    # Display the matrix view with filtered data
    display_resource_matrix_view(filtered_data, start_date, end_date)

    # Display resource conflicts section with severity indicators
    display_resource_conflicts_enhanced(filtered_data)


def display_workload_summary_metrics(filtered_data: pd.DataFrame) -> None:
    """
    Display summary metrics for workload distribution.

    Args:
        filtered_data: Filtered DataFrame of resource allocation data
    """
    if filtered_data.empty:
        return

    st.subheader("Workload Summary")

    # Calculate key metrics
    total_projects = filtered_data["Project"].nunique()
    total_resources = filtered_data["Resource"].nunique()
    avg_allocation = filtered_data["Allocation %"].mean()

    # Calculate overallocated resources
    resource_allocation = filtered_data.groupby("Resource")["Allocation %"].sum()
    overallocated_count = sum(resource_allocation > 100)

    # Calculate underutilized resources (less than 50% allocated)
    underutilized_count = sum((resource_allocation > 0) & (resource_allocation < 50))

    # Display metrics in columns
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Active Projects", total_projects)
    with col2:
        st.metric("Allocated Resources", total_resources)
    with col3:
        st.metric("Avg Allocation", f"{avg_allocation:.1f}%")
    with col4:
        st.metric("Overallocated", overallocated_count, delta_color="inverse")
    with col5:
        st.metric("Underutilized", underutilized_count, delta_color="inverse")


def display_workload_distribution_chart(filtered_data: pd.DataFrame) -> None:
    """
    Display workload distribution across resources.

    Args:
        filtered_data: Filtered DataFrame of resource allocation data
    """
    if filtered_data.empty:
        return

    # Get chart height from display preferences
    display_prefs = load_display_preferences()
    chart_height = display_prefs.get("chart_height", 600)

    st.subheader("Workload Distribution")

    # Calculate allocation by resource
    resource_allocation = (
        filtered_data.groupby(["Resource", "Type"])["Allocation %"].sum().reset_index()
    )
    resource_allocation = resource_allocation.sort_values(
        "Allocation %", ascending=False
    )

    # Load utilization thresholds for color coding
    utilization_thresholds = load_utilization_thresholds()
    optimal_min = utilization_thresholds.get("optimal_min", 70)
    optimal_max = utilization_thresholds.get("optimal_max", 90)

    # Create a chart showing allocation by resource with color bands
    fig = px.bar(
        resource_allocation,
        x="Resource",
        y="Allocation %",
        color="Type",
        title="Resource Allocation Distribution",
        labels={"Resource": "Resource", "Allocation %": "Allocation %"},
        height=chart_height,  # Use configurable chart height
    )

    # Add bands for optimal utilization
    fig.add_hrect(
        y0=optimal_min,
        y1=optimal_max,
        line_width=0,
        fillcolor="green",
        opacity=0.5,
        annotation_text="Optimal Zone",
        annotation_position="top right",
    )

    # Add a line for 100% allocation
    fig.add_hline(y=100, line_width=2, line_dash="dash", line_color="red")

    # Improve layout
    fig.update_layout(xaxis_tickangle=-45)

    st.plotly_chart(fig, use_container_width=True)


def display_project_workload_breakdown(filtered_data: pd.DataFrame) -> None:
    """
    Display project workload breakdown.

    Args:
        filtered_data: Filtered DataFrame of resource allocation data
    """
    if filtered_data.empty:
        return

    # Get chart height from display preferences
    display_prefs = load_display_preferences()
    chart_height = display_prefs.get("chart_height", 600)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Project Resource Distribution")

        # Calculate resources per project
        project_resources = (
            filtered_data.groupby("Project")["Resource"].nunique().reset_index()
        )
        project_resources = project_resources.sort_values("Resource", ascending=False)

        # Create chart
        fig1 = px.bar(
            project_resources,
            x="Project",
            y="Resource",
            title="Resources Per Project",
            labels={"Project": "Project", "Resource": "Number of Resources"},
            height=chart_height,  # Use configurable chart height
        )

        fig1.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        st.subheader("Department Workload")

        # Get department for each resource
        resource_dept = filtered_data[
            ["Resource", "Department", "Allocation %"]
        ].drop_duplicates()
        dept_allocation = (
            resource_dept.groupby("Department")["Allocation %"].sum().reset_index()
        )

        # Create pie chart
        fig2 = px.pie(
            dept_allocation,
            values="Allocation %",
            names="Department",
            title="Workload by Department",
            height=chart_height,  # Use configurable chart height
        )

        st.plotly_chart(fig2, use_container_width=True)


def display_resource_conflicts_enhanced(filtered_data: pd.DataFrame) -> None:
    """
    Display enhanced resource conflicts visualization with severity indicators.

    Args:
        filtered_data: Filtered DataFrame of resource allocation data
    """
    # Get chart height from display preferences
    display_prefs = load_display_preferences()
    chart_height = display_prefs.get("chart_height", 600)

    st.subheader("Resource Conflicts")
    conflicts = find_resource_conflicts(filtered_data)

    if conflicts.empty:
        st.success("No resource conflicts detected in the selected date range.")
        return

    # Group conflicts by resource
    resources = conflicts["Resource"].unique()

    # Create a summary bar chart of conflicts
    conflict_summary = conflicts.groupby("Resource")["Allocation"].max().reset_index()
    conflict_summary = conflict_summary.sort_values("Allocation", ascending=False)

    # Define a function to categorize the severity
    def get_severity(allocation):
        if allocation > 150:
            return "Critical"
        elif allocation > 125:
            return "High"
        else:
            return "Medium"

    conflict_summary["Severity"] = conflict_summary["Allocation"].apply(get_severity)

    # Create a bar chart with color based on severity
    fig = px.bar(
        conflict_summary,
        x="Resource",
        y="Allocation",
        color="Severity",
        title="Resource Conflict Severity",
        labels={"Resource": "Resource", "Allocation": "Peak Allocation (%)"},
        color_discrete_map={"Critical": "red", "High": "orange", "Medium": "yellow"},
        height=chart_height,  # Use configurable chart height
    )

    fig.add_hline(y=100, line_width=2, line_dash="dash", line_color="gray")
    st.plotly_chart(fig, use_container_width=True)

    # For each resource with conflicts, show the detailed conflicts
    for resource in resources:
        resource_conflicts = conflicts[conflicts["Resource"] == resource]
        max_allocation = resource_conflicts["Allocation"].max()
        severity = get_severity(max_allocation)

        # Use colored icons based on severity
        if severity == "Critical":
            icon = "🔴"
        elif severity == "High":
            icon = "🟠"
        else:
            icon = "🟡"

        with st.expander(
            f"{icon} {resource} ({len(resource_conflicts)} overallocations, peak: {max_allocation:.0f}%)"
        ):
            dates = resource_conflicts["Date"].dt.strftime("%Y-%m-%d").tolist()
            allocations = resource_conflicts["Allocation"].tolist()
            projects = resource_conflicts["Projects"].tolist()

            # Create a simple table with the conflicts
            conflict_data = pd.DataFrame(
                {
                    "Date": dates,
                    "Allocation %": allocations,
                    "Conflicting Projects": projects,
                }
            )

            st.dataframe(conflict_data, use_container_width=True)


def display_resource_utilization_tab():
    """Display the resource utilization/performance metrics tab."""
    display_action_bar()
    st.subheader("Performance Metrics")

    if not st.session_state.data["projects"]:
        st.warning("No projects found. Please add projects first.")
        return

    if not (
        st.session_state.data["people"]
        or st.session_state.data["teams"]
        or st.session_state.data["departments"]
    ):
        st.warning(
            "No resources found. Please add people, teams, or departments first."
        )
        return

    # Get filters using the standardized filter component
    filters = create_resource_analytics_filters("performance")

    # Create the Gantt data
    gantt_data = create_gantt_data(
        st.session_state.data["projects"], st.session_state.data
    )

    # Apply filters
    filtered_data = apply_filters(gantt_data, filters)

    # Extract date range
    start_date = filters["date_range"][0]
    end_date = filters["date_range"][1]

    # Display the dashboard with filtered data
    if filtered_data.empty:
        st.warning("No data matches your filter criteria. Try adjusting the filters.")
    else:
        display_performance_metrics_dashboard(filtered_data, start_date, end_date)


def display_performance_metrics_dashboard(
    filtered_data: pd.DataFrame, start_date: pd.Timestamp, end_date: pd.Timestamp
) -> None:
    """
    Display comprehensive performance metrics dashboard with visualizations focused on resource efficiency.

    Args:
        filtered_data: Filtered DataFrame of resource allocation data
        start_date: Start date for the visualization
        end_date: End date for the visualization
    """
    # Get chart height from display preferences
    display_prefs = load_display_preferences()
    chart_height = display_prefs.get("chart_height", 600)

    # Calculate utilization metrics
    utilization_df = calculate_resource_utilization(filtered_data)

    if utilization_df.empty:
        st.info("No utilization data available with current filters.")
        return

    # Load utilization thresholds
    thresholds = load_utilization_thresholds()
    under_threshold = thresholds.get("under", 50)
    optimal_min = thresholds.get("optimal_min", 70)
    optimal_max = thresholds.get("optimal_max", 90)
    over_threshold = thresholds.get("over", 100)

    # 1. Display Key Performance Indicators (REVISED: Single row with most important metrics)
    st.subheader("Performance Summary")

    # Calculate key metrics
    avg_util = utilization_df["Utilization %"].mean()
    median_util = utilization_df["Utilization %"].median()
    std_util = utilization_df[
        "Utilization %"
    ].std()  # Standard deviation for variability

    # Calculate resource distribution
    total_resources = len(utilization_df)
    over_utilized = sum(utilization_df["Utilization %"] > over_threshold)
    under_utilized = sum(utilization_df["Utilization %"] < under_threshold)
    optimal_utilized = sum(
        (utilization_df["Utilization %"] >= optimal_min)
        & (utilization_df["Utilization %"] <= optimal_max)
    )

    # Calculate efficiency score (percentage of resources in optimal range)
    efficiency_score = (
        (optimal_utilized / total_resources * 100) if total_resources > 0 else 0
    )

    # REVISED: Display most important metrics in a single row (5 columns)
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            "Average Utilization",
            f"{avg_util:.1f}%",
            delta=f"{avg_util - 75:.1f}%" if avg_util != 75 else None,
            delta_color="normal"
            if optimal_min <= avg_util <= optimal_max
            else "inverse",
        )

    with col2:
        optimal_pct = (
            (optimal_utilized / total_resources * 100) if total_resources > 0 else 0
        )
        st.metric(
            "Optimally Utilized",
            f"{optimal_utilized} ({optimal_pct:.1f}%)",
            help=f"Resources within {optimal_min}% to {optimal_max}%",
        )

    with col3:
        over_pct = (over_utilized / total_resources * 100) if total_resources > 0 else 0
        st.metric(
            "Overallocated",
            f"{over_utilized} ({over_pct:.1f}%)",
            delta_color="inverse",
            help=f"Resources above {over_threshold}%",
        )

    with col4:
        st.metric(
            "Efficiency Score",
            f"{efficiency_score:.1f}%",
            help=f"Percentage of resources within optimal utilization range ({optimal_min}%-{optimal_max}%)",
        )

    with col5:
        st.metric(
            "Resource Balance",
            f"{std_util:.1f}%",
            help="Lower values indicate more balanced allocation across resources (standard deviation)",
        )

    # 2. Resource Efficiency Analysis
    st.subheader("Resource Efficiency Analysis")

    # Create two column layout - REVISED with 8:2 ratio to give even more space to the chart
    col1, col2 = st.columns([8, 2])

    with col1:
        # Define a performance score - higher for being in optimal range
        def calculate_performance_score(util):
            if optimal_min <= util <= optimal_max:
                return 100  # Full score for optimal range
            elif util < optimal_min:
                # Linear scale from 0 to score at optimal_min
                return (util / optimal_min) * 80
            else:  # util > optimal_max
                if util <= over_threshold:
                    # Linear scale from score at optimal_max to score at over_threshold
                    over_range = over_threshold - optimal_max
                    over_percent = (util - optimal_max) / over_range
                    return 80 - (over_percent * 30)  # Score decreases from 80 to 50
                else:
                    # Linear scale from score at over_threshold to 0 at 150%
                    excess = min(util - over_threshold, 50)  # Cap at 50% over
                    return 50 - (excess)  # Score decreases from 50 to 0

        # Add performance score
        utilization_df["Performance Score"] = utilization_df["Utilization %"].apply(
            calculate_performance_score
        )

        # Add visual performance rating with high-contrast symbols
        def get_performance_rating(score):
            if score >= 90:
                return "⭐⭐⭐⭐⭐"  # Using emoji stars for better visibility
            elif score >= 75:
                return "⭐⭐⭐⭐☆"
            elif score >= 60:
                return "⭐⭐⭐☆☆"
            elif score >= 40:
                return "⭐⭐☆☆☆"
            else:
                return "⭐☆☆☆☆"

        utilization_df["Rating"] = utilization_df["Performance Score"].apply(
            get_performance_rating
        )

        # Get top performers
        top_performers = utilization_df.sort_values(
            "Performance Score", ascending=False
        ).head(10)

        # Create horizontal bar chart - IMPROVED COLOR SCHEME
        # Using a more neutral color palette that works better in both themes
        colors = [
            "#4285F4",  # Blue
            "#34A853",  # Green
            "#FBBC05",  # Yellow
            "#EA4335",  # Red
        ]

        # Assign colors based on resource type
        def get_type_color(resource_type):
            type_colors = {
                "Person": colors[0],
                "Team": colors[1],
                "Department": colors[2],
            }
            return type_colors.get(resource_type, colors[3])

        top_performers["Color"] = top_performers["Type"].apply(get_type_color)

        # Create chart - REVISED for better star visibility with perfect scores
        fig1 = go.Figure()

        # Add bars for each resource
        for idx, row in top_performers.iterrows():
            fig1.add_trace(
                go.Bar(
                    y=[row["Resource"]],
                    x=[row["Performance Score"]],
                    orientation="h",
                    name=row["Type"],
                    marker_color=row["Color"],
                    textposition="none",
                    hovertext=f"{row['Resource']} - {row['Type']}<br>Utilization: {row['Utilization %']:.1f}%<br>Score: {row['Performance Score']:.1f}",
                    hoverinfo="text",
                )
            )

        # Update layout - IMPROVED to ensure stars show even at 100% score
        fig1.update_layout(
            title="Top 10 Most Efficient Resources",
            xaxis_title="Performance Score",
            yaxis_title="Resource",
            showlegend=False,
            margin=dict(l=10, r=120, t=40, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(
                range=[0, 120],
                gridcolor="rgba(128,128,128,0.2)",
                tickvals=[0, 20, 40, 60, 80, 100],
            ),
            yaxis=dict(
                gridcolor="rgba(128,128,128,0.2)",
            ),
            height=chart_height,  # Add configurable chart height
            annotations=[
                dict(
                    x=row["Performance Score"]
                    + 5,  # Reduced offset from 10 to 5 (50% closer)
                    y=i,
                    text=f"{row['Rating']} ({row['Utilization %']:.1f}%)",
                    showarrow=False,
                    font=dict(size=14),
                    xanchor="left",
                    bgcolor="rgba(255,255,255,0.7)",
                    bordercolor="rgba(0,0,0,0.2)",
                    borderwidth=1,
                    borderpad=4,
                    opacity=0.8,
                )
                for i, (_, row) in enumerate(top_performers.iterrows())
            ],
        )

        st.plotly_chart(fig1, use_container_width=True)

    # IMPROVED: Rating legend with reduced font size
    with col2:
        # Reduced vertical spacing to align with graph title
        st.markdown("<br>", unsafe_allow_html=True)

        # Create a styled box for the legend with consistent but smaller star styling
        st.markdown(
            """
        <div style="border:1px solid rgba(128,128,128,0.3); border-radius:5px; padding:8px; background-color:rgba(128,128,128,0.05);">
        <p style="font-weight:bold; margin-bottom:6px; font-size:0.95em;">Performance Rating Scale</p>
        <p style="margin:4px 0;"><span style="font-size:1.05em;">⭐⭐⭐⭐⭐</span> <span style="opacity:0.8; font-size:0.85em;">(90-100): Excellent</span></p>
        <p style="margin:4px 0;"><span style="font-size:1.05em;">⭐⭐⭐⭐☆</span> <span style="opacity:0.8; font-size:0.85em;">(75-89): Very good</span></p>
        <p style="margin:4px 0;"><span style="font-size:1.05em;">⭐⭐⭐☆☆</span> <span style="opacity:0.8; font-size:0.85em;">(60-74): Good</span></p>
        <p style="margin:4px 0;"><span style="font-size:1.05em;">⭐⭐☆☆☆</span> <span style="opacity:0.8; font-size:0.85em;">(40-59): Fair</span></p>
        <p style="margin:4px 0;"><span style="font-size:1.05em;">⭐☆☆☆☆</span> <span style="opacity:0.8; font-size:0.85em;">(0-39): Poor</span></p>
        <hr style="margin:6px 0; opacity:0.2;">
        <p style="font-size:0.8em; opacity:0.8; margin-bottom:0;">The Performance Score reflects how close a resource is to optimal utilization (70-90% range).</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    # Resource Allocation Balance - FIX for Balance Score line color in dark theme
    if "Department" in filtered_data.columns:
        # Calculate department/team metrics
        dept_util = (
            filtered_data.groupby(["Department", "Resource"])["Allocation %"]
            .sum()
            .reset_index()
        )

        dept_metrics = []
        for dept, group in dept_util.groupby("Department"):
            avg_util = group["Allocation %"].mean()
            optimal_count = sum(
                (group["Allocation %"] >= optimal_min)
                & (group["Allocation %"] <= optimal_max)
            )
            efficiency = (optimal_count / len(group) * 100) if len(group) > 0 else 0

            # REVISED status calculation to ensure proper categorization
            status = "Optimal"
            if avg_util < optimal_min:
                status = "Underutilized"
            elif avg_util > over_threshold:
                status = "Overutilized"

            dept_metrics.append(
                {
                    "Department": dept,
                    "Average Utilization": avg_util,
                    "Resource Count": len(group),
                    "Efficiency Score": efficiency,
                    "Optimal Resources": optimal_count,
                    "Utilization Status": status,  # Corrected status logic
                }
            )

        if dept_metrics:
            dept_df = pd.DataFrame(dept_metrics)

            # Sort by efficiency score
            dept_df = dept_df.sort_values("Efficiency Score", ascending=False)

            # Create color map for utilization status with more distinct colors
            status_colors = {
                "Optimal": "#66bb6a",  # Green
                "Underutilized": "#ffca28",  # Amber
                "Overutilized": "#ff7043",  # Orange
            }

            # Create bar chart - IMPROVED for better reference visualization
            fig3 = px.bar(
                dept_df,
                x="Department",
                y="Average Utilization",
                color="Utilization Status",
                color_discrete_map=status_colors,
                text="Average Utilization",
                hover_data=["Efficiency Score", "Optimal Resources", "Resource Count"],
                labels={
                    "Department": "Department/Team",
                    "Average Utilization": "Average Utilization (%)",
                    "Efficiency Score": "Efficiency Score (%)",
                    "Optimal Resources": "Resources in Optimal Range",
                    "Resource Count": "Total Resources",
                },
                title="Department Utilization by Status",
                height=chart_height,  # Add configurable chart height
            )

            # Format text to show percentages
            fig3.update_traces(texttemplate="%{text:.1f}%", textposition="outside")

            # Create custom hover template
            fig3.update_traces(
                hovertemplate="<b>%{x}</b><br>"
                + "Utilization: %{y:.1f}%<br>"
                + "Resources: %{customdata[2]}<br>"
                + "Efficiency Score: %{customdata[0]:.1f}%<br>"
                + "Optimal Resources: %{customdata[1]}<extra></extra>"
            )

            fig3.add_hrect(
                y0=optimal_min,
                y1=optimal_max,
                fillcolor="rgba(66, 165, 245, 0.5)",
                line_width=0,
                annotation_text="Optimal",
                annotation_position="right",
                annotation=dict(
                    font=dict(color="#1B5E20", size=12),
                    bgcolor="rgba(255,255,255,0.7)",
                    bordercolor="#1B5E20",
                    borderwidth=1,
                ),
                layer="above",  # Position above the bars
            )

            # Add over threshold line - keep this one
            fig3.add_shape(
                type="line",
                x0=-0.5,
                x1=len(dept_df) - 0.5,
                y0=over_threshold,
                y1=over_threshold,
                line=dict(
                    color="#B71C1C",  # Dark red for better contrast
                    width=3,
                    dash="dot",
                ),
                layer="above",  # Place above the bars
            )

            # Add just the overallocated annotation
            fig3.add_annotation(
                x=len(dept_df) - 0.5,
                y=over_threshold,
                text="Overallocated",
                showarrow=False,
                font=dict(color="#B71C1C", size=12),
                bgcolor="rgba(255,255,255,0.7)",
                bordercolor="#B71C1C",
                borderwidth=1,
                borderpad=3,
                xanchor="right",
            )

            # Update layout for better visibility in both themes
            fig3.update_layout(
                margin=dict(l=10, r=10, t=40, b=80),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(gridcolor="rgba(128,128,128,0.2)", tickangle=-45),
                yaxis=dict(
                    gridcolor="rgba(128,128,128,0.2)",
                    range=[0, max(150, dept_df["Average Utilization"].max() * 1.1)],
                ),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1,
                ),
                height=chart_height,  # Add configurable chart height
            )

            st.plotly_chart(fig3, use_container_width=True)

            # REPLACEMENT: New metric instead of the radar chart
            st.subheader("Resource Allocation Balance")

            # Create resource allocation distribution analysis
            allocation_ranges = [
                (0, 30, "Very Low (0-30%)"),
                (30, 50, "Low (30-50%)"),
                (50, 70, "Moderate (50-70%)"),
                (70, 90, "Optimal (70-90%)"),
                (90, 100, "High (90-100%)"),
                (100, float("inf"), "Overallocated (>100%)"),
            ]

            distribution_data = []
            for dept, group in dept_util.groupby("Department"):
                dept_data = {"Department": dept}
                total_resources = len(group)

                # Calculate distribution across allocation ranges
                for lower, upper, label in allocation_ranges:
                    count = sum(
                        (group["Allocation %"] >= lower)
                        & (group["Allocation %"] < upper)
                    )
                    pct = (count / total_resources * 100) if total_resources > 0 else 0
                    dept_data[label] = pct

                # Add additional metrics
                dept_data["Total Resources"] = total_resources
                # Calculate balance score (higher when most resources are in optimal range)
                optimal_count = sum(
                    (group["Allocation %"] >= 70) & (group["Allocation %"] <= 90)
                )
                dept_data["Balance Score"] = (
                    (optimal_count / total_resources * 100)
                    if total_resources > 0
                    else 0
                )

                distribution_data.append(dept_data)

            if distribution_data:
                dist_df = pd.DataFrame(distribution_data)

                # Sort by Balance Score
                dist_df = dist_df.sort_values("Balance Score", ascending=False)

                display_df = dist_df  # Show all departments, no filtering

                # Create a stacked bar chart to show distribution
                allocation_cols = [
                    col
                    for col in dist_df.columns
                    if col not in ["Department", "Total Resources", "Balance Score"]
                ]

                fig_dist = go.Figure()

                # Use a color scale appropriate for allocation levels (low to high)
                colors = [
                    "#E3F2FD",
                    "#90CAF9",
                    "#42A5F5",
                    "#2196F3",
                    "#1976D2",
                    "#FF5252",
                ]

                # Loop through allocation categories - Fix error in iteration
                for i, col in enumerate(allocation_cols):
                    fig_dist.add_trace(
                        go.Bar(
                            name=col,
                            x=display_df["Department"],
                            y=display_df[col],
                            marker_color=colors[i],
                            hovertemplate="%{y:.1f}% of resources",
                        )
                    )

                # Add balance score as a line with high-visibility color
                fig_dist.add_trace(
                    go.Scatter(
                        x=display_df["Department"],
                        y=display_df["Balance Score"],
                        mode="lines+markers",
                        name="Balance Score",
                        line=dict(
                            color="#00BCD4", width=3
                        ),  # Bright cyan - visible in both themes
                        marker=dict(size=10, symbol="diamond", color="#00BCD4"),
                        yaxis="y2",
                    )
                )

                # Update layout - FIX for yaxis2 title definition and improved styling
                fig_dist.update_layout(
                    title="Department Resource Allocation Distribution",
                    xaxis=dict(title="Department", tickangle=-45),
                    yaxis=dict(
                        title="Percentage of Resources",
                        gridcolor="rgba(128,128,128,0.2)",
                    ),
                    yaxis2=dict(
                        title=dict(
                            text="Balance Score",
                            font=dict(color="#00BCD4"),  # Match the line color
                        ),
                        tickfont=dict(color="#00BCD4"),  # Match the line color
                        overlaying="y",
                        side="right",
                        range=[0, 100],
                        gridcolor="rgba(0,0,0,0)",
                        zerolinecolor="rgba(0,0,0,0)",
                    ),
                    barmode="stack",
                    legend=dict(
                        orientation="h",  # Keep horizontal orientation
                        yanchor="bottom",  # Keep at bottom
                        y=1.02,  # Keep y position
                        xanchor="right",  # Changed from "center" to "right"
                        x=1,  # Changed from 0.5 to 1 (right aligned)
                    ),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    margin=dict(l=10, r=10, t=40, b=100),
                    height=chart_height,  # Add configurable chart height
                )

                st.plotly_chart(fig_dist, use_container_width=True)

                # Place explanation in an expander with help icon for better UX
                with st.expander(
                    "ℹ️ Understanding the Resource Allocation Distribution",
                    expanded=False,
                ):
                    st.markdown(
                        """
                    <div style="background-color:rgba(0,188,212,0.1); border-left:3px solid #00BCD4; padding:10px; border-radius:2px;">
                    <p><strong>Understanding the Resource Allocation Distribution:</strong></p>
                    <ul>
                        <li>The <strong>stacked bars</strong> show how resources are distributed across utilization ranges within each department.</li>
                        <li>The <strong>cyan line</strong> represents the Balance Score - higher scores indicate more resources in the optimal utilization range (70-90%).</li>
                        <li>An ideally balanced department would have most resources in the "Optimal" category with minimal overallocation or underutilization.</li>
                    </ul>
                    <p><strong>Note:</strong> If all resources show the same allocation level (e.g., all at 100%), this indicates all resources are allocated at the same percentage in your project data.</p>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )

    # 4. Performance Trends Over Time - FIX: Corrected weekly data filtering logic
    st.subheader("Performance Trends")

    # Create date range with weekly intervals
    date_range = pd.date_range(start=start_date, end=end_date, freq="W")

    if len(date_range) > 1:
        # Create a dataframe to store utilization over time
        weekly_data = []

        for i in range(len(date_range) - 1):
            week_start = date_range[i]
            week_end = date_range[i + 1]

            # Filter data for this week - FIX: Use filtered_data in the condition, not week_data
            week_data = filtered_data[
                (filtered_data["Start"] <= week_end)
                & (filtered_data["End"] >= week_start)
            ]

            if not week_data.empty:
                # Calculate utilization for resources this week
                week_util = calculate_resource_utilization(week_data)

                # Calculate metrics
                avg_util = week_util["Utilization %"].mean()
                median_util = week_util["Utilization %"].median()
                optimal_count = sum(
                    (week_util["Utilization %"] >= optimal_min)
                    & (week_util["Utilization %"] <= optimal_max)
                )
                total_count = len(week_util)
                efficiency = (
                    (optimal_count / total_count * 100) if total_count > 0 else 0
                )

                weekly_data.append(
                    {
                        "Week": week_start.strftime("%b %d"),
                        "Average Utilization": avg_util,
                        "Median Utilization": median_util,
                        "Efficiency Score": efficiency,
                        "Resource Count": total_count,
                    }
                )

        if weekly_data:
            # Create dataframe
            trend_df = pd.DataFrame(weekly_data)

            # Create line chart - REVERTED to original style with theme improvements
            fig4 = go.Figure()

            # Add lines for key metrics
            fig4.add_trace(
                go.Scatter(
                    x=trend_df["Week"],
                    y=trend_df["Average Utilization"],
                    mode="lines+markers",
                    name="Average Utilization",
                    line=dict(color="#42a5f5", width=3),  # Blue
                    marker=dict(size=8),
                )
            )

            fig4.add_trace(
                go.Scatter(
                    x=trend_df["Week"],
                    y=trend_df["Median Utilization"],
                    mode="lines+markers",
                    name="Median Utilization",
                    line=dict(color="#66bb6a", width=3),  # Green
                    marker=dict(size=8),
                )
            )

            fig4.add_trace(
                go.Scatter(
                    x=trend_df["Week"],
                    y=trend_df["Efficiency Score"],
                    mode="lines+markers",
                    name="Efficiency Score",
                    line=dict(color="#ab47bc", width=3),  # Purple
                    marker=dict(size=8),
                )
            )

            # Add reference zones
            fig4.add_hrect(
                y0=optimal_min,
                y1=optimal_max,
                fillcolor="rgba(102, 187, 106, 0.1)",  # Very light green
                line_width=0,
                annotation_text="Optimal Zone",
                annotation_position="top right",
            )

            # Add line for 100% utilization
            fig4.add_hline(
                y=100,
                line_dash="dash",
                line_color="rgba(244, 67, 54, 0.7)",  # Semi-transparent red
            )

            # REVERTED: Go back to standard hover with theme-compatible styling
            fig4.update_layout(
                title="Weekly Performance Trends",
                xaxis_title="Week",
                yaxis_title="Metrics (%)",
                margin=dict(l=10, r=10, t=40, b=40),
                paper_bgcolor="rgba(0,0,0,0)",  # Transparent background
                plot_bgcolor="rgba(0,0,0,0)",  # Transparent background
                legend=dict(
                    orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
                ),
                xaxis=dict(
                    gridcolor="rgba(128,128,128,0.2)",  # Light grid that works in both themes
                ),
                yaxis=dict(
                    gridcolor="rgba(128,128,128,0.2)",  # Light grid that works in both themes
                    range=[0, 110],  # Slightly above 100% to show the full range
                ),
                # Use default hover mode but with theme-compatible styling
                hovermode="x unified",
                hoverlabel=dict(
                    bordercolor="rgba(0, 0, 0, 0.3)",
                    # No bgcolor setting to allow default theme-aware colors
                    font_size=12,
                ),
                height=chart_height,  # Add configurable chart height
            )

            st.plotly_chart(fig4, use_container_width=True)
        else:
            st.info("Insufficient time-based data to display performance trends.")
    else:
        st.info(
            "Selected date range is too short to display meaningful trends. Please select a longer period."
        )

    # 5. Detailed Performance Data Table - No changes needed
    with st.expander("Detailed Resource Performance Data", expanded=False):
        # Prepare table data
        table_data = utilization_df.copy()

        # Sort by performance score
        table_data = table_data.sort_values("Performance Score", ascending=False)

        # Format display columns
        display_cols = [
            "Resource",
            "Type",
            "Department",
            "Utilization %",
            "Performance Score",
            "Rating",
            "Utilization Category",
        ]

        # Select only columns that exist
        display_cols = [col for col in display_cols if col in table_data.columns]

        st.dataframe(
            table_data[display_cols],
            column_config={
                "Utilization %": st.column_config.NumberColumn(
                    "Utilization %",
                    format="%.1f%%",
                ),
                "Performance Score": st.column_config.ProgressColumn(
                    "Performance Score",
                    format="%.1f",
                    min_value=0,
                    max_value=100,
                ),
            },
            hide_index=True,
            use_container_width=True,
        )


def display_capacity_planning_tab():
    """Display the capacity planning/availability forecast tab."""
    display_action_bar()
    st.subheader("Availability Forecast")

    if not st.session_state.data["projects"]:
        st.warning("No projects found. Please add projects first.")
        return

    if not (
        st.session_state.data["people"]
        or st.session_state.data["teams"]
        or st.session_state.data["departments"]
    ):
        st.warning(
            "No resources found. Please add people, teams, or departments first."
        )
        return

    # Get filters using the standardized filter component
    filters = create_resource_analytics_filters("availability")

    # Create and filter data
    gantt_data = create_gantt_data(
        st.session_state.data["projects"], st.session_state.data
    )

    # Apply filters
    filtered_data = apply_filters(gantt_data, filters)

    # Extract date range
    start_date = filters["date_range"][0]
    end_date = filters["date_range"][1]

    # Display the dashboard with filtered data
    if filtered_data.empty:
        st.warning("No data matches your filter criteria. Try adjusting the filters.")
    else:
        display_capacity_planning_dashboard(filtered_data, start_date, end_date)


def display_capacity_planning_dashboard(
    filtered_data: pd.DataFrame, start_date: pd.Timestamp, end_date: pd.Timestamp
) -> None:
    """
    Display the capacity planning dashboard with forecast charts.

    Args:
        filtered_data: Filtered DataFrame of resource allocation data
        start_date: Start date for the visualization
        end_date: End date for the visualization
    """
    # Get chart height from display preferences
    display_prefs = load_display_preferences()
    chart_height = display_prefs.get("chart_height", 600)

    st.subheader("Capacity Planning Dashboard")

    # Generate capacity data
    capacity_data = calculate_capacity_data(filtered_data, start_date, end_date)

    if capacity_data.empty:
        st.info("No capacity data available with current filters.")
        return

    # Display availability summary metrics
    display_availability_summary_metrics(capacity_data)

    # Display availability timeline
    display_availability_timeline(capacity_data, chart_height)

    # Display department/team availability breakdown
    display_availability_by_group(capacity_data, chart_height)

    # Create a heatmap of resource allocations over time
    # First, pivot the data to have resources as rows and dates as columns
    pivot_data = capacity_data.pivot_table(
        index="Resource", columns="Date", values="Allocation", aggfunc="sum"
    )

    # Convert allocation to availability (100% - allocation)
    availability_data = 100 - pivot_data

    # Sort resources by average availability
    avg_availability = availability_data.mean(axis=1).sort_values(ascending=False)
    sorted_availability = availability_data.loc[avg_availability.index]

    # Create a heatmap using plotly with availability data
    heatmap = px.imshow(
        sorted_availability.values,
        labels=dict(x="Date", y="Resource", color="Availability %"),
        x=sorted_availability.columns.strftime("%Y-%m-%d"),
        y=sorted_availability.index,
        color_continuous_scale="YlGnBu",  # Using YlGnBu - works well in both themes
        title="Resource Availability Heatmap",
        height=chart_height,
    )

    # Add better axis formatting
    heatmap.update_layout(
        xaxis=dict(
            tickangle=-45,
            tickmode="auto",
            nticks=20,
            tickformat="%b %d",
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        coloraxis_colorbar=dict(
            title="Availability %",
            ticksuffix="%",
        ),
        margin=dict(l=10, r=10, t=40, b=80),
    )

    # Add annotation to explain the heatmap
    heatmap.add_annotation(
        x=0.5,
        y=-0.15,
        xref="paper",
        yref="paper",
        text="Darker blue indicates higher resource availability. Resources with highest average availability are shown at the top.",
        showarrow=False,
        font=dict(size=12),
        opacity=0.8,
        align="center",
    )

    st.plotly_chart(heatmap, use_container_width=True)

    # Display resource capacity forecast
    display_capacity_forecast(capacity_data, start_date, end_date, chart_height)


def display_availability_summary_metrics(capacity_data: pd.DataFrame) -> None:
    """
    Display summary metrics for resource availability.

    Args:
        capacity_data: DataFrame containing resource allocation data
    """
    if capacity_data.empty:
        return

    # Calculate availability metrics
    # 1. Average availability across all resources
    avg_allocation = capacity_data["Allocation"].mean()
    avg_availability = 100 - avg_allocation

    # 2. Find days with highest availability
    daily_allocation = capacity_data.groupby("Date")["Allocation"].mean()
    daily_availability = 100 - daily_allocation

    # Find the date with highest availability
    if not daily_availability.empty:
        best_date = daily_availability.idxmax()
        best_date_availability = daily_availability.max()
        best_date_str = best_date.strftime("%b %d, %Y")
    else:
        best_date_str = "N/A"
        best_date_availability = 0

    # 3. Count resources with high availability (>50%)
    high_avail_resources = capacity_data.groupby("Resource")["Allocation"].mean()
    high_avail_count = sum(
        high_avail_resources < 50
    )  # Less than 50% allocated means >50% available

    # 4. Calculate availability trend (increasing or decreasing)
    if len(daily_availability) > 1:
        # Simple linear regression slope to determine trend
        x = np.arange(len(daily_availability))
        y = daily_availability.values
        slope = np.polyfit(x, y, 1)[0]
        trend_direction = (
            "Increasing" if slope > 0 else "Decreasing" if slope < 0 else "Stable"
        )
        trend_value = abs(slope) * len(daily_availability)  # Total change over period
    else:
        trend_direction = "Stable"
        trend_value = 0

    # Display metrics in columns
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Average Availability",
            f"{avg_availability:.1f}%",
            help="Average resource availability across the entire period",
        )

    with col2:
        st.metric(
            "Best Date for Planning",
            best_date_str,
            delta=f"{best_date_availability:.1f}% Available",
            help="Date with highest average resource availability",
        )

    with col3:
        st.metric(
            "Resources >50% Available",
            high_avail_count,
            help="Number of resources with more than 50% availability",
        )

    with col4:
        delta_color = (
            "normal"
            if trend_direction == "Increasing"
            else "inverse"
            if trend_direction == "Decreasing"
            else "off"
        )
        st.metric(
            "Availability Trend",
            trend_direction,
            delta=f"{trend_value:.1f}% {trend_direction}"
            if trend_value > 0.5
            else None,
            delta_color=delta_color,
            help="Whether resource availability is increasing or decreasing over time",
        )


def display_availability_timeline(
    capacity_data: pd.DataFrame, chart_height: int = 600
) -> None:
    """
    Display a timeline chart showing resource availability over time.

    Args:
        capacity_data: DataFrame containing resource allocation data
        chart_height: Height of the chart in pixels
    """
    if capacity_data.empty:
        return

    st.subheader("Availability Timeline")

    # Calculate daily allocation metrics
    daily_metrics = (
        capacity_data.groupby("Date")
        .agg({"Allocation": ["mean", "min", "max", "count"]})
        .reset_index()
    )

    # Flatten the column names
    daily_metrics.columns = [
        "Date",
        "Mean Allocation",
        "Min Allocation",
        "Max Allocation",
        "Resource Count",
    ]

    # Calculate availability metrics (100% - allocation)
    daily_metrics["Mean Availability"] = 100 - daily_metrics["Mean Allocation"]
    daily_metrics["Max Availability"] = (
        100 - daily_metrics["Min Allocation"]
    )  # Min allocation = Max availability
    daily_metrics["Min Availability"] = (
        100 - daily_metrics["Max Allocation"]
    )  # Max allocation = Min availability

    # Create the timeline chart
    fig = go.Figure()

    # Use a more visible color for the legend marker
    range_color = "rgba(33, 150, 243, 0.7)"  # More visible blue for legend
    fill_color = "rgba(33, 150, 243, 0.2)"  # Light blue for actual area fill

    fig.add_trace(
        go.Scatter(
            x=daily_metrics["Date"],
            y=daily_metrics["Max Availability"],
            fill=None,
            mode="lines",
            line=dict(width=1, color=range_color),  # More visible line for legend
            name="Availability Range",
            showlegend=True,
            hoverinfo="skip",
            legendgroup="availability_range",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=daily_metrics["Date"],
            y=daily_metrics["Min Availability"],
            fill="tonexty",  # Fill to the trace before
            mode="lines",
            line=dict(width=0),
            fillcolor=fill_color,
            name="Availability Range",
            showlegend=False,
            hovertemplate="Date: %{x}<br>Range: %{y:.1f}% - %{customdata:.1f}%<extra></extra>",
            customdata=daily_metrics["Max Availability"],
            legendgroup="availability_range",
        )
    )

    # Add mean availability line
    fig.add_trace(
        go.Scatter(
            x=daily_metrics["Date"],
            y=daily_metrics["Mean Availability"],
            mode="lines+markers",
            line=dict(color="#2196F3", width=3),  # Blue color
            marker=dict(size=7),
            name="Average Availability",
        )
    )

    # Add resource count as a secondary axis
    fig.add_trace(
        go.Scatter(
            x=daily_metrics["Date"],
            y=daily_metrics["Resource Count"],
            mode="lines",
            line=dict(color="#FF9800", width=2, dash="dot"),  # Orange color
            name="Resource Count",
            yaxis="y2",
        )
    )

    # Add reference lines
    fig.add_hline(
        y=70,
        line_width=1,
        line_dash="dash",
        line_color="green",
        annotation_text="High Availability (70%+)",
        annotation_position="top right",
    )
    fig.add_hline(
        y=30,
        line_width=1,
        line_dash="dash",
        line_color="red",
        annotation_text="Low Availability (<30%)",
        annotation_position="bottom right",
    )

    # Update layout with dual y-axis
    fig.update_layout(
        title="Resource Availability Over Time",
        xaxis_title="Date",
        yaxis=dict(
            title="Availability %",
            range=[0, 100],
            gridcolor="rgba(128,128,128,0.2)",
            ticksuffix="%",
        ),
        yaxis2=dict(
            title=dict(text="Resource Count", font=dict(color="#FF9800")),
            tickfont=dict(color="#FF9800"),
            anchor="x",
            overlaying="y",
            side="right",
            gridcolor="rgba(0,0,0,0)",
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=40, b=40),
        height=chart_height,
        hovermode="x unified",
    )

    st.plotly_chart(fig, use_container_width=True)

    # Add explanation of the chart
    with st.expander("ℹ️ Understanding the Availability Timeline", expanded=False):
        st.markdown(
            """
        <div style="background-color:rgba(0,188,212,0.1); border-left:3px solid #00BCD4; padding:10px; border-radius:2px;">
        <p><strong>Understanding the Availability Timeline:</strong></p>
        <ul>
            <li>The <strong>blue line</strong> indicates average resource availability across all resources for each day</li>
            <li>The <strong>light blue area</strong> shows the range between minimum and maximum resource availability</li>
            <li>The <strong>orange dotted line</strong> represents the number of resources available on each day</li>
            <li>The <strong>green dashed line</strong> marks the high availability threshold (70%)</li>
            <li>The <strong>red dashed line</strong> marks the low availability threshold (30%)</li>
        </ul>
        <p><strong>Note:</strong> This chart helps you identify days with higher resource availability for planning new work.</p>
        </div>
        """,
            unsafe_allow_html=True,
        )


def display_availability_by_group(
    capacity_data: pd.DataFrame, chart_height: int = 600
) -> None:
    """
    Display availability breakdown by department and team.

    Args:
        capacity_data: DataFrame containing resource allocation data
        chart_height: Height of the chart in pixels
    """
    if capacity_data.empty or "Department" not in capacity_data.columns:
        return

    st.subheader("Department & Team Availability")

    # Calculate average allocation by department
    dept_allocation = (
        capacity_data.groupby("Department")["Allocation"].mean().reset_index()
    )
    dept_allocation["Availability"] = 100 - dept_allocation["Allocation"]
    dept_allocation = dept_allocation.sort_values("Availability", ascending=False)

    # Get department colors
    dept_colors = load_department_colors()

    # Create color map for departments
    color_map = {
        dept: color
        for dept, color in dept_colors.items()
        if dept in dept_allocation["Department"].values
    }

    # Create two-column layout
    col1, col2 = st.columns(2)

    with col1:
        # Create horizontal bar chart for department availability
        fig1 = px.bar(
            dept_allocation,
            x="Availability",
            y="Department",
            orientation="h",
            title="Availability by Department",
            color="Department",
            color_discrete_map=color_map,
            labels={"Availability": "Availability %", "Department": "Department"},
            text_auto=".1f",
            height=chart_height,
        )

        # Update text to show percentages
        fig1.update_traces(
            texttemplate="%{x:.1f}%",
            textposition="outside",
        )

        # Add vertical reference lines
        fig1.add_vline(
            x=30,
            line_width=1,
            line_dash="dash",
            line_color="rgba(244,67,54,0.7)",
            annotation=dict(
                text="Low",
                showarrow=False,
                font=dict(color="rgba(244,67,54,0.7)"),
                xanchor="left",
            ),
        )
        fig1.add_vline(
            x=70,
            line_width=1,
            line_dash="dash",
            line_color="rgba(76,175,80,0.7)",
            annotation=dict(
                text="High",
                showarrow=False,
                font=dict(color="rgba(76,175,80,0.7)"),
                xanchor="right",
            ),
        )

        # Update layout
        fig1.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(
                range=[0, 100],
                gridcolor="rgba(128,128,128,0.2)",
                ticksuffix="%",
            ),
            yaxis=dict(
                gridcolor="rgba(128,128,128,0.2)",
            ),
            margin=dict(l=10, r=10, t=40, b=40),
            showlegend=False,
        )

        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        # Check if "Team" column exists in the data
        if "Team" in capacity_data.columns:
            # Filter for resources that have team assignments
            # We'll use fillna with an empty string to avoid dropping rows
            team_data = capacity_data.copy()
            team_data["Team"] = team_data["Team"].fillna("")
            team_data = team_data[team_data["Team"] != ""]

            if not team_data.empty and team_data["Team"].nunique() > 0:
                # Calculate team availability by grouping
                team_allocation = (
                    team_data.groupby(["Department", "Team"])["Allocation"]
                    .mean()
                    .reset_index()
                )
                team_allocation["Availability"] = 100 - team_allocation["Allocation"]
                team_allocation = team_allocation.sort_values(
                    "Availability", ascending=False
                )

                # Create team availability chart colored by department
                fig2 = px.bar(
                    team_allocation,
                    x="Availability",
                    y="Team",
                    orientation="h",
                    title="Availability by Team",
                    color="Department",
                    color_discrete_map=color_map,
                    labels={"Availability": "Availability %", "Team": "Team"},
                    text_auto=".1f",
                    height=chart_height,
                )

                # Update text to show percentages
                fig2.update_traces(
                    texttemplate="%{x:.1f}%",
                    textposition="outside",
                )

                # Add vertical reference lines
                fig2.add_vline(
                    x=30,
                    line_width=1,
                    line_dash="dash",
                    line_color="rgba(244,67,54,0.7)",
                )
                fig2.add_vline(
                    x=70,
                    line_width=1,
                    line_dash="dash",
                    line_color="rgba(76,175,80,0.7)",
                )

                # Update layout
                fig2.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    xaxis=dict(
                        range=[0, 100],
                        gridcolor="rgba(128,128,128,0.2)",
                        ticksuffix="%",
                    ),
                    yaxis=dict(
                        gridcolor="rgba(128,128,128,0.2)",
                    ),
                    margin=dict(l=10, r=10, t=40, b=40),
                )

                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info(
                    "No team data available for display. Resources may not have team assignments."
                )
        else:
            if "Type" in capacity_data.columns:
                type_allocation = (
                    capacity_data.groupby("Type")["Allocation"].mean().reset_index()
                )
                type_allocation["Availability"] = 100 - type_allocation["Allocation"]
                type_allocation = type_allocation.sort_values(
                    "Availability", ascending=False
                )

                # Create type availability chart
                fig2 = px.bar(
                    type_allocation,
                    x="Availability",
                    y="Type",
                    orientation="h",
                    title="Availability by Resource Type",
                    color="Type",
                    color_discrete_map={
                        "Person": "#2196F3",
                        "Team": "#FF9800",
                        "Department": "#4CAF50",
                    },
                    labels={"Availability": "Availability %", "Type": "Resource Type"},
                    text_auto=".1f",
                    height=chart_height,
                )

                # Update text to show percentages
                fig2.update_traces(
                    texttemplate="%{x:.1f}%",
                    textposition="outside",
                )

                # Add vertical reference lines
                fig2.add_vline(
                    x=30,
                    line_width=1,
                    line_dash="dash",
                    line_color="rgba(244,67,54,0.7)",
                )
                fig2.add_vline(
                    x=70,
                    line_width=1,
                    line_dash="dash",
                    line_color="rgba(76,175,80,0.7)",
                )

                # Update layout
                fig2.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    xaxis=dict(
                        range=[0, 100],
                        gridcolor="rgba(128,128,128,0.2)",
                        ticksuffix="%",
                    ),
                    yaxis=dict(
                        gridcolor="rgba(128,128,128,0.2)",
                    ),
                    margin=dict(l=10, r=10, t=40, b=40),
                    showlegend=False,
                )

                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("No team or resource type data available for display.")


def display_capacity_forecast(
    capacity_data: pd.DataFrame,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
    chart_height: int = 600,
) -> None:
    """
    Display capacity forecast visualization showing upcoming resource availability.

    Args:
        capacity_data: DataFrame containing resource allocation data
        start_date: Start date for the visualization
        end_date: End date for the visualization
        chart_height: Height of the chart in pixels
    """
    if capacity_data.empty:
        return

    st.subheader("Resource Capacity Forecast")

    # Calculate total capacity and used capacity by date
    resource_count = capacity_data.groupby("Date")["Resource"].nunique()
    daily_allocations = capacity_data.groupby("Date")["Allocation"].sum()

    # Each resource has 100% capacity, so total daily capacity is resource_count * 100
    daily_capacity = resource_count * 100

    # Calculate available capacity (total - used)
    available_capacity = daily_capacity - daily_allocations
    available_capacity_pct = available_capacity / daily_capacity * 100

    # Create forecast dataframe
    forecast_df = pd.DataFrame(
        {
            "Date": available_capacity.index,
            "Available Capacity (person-%)": available_capacity.values,
            "Available Capacity %": available_capacity_pct.values,
            "Resource Count": resource_count.values,
        }
    )

    # Create area chart for available capacity
    fig = go.Figure()

    # Add total capacity area
    fig.add_trace(
        go.Scatter(
            x=forecast_df["Date"],
            y=daily_capacity.values,
            fill=None,
            mode="lines",
            line=dict(width=0, color="rgba(33, 150, 243, 0.1)"),
            showlegend=False,
            hoverinfo="skip",
        )
    )

    # Add used capacity area
    fig.add_trace(
        go.Scatter(
            x=forecast_df["Date"],
            y=available_capacity.values,
            fill="tonexty",
            mode="lines",
            line=dict(width=0),
            fillcolor="rgba(244, 67, 54, 0.2)",
            name="Allocated Capacity",
            hovertemplate="%{x|%b %d, %Y}<br>Allocated: %{customdata:.1f}%<extra></extra>",
            customdata=100 - available_capacity_pct.values,
        )
    )

    # Add available capacity area
    fig.add_trace(
        go.Scatter(
            x=forecast_df["Date"],
            y=[0] * len(forecast_df),
            fill="tonexty",
            mode="lines",
            line=dict(width=0),
            fillcolor="rgba(76, 175, 80, 0.2)",
            name="Available Capacity",
            hovertemplate="%{x|%b %d, %Y}<br>Available: %{customdata:.1f}%<extra></extra>",
            customdata=available_capacity_pct.values,
        )
    )

    # Add line for available capacity percentage
    fig.add_trace(
        go.Scatter(
            x=forecast_df["Date"],
            y=available_capacity_pct.values,
            mode="lines",
            line=dict(color="#4CAF50", width=3),
            name="Available Capacity %",
            yaxis="y2",
            hovertemplate="%{x|%b %d, %Y}<br>Available: %{y:.1f}%<extra></extra>",
        )
    )

    # Update layout with dual y-axis
    fig.update_layout(
        title="Resource Capacity Forecast",
        xaxis_title="Date",
        yaxis=dict(
            title="Capacity (person-%)",
            gridcolor="rgba(128,128,128,0.2)",
        ),
        yaxis2=dict(
            title=dict(  # Fix: Use title dict with font property instead of titlefont
                text="Available Capacity %", font=dict(color="#4CAF50")
            ),
            tickfont=dict(color="#4CAF50"),
            anchor="x",
            overlaying="y",
            side="right",
            range=[0, 100],
            gridcolor="rgba(0,0,0,0)",
            ticksuffix="%",
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=40, b=40),
        height=chart_height,
        hovermode="x unified",
    )

    st.plotly_chart(fig, use_container_width=True)

    # Add explanation for the capacity forecast
    with st.expander("ℹ️ Understanding the Capacity Forecast", expanded=False):
        st.markdown(
            """
        <div style="background-color:rgba(0,188,212,0.1); border-left:3px solid #00BCD4; padding:10px; border-radius:2px;">
        <p><strong>Understanding the Capacity Forecast:</strong></p>
        <ul>
            <li>The <strong>green area</strong> represents available capacity that can be allocated to new work</li>
            <li>The <strong>red area</strong> shows already allocated capacity</li>
            <li>The <strong>green line</strong> indicates the percentage of total capacity that is available</li>
        </ul>
        <p><strong>Note:</strong> The capacity is measured in person-percentages. For example, if there are 10 resources and each has 100% capacity, the total daily capacity is 1000 person-%.</p>
        <p>This chart helps you identify periods with higher available capacity for planning new projects or tasks.</p>
        </div>
        """,
            unsafe_allow_html=True,
        )


def display_resource_calendar_tab():
    """Display the resource calendar tab."""
    display_action_bar()
    st.subheader("Resource Calendar")

    if not st.session_state.data["projects"]:
        st.warning("No projects found. Please add projects first.")
        return
    elif not (
        st.session_state.data["people"]
        or st.session_state.data["teams"]
        or st.session_state.data["departments"]
    ):
        st.warning(
            "No resources found. Please add people, teams, or departments first."
        )
        return

    # Get filters using the standardized filter component
    filters = create_resource_analytics_filters("calendar")

    # Create and filter data
    gantt_data = create_gantt_data(
        st.session_state.data["projects"], st.session_state.data
    )

    # Apply filters
    filtered_data = apply_filters(gantt_data, filters)

    # Extract date range
    start_date = filters["date_range"][0]
    end_date = filters["date_range"][1]

    # Display the calendar with filtered data
    if filtered_data.empty:
        st.warning("No data matches your filter criteria. Try adjusting the filters.")
    else:
        display_enhanced_resource_calendar(filtered_data, start_date, end_date)


def display_enhanced_resource_calendar(
    filtered_data: pd.DataFrame, start_date: pd.Timestamp, end_date: pd.Timestamp
) -> None:
    """
    Display an enhanced calendar view of resource allocations with summary metrics and visualizations.

    Args:
        filtered_data: Filtered DataFrame of resource allocation data
        start_date: Start date for the visualization
        end_date: End date for the visualization
    """
    # Get chart height from display preferences
    display_prefs = load_display_preferences()
    chart_height = display_prefs.get("chart_height", 600)

    if filtered_data.empty:
        st.info("No data available for the calendar view with current filters.")
        return

    # Get unique resources and create a multiselect or selectbox depending on number of resources
    resources = filtered_data["Resource"].unique()

    # Display calendar summary metrics
    st.subheader("Calendar Summary Metrics")
    display_calendar_summary_metrics(filtered_data, start_date, end_date)

    # Display allocation pattern analysis
    st.subheader("Allocation Pattern Analysis")
    display_allocation_patterns(filtered_data, start_date, end_date, chart_height)

    # Display time-based metrics visualization
    st.subheader("Weekly Allocation Patterns")
    display_weekly_allocation_patterns(filtered_data, chart_height)

    # Resource selection for detailed calendar view
    st.subheader("Resource Calendar View")

    # Enhanced resource selection with indicators
    if len(resources) > 10:
        # For many resources, show a multiselect with limit
        selected_resource = st.selectbox(
            "Select Resource for Detailed Calendar",
            options=resources,
            key="calendar_resource_detailed",
            format_func=lambda x: f"{x} ({filtered_data[filtered_data['Resource'] == x]['Allocation %'].mean():.0f}% avg)",
        )
        selected_resources = [selected_resource]
    else:
        # For fewer resources, allow multi-select
        selected_resources = st.multiselect(
            "Select Resources for Calendar View (up to 3)",
            options=resources,
            default=[resources[0]],
            max_selections=3,
            key="calendar_resources_multi",
            format_func=lambda x: f"{x} ({filtered_data[filtered_data['Resource'] == x]['Allocation %'].mean():.0f}% avg)",
        )

        if not selected_resources:
            st.info("Please select at least one resource to view the calendar.")
            return

    # Calendar view options
    col1, col2 = st.columns([1, 1])
    with col1:
        view_mode = st.radio(
            "Calendar View Mode",
            options=["Monthly", "Weekly", "Daily"],
            horizontal=True,
            index=0,
            key="calendar_view_mode",
        )

    with col2:
        show_project_colors = st.checkbox(
            "Show Project Colors", value=True, key="calendar_show_colors"
        )
        show_details = st.checkbox(
            "Show Detailed Allocations", value=True, key="calendar_show_details"
        )

    # Display the enhanced calendar for selected resources
    display_enhanced_calendar_view(
        filtered_data,
        selected_resources,
        start_date,
        end_date,
        view_mode,
        show_project_colors,
        show_details,
    )


def display_calendar_summary_metrics(
    filtered_data: pd.DataFrame, start_date: pd.Timestamp, end_date: pd.Timestamp
) -> None:
    """
    Display calendar-specific summary metrics.

    Args:
        filtered_data: Filtered DataFrame of resource allocation data
        start_date: Start date for the visualization
        end_date: End date for the visualization
    """
    if filtered_data.empty:
        return

    # Calculate metrics specific to calendar analysis
    total_resources = filtered_data["Resource"].nunique()

    # Calculate the total duration in the selected range
    date_range = pd.date_range(start=start_date, end=end_date)
    total_days = len(date_range)

    # Calculate working days (Mon-Fri) in the range
    working_days = sum(1 for d in date_range if d.weekday() < 5)

    # Create a daily allocation table
    daily_allocation = {}
    max_daily_allocation = 0
    busiest_date = None

    for date in date_range:
        # Filter assignments for this date
        date_assignments = filtered_data[
            (filtered_data["Start"] <= date) & (filtered_data["End"] >= date)
        ]

        # Count resources allocated on this date
        resources_allocated = date_assignments["Resource"].nunique()
        daily_allocation[date] = resources_allocated

        # Track busiest date
        if resources_allocated > max_daily_allocation:
            max_daily_allocation = resources_allocated
            busiest_date = date

    # Calculate metrics
    total_allocated_days = sum(daily_allocation.values())
    avg_daily_resources = total_allocated_days / total_days if total_days > 0 else 0
    allocation_coverage = (
        len([v for v in daily_allocation.values() if v > 0]) / total_days * 100
        if total_days > 0
        else 0
    )

    # Calculate weekend allocations percentage
    weekend_dates = [d for d in date_range if d.weekday() >= 5]
    weekend_allocation_count = sum(daily_allocation.get(d, 0) for d in weekend_dates)
    weekend_days = len(weekend_dates)
    weekend_allocation_pct = (
        weekend_allocation_count / total_allocated_days * 100
        if total_allocated_days > 0
        else 0
    )

    # Display metrics in columns
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Calendar Coverage",
            f"{allocation_coverage:.1f}%",
            help="Percentage of days in the selected range with at least one resource allocated",
        )

    with col2:
        busiest_date_str = busiest_date.strftime("%Y-%m-%d") if busiest_date else "N/A"
        st.metric(
            "Busiest Date",
            busiest_date_str,
            delta=f"{max_daily_allocation} resources" if busiest_date else None,
            help="Date with the highest number of allocated resources",
        )

    with col3:
        st.metric(
            "Avg Daily Resources",
            f"{avg_daily_resources:.1f}",
            help="Average number of resources allocated per day",
        )

    with col4:
        st.metric(
            "Weekend Allocations",
            f"{weekend_allocation_pct:.1f}%",
            help="Percentage of total resource allocations occurring on weekends",
        )


def display_allocation_patterns(
    filtered_data: pd.DataFrame,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
    chart_height: int = 600,
) -> None:
    """
    Display calendar-based allocation patterns visualization.

    Args:
        filtered_data: Filtered DataFrame of resource allocation data
        start_date: Start date for the visualization
        end_date: End date for the visualization
        chart_height: Height of the chart in pixels
    """
    if filtered_data.empty:
        return

    # Create a date range for analysis
    date_range = pd.date_range(start=start_date, end=end_date)

    # Create a list to store daily allocation counts
    allocation_by_day = []
    weekday_names = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]

    # Calculate allocations by day of week
    for date in date_range:
        date_assignments = filtered_data[
            (filtered_data["Start"] <= date) & (filtered_data["End"] >= date)
        ]

        allocation_by_day.append(
            {
                "Date": date,
                "WeekDay": weekday_names[date.weekday()],
                "WeekNumber": date.isocalendar()[1],  # ISO week number
                "MonthDay": date.day,
                "Month": date.strftime("%B"),
                "ResourceCount": date_assignments["Resource"].nunique(),
                "ProjectCount": date_assignments["Project"].nunique(),
                "TotalAllocation": date_assignments["Allocation %"].sum(),
            }
        )

    # Convert to DataFrame
    pattern_df = pd.DataFrame(allocation_by_day)

    if pattern_df.empty:
        st.info("No allocation data available for pattern analysis.")
        return

    # Create a compact 2-column layout for visualizations
    col1, col2 = st.columns(2)

    with col1:
        # Create a heatmap of resource allocation by day of week
        pivot_df = pattern_df.pivot_table(
            index="WeekNumber", columns="WeekDay", values="ResourceCount", aggfunc="sum"
        )

        # Reorder columns to have Monday first
        pivot_df = pivot_df[weekday_names]

        # Create heatmap
        fig1 = px.imshow(
            pivot_df,
            labels=dict(x="Day of Week", y="Week Number", color="Resource Count"),
            x=weekday_names,
            y=pivot_df.index,
            color_continuous_scale="YlGnBu",
            aspect="auto",
            title="Resource Allocation Heatmap by Day of Week",
        )

        # Adjust layout
        fig1.update_layout(
            height=chart_height,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(tickangle=-45),
            margin=dict(l=10, r=10, t=40, b=80),
        )

        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        # Create a bar chart of average allocation by day of week
        weekday_avg = (
            pattern_df.groupby("WeekDay")
            .agg({"ResourceCount": "mean", "ProjectCount": "mean"})
            .reset_index()
        )

        # Ensure proper ordering
        weekday_avg["WeekDay"] = pd.Categorical(
            weekday_avg["WeekDay"], categories=weekday_names, ordered=True
        )
        weekday_avg = weekday_avg.sort_values("WeekDay")

        # Create chart
        fig2 = go.Figure()

        # Add resource count bars
        fig2.add_trace(
            go.Bar(
                x=weekday_avg["WeekDay"],
                y=weekday_avg["ResourceCount"],
                name="Average Resources",
                marker_color="#42A5F5",  # Blue
                text=weekday_avg["ResourceCount"].round(1),
                textposition="outside",
            )
        )

        # Add project count as a line
        fig2.add_trace(
            go.Scatter(
                x=weekday_avg["WeekDay"],
                y=weekday_avg["ProjectCount"],
                mode="lines+markers",
                name="Average Projects",
                line=dict(color="#FF7043", width=3),  # Orange
                marker=dict(size=8),
                yaxis="y2",
            )
        )

        # Update layout with dual y-axis
        fig2.update_layout(
            title="Average Resources vs Projects by Day of Week",
            xaxis=dict(title="Day of Week"),
            yaxis=dict(
                title="Average Resources",
                gridcolor="rgba(128,128,128,0.2)",
            ),
            yaxis2=dict(
                title="Average Projects",
                overlaying="y",
                side="right",
                gridcolor="rgba(0,0,0,0)",
            ),
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
            ),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=chart_height,
            margin=dict(l=10, r=10, t=40, b=40),
        )

        st.plotly_chart(fig2, use_container_width=True)

    # Display pattern insights as an expander
    with st.expander("ℹ️ Understanding Allocation Patterns", expanded=False):
        st.markdown(
            """
            <div style="background-color:rgba(0,188,212,0.1); border-left:3px solid #00BCD4; padding:10px; border-radius:2px;">
            <p><strong>Understanding Allocation Patterns:</strong></p>
            <ul>
                <li>The <strong>Resource Allocation Heatmap</strong> shows resource allocation intensity across weeks and days.</li>
                <li>Darker colors indicate more resources allocated on those days.</li>
                <li>The <strong>Day of Week Analysis</strong> shows how resource and project allocations vary across the week.</li>
                <li>Look for patterns like higher allocations midweek or lower allocations on Mondays/Fridays.</li>
            </ul>
            <p><strong>Note:</strong> These patterns can help you schedule new work during historically less utilized days.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def display_weekly_allocation_patterns(
    filtered_data: pd.DataFrame, chart_height: int = 600
) -> None:
    """
    Display weekly allocation patterns to see how resource usage changes through the week.

    Args:
        filtered_data: Filtered DataFrame of resource allocation data
        chart_height: Height of the chart in pixels
    """
    if filtered_data.empty:
        return

    # Create a list to track daily allocations for all resources
    weekday_allocation_data = []

    # Get unique resources
    resources = filtered_data["Resource"].unique()

    # For each resource, calculate their average allocation by day of week
    for resource in resources:
        resource_data = filtered_data[filtered_data["Resource"] == resource]

        # Expand daily allocations
        start_dates = pd.to_datetime(resource_data["Start"])
        end_dates = pd.to_datetime(resource_data["End"])
        allocation_pcts = resource_data["Allocation %"]
        projects = resource_data["Project"]

        # For each assignment, add to the daily allocation table
        for start, end, allocation, project in zip(
            start_dates, end_dates, allocation_pcts, projects
        ):
            # Create a date range for this assignment
            days = pd.date_range(start=start, end=end)

            # Add each day's allocation
            for day in days:
                weekday = day.weekday()  # 0=Monday, 6=Sunday
                weekday_allocation_data.append(
                    {
                        "Resource": resource,
                        "WeekDay": weekday,
                        "WeekDayName": [
                            "Monday",
                            "Tuesday",
                            "Wednesday",
                            "Thursday",
                            "Friday",
                            "Saturday",
                            "Sunday",
                        ][weekday],
                        "Date": day,
                        "Allocation": allocation,
                        "Project": project,
                    }
                )

    # Convert to DataFrame
    weekly_pattern_df = pd.DataFrame(weekday_allocation_data)

    if weekly_pattern_df.empty:
        st.info("No data available for weekly allocation patterns.")
        return

    # Calculate average allocation by day of week for all resources
    avg_by_day = (
        weekly_pattern_df.groupby("WeekDayName")["Allocation"].mean().reset_index()
    )

    # Ensure correct order
    weekday_order = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    avg_by_day["WeekDayName"] = pd.Categorical(
        avg_by_day["WeekDayName"], categories=weekday_order, ordered=True
    )
    avg_by_day = avg_by_day.sort_values("WeekDayName")

    # Create areas for both weekday and weekend zones
    fig = go.Figure()

    # Add weekday/weekend zones
    fig.add_vrect(
        x0=-0.5,
        x1=4.5,
        fillcolor="rgba(220, 220, 220, 0.2)",
        layer="below",
        line_width=0,
        annotation=dict(
            text="Weekdays",
            x=2,
            y=1.05,
            showarrow=False,
            yref="paper",
            font=dict(size=12, color="rgba(100,100,100,0.7)"),
        ),
    )

    fig.add_vrect(
        x0=4.5,
        x1=6.5,
        fillcolor="rgba(255, 220, 200, 0.2)",
        layer="below",
        line_width=0,
        annotation=dict(
            text="Weekend",
            x=5.5,
            y=1.05,
            showarrow=False,
            yref="paper",
            font=dict(size=12, color="rgba(100,100,100,0.7)"),
        ),
    )

    # Add line chart
    fig.add_trace(
        go.Scatter(
            x=avg_by_day["WeekDayName"],
            y=avg_by_day["Allocation"],
            mode="lines+markers",
            line=dict(color="#2196F3", width=3),
            marker=dict(size=10),
            name="Average Allocation",
        )
    )

    # Calculate and add standard deviation as error bands
    std_by_day = (
        weekly_pattern_df.groupby("WeekDayName")["Allocation"].std().reset_index()
    )
    std_by_day["WeekDayName"] = pd.Categorical(
        std_by_day["WeekDayName"], categories=weekday_order, ordered=True
    )
    std_by_day = std_by_day.sort_values("WeekDayName")

    # Add upper band
    upper_band = avg_by_day["Allocation"] + std_by_day["Allocation"]
    fig.add_trace(
        go.Scatter(
            x=avg_by_day["WeekDayName"],
            y=upper_band,
            mode="lines",
            line=dict(width=0),
            showlegend=False,
            hoverinfo="skip",
        )
    )

    # Add lower band
    lower_band = avg_by_day["Allocation"] - std_by_day["Allocation"]
    lower_band = [max(0, val) for val in lower_band]  # Ensure no negative values

    fig.add_trace(
        go.Scatter(
            x=avg_by_day["WeekDayName"],
            y=lower_band,
            mode="lines",
            line=dict(width=0),
            fill="tonexty",
            fillcolor="rgba(33, 150, 243, 0.2)",
            showlegend=False,
            hoverinfo="skip",
        )
    )

    # Add reference line for 100% allocation
    fig.add_hline(
        y=100,
        line_dash="dash",
        line_color="rgba(255, 0, 0, 0.5)",
    )

    # Add annotation for the 100% line separately
    fig.add_annotation(
        text="100% Allocation",
        x=1,
        y=100,
        xref="paper",
        yref="y",
        showarrow=False,
        font=dict(color="red"),
        align="right",
        xanchor="right",
    )

    # Update layout
    fig.update_layout(
        title="Average Resource Allocation by Day of Week",
        xaxis_title="Day of Week",
        yaxis_title="Average Allocation (%)",
        yaxis=dict(
            gridcolor="rgba(128,128,128,0.2)",
            range=[0, max(150, upper_band.max() * 1.1)],
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=chart_height,
        margin=dict(l=10, r=10, t=40, b=40),
        hovermode="x unified",
    )

    st.plotly_chart(fig, use_container_width=True)

    # Create two columns for additional metrics
    col1, col2 = st.columns(2)

    with col1:
        # Calculate highest and lowest allocation days
        max_idx = avg_by_day["Allocation"].idxmax()
        min_idx = avg_by_day["Allocation"].idxmin()

        max_day = avg_by_day.iloc[max_idx]["WeekDayName"]
        min_day = avg_by_day.iloc[min_idx]["WeekDayName"]

        max_alloc = avg_by_day.iloc[max_idx]["Allocation"]
        min_alloc = avg_by_day.iloc[min_idx]["Allocation"]

        # Create metrics card
        st.markdown(
            f"""
            <div style="border:1px solid rgba(128,128,128,0.2); border-radius:5px; padding:10px; margin-bottom:10px;">
            <h4 style="margin-top:0;">Weekly Pattern Insights</h4>
            <p><strong>Highest Allocation Day:</strong> {max_day} ({max_alloc:.1f}%)</p>
            <p><strong>Lowest Allocation Day:</strong> {min_day} ({min_alloc:.1f}%)</p>
            <p><strong>Weekday/Weekend Ratio:</strong> {avg_by_day.iloc[:5]["Allocation"].mean():.1f}% / {avg_by_day.iloc[5:]["Allocation"].mean():.1f}%</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        # Calculate resource allocation stability
        resource_stability = []

        for resource in resources:
            resource_data = weekly_pattern_df[weekly_pattern_df["Resource"] == resource]

            if len(resource_data) >= 5:  # Only if we have enough data points
                weekday_avg = resource_data.groupby("WeekDayName")["Allocation"].mean()

                # Calculate coefficient of variation as measure of stability
                stability = (
                    weekday_avg.std() / weekday_avg.mean()
                    if weekday_avg.mean() > 0
                    else 0
                )

                # Lower values indicate more stable allocation across weekdays
                resource_stability.append(
                    {
                        "Resource": resource,
                        "StabilityScore": 100
                        * (
                            1 - min(stability, 1)
                        ),  # Convert to 0-100 score, higher is more stable
                        "AvgAllocation": resource_data["Allocation"].mean(),
                    }
                )

        if resource_stability:
            stability_df = pd.DataFrame(resource_stability)
            stability_df = stability_df.sort_values(
                "StabilityScore", ascending=False
            ).head(5)

            # Create metrics card
            st.markdown(
                f"""
                <div style="border:1px solid rgba(128,128,128,0.2); border-radius:5px; padding:10px;">
                <h4 style="margin-top:0;">Most Consistent Resources</h4>
                <p>Resources with the most stable weekly allocation patterns:</p>
                <ol style="margin-left:20px; padding-left:0;">
                {"".join([f"<li><strong>{row['Resource']}</strong> - Stability: {row['StabilityScore']:.1f}%, Avg: {row['AvgAllocation']:.1f}%</li>" for _, row in stability_df.iterrows()])}
                </ol>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.info("Not enough data to calculate resource stability.")


def display_enhanced_calendar_view(
    filtered_data: pd.DataFrame,
    selected_resources: List[str],
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
    view_mode: str = "Monthly",
    show_project_colors: bool = True,
    show_details: bool = True,
) -> None:
    """
    Display an enhanced calendar view with better visual design.

    Args:
        filtered_data: Filtered DataFrame of resource allocation data
        selected_resources: List of selected resources to display
        start_date: Start date for the visualization
        end_date: End date for the visualization
        view_mode: View mode (Monthly, Weekly, Daily)
        show_project_colors: Whether to show project colors
        show_details: Whether to show detailed allocations
    """
    if not selected_resources:
        st.info("Please select at least one resource to view the calendar.")
        return

    # Define date ranges based on view mode
    if view_mode == "Monthly":
        # Group by month
        date_groups = pd.date_range(
            start=start_date.replace(day=1),
            end=end_date + pd.DateOffset(months=1),
            freq="MS",
        )
        group_format = "%B %Y"  # Month and year format
    elif view_mode == "Weekly":
        # Group by week
        date_groups = pd.date_range(
            start=start_date
            - pd.DateOffset(days=start_date.weekday()),  # Start from Monday
            end=end_date + pd.DateOffset(days=6),
            freq="W-MON",  # Weekly starting from Monday
        )
        group_format = "Week of %b %d, %Y"  # Week of Month day, Year
    else:  # Daily view
        # No grouping, just show current date
        date_groups = [start_date]  # We'll handle the iteration differently
        group_format = "%A, %b %d, %Y"  # Day of Week, Month day, Year

    # Get unique projects for color mapping
    projects = filtered_data["Project"].unique()
    color_map = {
        project: f"hsl({hash(project) % 360}, 70%, 50%)" for project in projects
    }

    # Create data processing for each resource
    for resource in selected_resources:
        resource_data = filtered_data[filtered_data["Resource"] == resource]

        # Determine resource type and average allocation
        resource_type = (
            resource_data["Type"].iloc[0] if not resource_data.empty else "Unknown"
        )
        avg_allocation = (
            resource_data["Allocation %"].mean() if not resource_data.empty else 0
        )

        # Display resource header
        st.markdown(
            f"""
            <div style="
                padding: 10px;
                border-radius: 5px;
                margin-bottom: 10px;
                background-color: rgba(33, 150, 243, 0.1);
                border-left: 5px solid #2196F3;
                display: flex;
                justify-content: space-between;
                align-items: center;
            ">
                <div>
                    <h4 style="margin:0;">{resource} ({resource_type})</h4>
                    <p style="margin:5px 0 0 0; font-size:0.9em; opacity:0.8;">
                        Average Allocation: {avg_allocation:.1f}% | 
                        Projects: {resource_data["Project"].nunique()} | 
                        Date Range: {resource_data["Start"].min().strftime("%b %d")} - {resource_data["End"].max().strftime("%b %d")}
                    </p>
                </div>
                <div style="text-align:right; font-size:1.2em; font-weight:bold;">
                    {_get_allocation_indicator(avg_allocation)}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Process and display each date group
        if view_mode == "Daily":
            # For daily view, we show a single week at a time with a date picker
            selected_date = pd.to_datetime(
                st.date_input(
                    "Select date to view",
                    value=start_date,
                    min_value=start_date.date(),
                    max_value=end_date.date(),
                )
            )

            # Calculate the start of week (Monday)
            week_start = selected_date - pd.DateOffset(days=selected_date.weekday())
            week_end = week_start + pd.DateOffset(days=6)

            # Display single week
            st.markdown(f"**Week of {week_start.strftime('%b %d, %Y')}**")
            _display_calendar_week(
                resource_data,
                week_start,
                week_end,
                color_map,
                show_project_colors,
                show_details,
            )
        else:
            # For Monthly or Weekly views
            for i in range(len(date_groups) - 1):
                group_start = date_groups[i]
                group_end = date_groups[i + 1] - pd.DateOffset(
                    days=1
                )  # Last day of the period

                # Skip if the group is outside our range
                if group_end < start_date or group_start > end_date:
                    continue

                with st.expander(
                    group_start.strftime(group_format),
                    expanded=(i == 0),  # Expand only the first group
                ):
                    if view_mode == "Monthly":
                        # Display month calendar (grouped by weeks)
                        month_start = group_start

                        # Calculate weeks in the month
                        week_starts = pd.date_range(
                            start=month_start,
                            end=group_end + pd.DateOffset(days=1),
                            freq="W-MON",
                        )

                        # Add the first day of the month if it's not a Monday
                        if month_start.weekday() != 0:  # Not Monday
                            week_starts = (
                                pd.DatetimeIndex([month_start])
                                .append(week_starts)
                                .sort_values()
                            )

                        # Display each week
                        for j in range(len(week_starts)):
                            week_start = week_starts[j]

                            # Calculate end of week (Sunday) or end of month
                            if j < len(week_starts) - 1:
                                week_end = week_starts[j + 1] - pd.DateOffset(days=1)
                            else:
                                week_end = group_end

                            # Skip if the week is outside our range
                            if week_end < start_date or week_start > end_date:
                                continue

                            # Display the week
                            _display_calendar_week(
                                resource_data,
                                week_start,
                                week_end,
                                color_map,
                                show_project_colors,
                                show_details,
                            )
                    else:  # Weekly view
                        # Display single week
                        _display_calendar_week(
                            resource_data,
                            group_start,
                            group_end,
                            color_map,
                            show_project_colors,
                            show_details,
                        )


def _display_calendar_week(
    resource_data: pd.DataFrame,
    week_start: pd.Timestamp,
    week_end: pd.Timestamp,
    color_map: Dict[str, str],
    show_project_colors: bool = True,
    show_details: bool = True,
) -> None:
    """
    Display a single week in the calendar.

    Args:
        resource_data: DataFrame containing resource allocation data
        week_start: Start date of the week (Monday)
        week_end: End date of the week (Sunday)
        color_map: Dictionary mapping projects to colors
        show_project_colors: Whether to show project colors
        show_details: Whether to show detailed allocations
    """
    # Create a list of days in the week
    days = pd.date_range(start=week_start, end=week_end)
    weekday_names = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]

    # Create a list to store HTML for each day
    day_cells = []

    # Helper function to escape HTML special characters
    def escape_html(text):
        """Escape HTML special characters to prevent HTML injection."""
        if isinstance(text, str):
            return (
                text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&#39;")
            )
        return text

    for day in days:
        day_str = day.strftime("%a, %b %d")
        is_weekend = day.weekday() >= 5

        # Filter assignments for this day
        day_assignments = resource_data[
            (resource_data["Start"] <= day) & (resource_data["End"] >= day)
        ]

        if day_assignments.empty:
            # Empty day - improved styling for both themes
            # Use more neutral colors that work in both themes
            bgcolor = "rgba(240,240,240,0.3)" if is_weekend else "rgba(255,255,255,0.1)"
            border_style = "1px solid rgba(200,200,200,0.4)"

            day_cells.append(
                f'<td style="border:{border_style}; background-color:{bgcolor}; width:14%; vertical-align:top; box-shadow: inset 0 0 2px rgba(0,0,0,0.1);"><div style="padding:8px; min-height:100px;"><div style="margin-bottom:8px; font-weight:bold;">{day_str}</div><div style="color:rgba(150,150,150,0.8); text-align:center; margin-top:30px; font-style:italic;">No allocation</div></div></td>'
            )
        else:
            # Day with assignments
            total_allocation = day_assignments["Allocation %"].sum()
            bgcolor = _get_allocation_color(total_allocation / 100)

            if is_weekend:
                # Apply a subtle blend for weekends
                bgcolor = _blend_colors(bgcolor, "rgba(220,220,220,0.15)", 0.2)

            # Enhanced border with better visibility
            border_style = "1px solid rgba(180,180,180,0.5)"

            # Sort assignments by allocation percentage (descending)
            day_assignments = day_assignments.sort_values(
                "Allocation %", ascending=False
            )

            # Create project segments with improved styling
            project_segments = []
            for _, row in day_assignments.iterrows():
                # Escape project name to prevent HTML injection
                project = escape_html(row["Project"])
                allocation = row["Allocation %"]

                if show_project_colors:
                    base_color = color_map.get(project, "#808080")
                    # Enhance color for better visibility
                    color = _enhance_color_contrast(base_color)
                else:
                    # Use a color based on allocation level with enhanced contrast
                    color = _get_allocation_color(
                        allocation / 100, enhance_contrast=True
                    )

                if show_details:
                    # Improved text contrast and padding
                    text_color = _get_contrasting_text_color(color)
                    project_segments.append(
                        f'<div style="margin-bottom:6px; border-radius:4px; padding:6px; background-color:{color}; color:{text_color}; box-shadow:0 1px 2px rgba(0,0,0,0.1);"><div style="font-weight:bold; font-size:0.9em; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;" title="{project}">{project}</div><div style="font-size:0.8em; margin-top:2px;">{allocation:.0f}%</div></div>'
                    )
                else:
                    # Simplified view with better visibility
                    height = max(
                        8, min(35, allocation / 5)
                    )  # Slightly larger height for better visibility
                    project_segments.append(
                        f'<div style="margin-bottom:3px; border-radius:3px; height:{height}px; background-color:{color}; box-shadow:0 1px 2px rgba(0,0,0,0.15);" title="{project}: {allocation:.0f}%"></div>'
                    )

            # Create day cell with improved header styling
            alloc_color = _get_allocation_text_color(total_allocation)
            day_cells.append(
                f'<td style="border:{border_style}; background-color:{bgcolor}; width:14%; vertical-align:top; box-shadow: inset 0 0 3px rgba(0,0,0,0.1);"><div style="padding:8px; min-height:100px;"><div style="display:flex; justify-content:space-between; margin-bottom:8px; border-bottom:1px solid rgba(180,180,180,0.2); padding-bottom:4px;"><span style="font-weight:bold;">{day_str}</span><span style="font-weight:bold; color:{alloc_color};">{total_allocation:.0f}%</span></div>{"".join(project_segments)}</div></td>'
            )

    # Enhanced table styling with better spacing and borders
    header_row = "".join(
        [
            f'<th style="padding:6px; background-color:rgba(100,100,100,0.1); border-bottom:2px solid rgba(150,150,150,0.4);">{day}</th>'
            for day in weekday_names
        ]
    )
    data_row = "".join(day_cells)

    # Use a more compact HTML format with improved container styling
    calendar_html = f'<div class="calendar-container" style="border-radius:5px; overflow:hidden; box-shadow:0 2px 8px rgba(0,0,0,0.1);"><table style="width:100%; border-collapse:collapse; table-layout:fixed; border:1px solid rgba(180,180,180,0.4);"><thead><tr>{header_row}</tr></thead><tbody><tr>{data_row}</tr></tbody></table></div>'

    # Display the calendar
    st.markdown(calendar_html, unsafe_allow_html=True)


def _get_allocation_indicator(allocation: float) -> str:
    """
    Get an emoji indicator based on allocation percentage.

    Args:
        allocation: Allocation percentage

    Returns:
        Emoji indicator string
    """
    if allocation < 25:
        return "🟢 Very Low"
    elif allocation < 50:
        return "🟢 Low"
    elif allocation < 70:
        return "🟡 Moderate"
    elif allocation < 90:
        return "🟡 Good"
    elif allocation <= 100:
        return "🟠 High"
    else:
        return "🔴 Overallocated"


def _get_allocation_color(allocation: float, enhance_contrast: bool = False) -> str:
    """
    Get a color based on allocation percentage with improved contrast for dark theme.

    Args:
        allocation: Allocation as a decimal (0.0 to 1.0+)
        enhance_contrast: Whether to enhance contrast for dark theme

    Returns:
        Hex color code
    """
    # Updated colors for better visibility in both light and dark themes
    if allocation < 0.25:
        return (
            "#1a75ff" if enhance_contrast else "rgba(25, 118, 210, 0.3)"
        )  # More visible blue
    elif allocation < 0.5:
        return (
            "#33cc33" if enhance_contrast else "rgba(46, 174, 79, 0.3)"
        )  # More visible green
    elif allocation < 0.7:
        return (
            "#33bbff" if enhance_contrast else "rgba(51, 187, 255, 0.4)"
        )  # Brighter blue
    elif allocation < 0.9:
        return (
            "#ffcc00" if enhance_contrast else "rgba(255, 204, 0, 0.4)"
        )  # Brighter yellow
    elif allocation <= 1.0:
        return (
            "#ff6666" if enhance_contrast else "rgba(255, 102, 102, 0.4)"
        )  # Brighter red
    else:
        return (
            "#ff3300" if enhance_contrast else "rgba(255, 51, 0, 0.6)"
        )  # Vivid orange-red for overallocation


def _get_contrasting_text_color(bg_color: str) -> str:
    """
    Get a contrasting text color (black or white) based on background color.

    Args:
        bg_color: Background color in hex format

    Returns:
        Text color (black or white) for optimal contrast
    """
    # If color is in rgba format, extract the RGB components
    if bg_color.startswith("rgba"):
        # Parse rgba format
        parts = bg_color.strip("rgba()").split(",")
        r, g, b = int(parts[0]), int(parts[1]), int(parts[2])
    elif bg_color.startswith("#"):
        # Parse hex format
        bg_color = bg_color.lstrip("#")
        if len(bg_color) == 3:  # Short hex format (e.g., #ABC)
            bg_color = "".join([c * 2 for c in bg_color])
        r = int(bg_color[0:2], 16)
        g = int(bg_color[2:4], 16)
        b = int(bg_color[4:6], 16)
    else:
        # Default to white text for unknown format
        return "#ffffff"

    # Calculate luminance - standard formula for perceived brightness
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255

    # Return black for light backgrounds, white for dark backgrounds
    return "#000000" if luminance > 0.55 else "#ffffff"


def _get_allocation_text_color(allocation: float) -> str:
    """
    Get a color for allocation text based on allocation percentage.

    Args:
        allocation: Allocation percentage

    Returns:
        Text color for the allocation percentage
    """
    if allocation < 50:
        return "#2196F3"  # Blue for low allocation
    elif allocation <= 90:
        return "#4CAF50"  # Green for medium allocation
    elif allocation <= 100:
        return "#FF9800"  # Orange for high allocation
    else:
        return "#F44336"  # Red for overallocation


def _enhance_color_contrast(color: str) -> str:
    """
    Enhance color contrast for better visibility in both themes.

    Args:
        color: Original color in hex format

    Returns:
        Enhanced color with better contrast
    """
    # If color is already in rgba format, return it
    if color.startswith("rgba"):
        return color

    # Parse hex format
    if color.startswith("#"):
        color = color.lstrip("#")
        if len(color) == 3:  # Short hex format (e.g., #ABC)
            color = "".join([c * 2 for c in color])
        r = int(color[0:2], 16)
        g = int(color[2:4], 16)
        b = int(color[4:6], 16)
    else:
        # Default color for unknown format
        return "#4285F4"

    # Calculate luminance
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255

    # Enhance saturation and brightness for better visibility
    # Increase saturation for pale colors
    import colorsys

    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)

    if s < 0.4:  # For less saturated colors
        s = min(1.0, s * 1.5)  # Increase saturation

    if v < 0.6:  # For darker colors
        v = min(1.0, v * 1.3)  # Brighten
    elif v > 0.9 and luminance > 0.7:  # For very light colors
        v = max(0.5, v * 0.85)  # Darken slightly for better visibility
        s = min(1.0, s * 1.3)  # Increase saturation

    r, g, b = [int(x * 255) for x in colorsys.hsv_to_rgb(h, s, v)]

    # Return enhanced color
    return f"#{r:02x}{g:02x}{b:02x}"


def _blend_colors(color1: str, color2: str, amount: float) -> str:
    """
    Blend two colors - updated for rgba support.

    Args:
        color1: First color (hex or rgba)
        color2: Second color (hex or rgba)
        amount: Blend amount (0.0 to 1.0) - how much of color2 to blend into color1

    Returns:
        Blended color
    """
    # Parse the first color
    if color1.startswith("rgba"):
        # Parse rgba format
        parts = color1.strip("rgba()").split(",")
        r1 = int(parts[0])
        g1 = int(parts[1])
        b1 = int(parts[2])
        a1 = float(parts[3]) if len(parts) > 3 else 1.0
    else:
        # Convert hex to RGB
        rgb1 = _hex_to_rgb(color1)
        r1, g1, b1 = rgb1
        a1 = 1.0

    # Parse the second color
    if color2.startswith("rgba"):
        # Parse rgba format
        parts = color2.strip("rgba()").split(",")
        r2 = int(parts[0])
        g2 = int(parts[1])
        b2 = int(parts[2])
        a2 = float(parts[3]) if len(parts) > 3 else 1.0
    else:
        # Convert hex to RGB
        rgb2 = _hex_to_rgb(color2)
        r2, g2, b2 = rgb2
        a2 = 1.0

    # Blend the colors
    r = int(r1 * (1 - amount) + r2 * amount)
    g = int(g1 * (1 - amount) + g2 * amount)
    b = int(b1 * (1 - amount) + b2 * amount)
    a = a1 * (1 - amount) + a2 * amount

    # Return as rgba for better theme compatibility
    return f"rgba({r},{g},{b},{a:.2f})"


def _hex_to_rgb(hex_color: str) -> tuple:
    """
    Convert hex color to RGB tuple.

    Args:
        hex_color: Hex color string

    Returns:
        RGB tuple (r, g, b)
    """
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join([c * 2 for c in hex_color])
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def display_resource_calendar(
    filtered_data: pd.DataFrame, start_date: pd.Timestamp, end_date: pd.Timestamp
) -> None:
    """
    Display the legacy calendar view (kept for backward compatibility).

    Args:
        filtered_data: Filtered DataFrame of resource allocation data
        start_date: Start date for the visualization
        end_date: End date for the visualization
    """
    # Redirect to the enhanced version
    display_enhanced_resource_calendar(filtered_data, start_date, end_date)


def display_resource_matrix_view(
    filtered_data: pd.DataFrame, start_date: pd.Timestamp, end_date: pd.Timestamp
) -> None:
    """
    Display resource data in a matrix visualization.

    Args:
        filtered_data: Filtered DataFrame of resource allocation data
        start_date: Start date for the visualization
        end_date: End date for the visualization
    """
    # Get chart height from display preferences
    display_prefs = load_display_preferences()
    chart_height = display_prefs.get("chart_height", 600)

    st.subheader("Resource Matrix View")

    if filtered_data.empty:
        st.info("No data to display with current filters.")
        return

    # Create a Gantt chart using Plotly
    fig = px.timeline(
        filtered_data,
        x_start="Start",
        x_end="End",
        y="Resource",
        color="Project",
        hover_name="Project",
        hover_data=["Allocation %"],
        title="Resource Allocation Timeline",
        labels={"Resource": "Resource", "Project": "Project"},
        height=chart_height,  # Add configurable chart height
    )

    # Add today's line
    today = pd.Timestamp.now()
    if start_date <= today <= end_date:
        fig.add_vline(x=today, line_width=2, line_color="red", line_dash="dash")
        fig.add_annotation(x=today, y=1.0, yref="paper", text="Today", showarrow=False)

    st.plotly_chart(fig, use_container_width=True)
