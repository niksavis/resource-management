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
                default=["Person", "Team", "Department"],
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
        height=500,
    )

    # Add bands for optimal utilization
    fig.add_hrect(
        y0=optimal_min,
        y1=optimal_max,
        line_width=0,
        fillcolor="green",
        opacity=0.1,
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
            height=400,
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
            height=400,
        )

        st.plotly_chart(fig2, use_container_width=True)


def display_resource_conflicts_enhanced(filtered_data: pd.DataFrame) -> None:
    """
    Display enhanced resource conflicts visualization with severity indicators.

    Args:
        filtered_data: Filtered DataFrame of resource allocation data
    """
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
        height=400,
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
        display_utilization_dashboard(filtered_data, start_date, end_date)


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
        display_resource_calendar(filtered_data, start_date, end_date)


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
    )

    # Add today's line
    today = pd.Timestamp.now()
    if start_date <= today <= end_date:
        fig.add_vline(x=today, line_width=2, line_color="red", line_dash="dash")
        fig.add_annotation(x=today, y=1.0, yref="paper", text="Today", showarrow=False)

    st.plotly_chart(fig, use_container_width=True)


def _display_resource_conflicts(filtered_data: pd.DataFrame) -> None:
    """
    Display resource conflicts (overallocations).

    Args:
        filtered_data: Filtered DataFrame of resource allocation data
    """
    st.subheader("Resource Conflicts")
    conflicts = find_resource_conflicts(filtered_data)

    if conflicts.empty:
        st.success("No resource conflicts detected in the selected date range.")
        return

    # Group conflicts by resource
    resources = conflicts["Resource"].unique()
    for resource in resources:
        resource_conflicts = conflicts[conflicts["Resource"] == resource]

        with st.expander(f"⚠️ {resource} ({len(resource_conflicts)} overallocations)"):
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


def display_utilization_dashboard(
    filtered_data: pd.DataFrame, start_date: pd.Timestamp, end_date: pd.Timestamp
) -> None:
    """
    Display the utilization dashboard with various charts.

    Args:
        filtered_data: Filtered DataFrame of resource allocation data
        start_date: Start date for the visualization
        end_date: End date for the visualization
    """
    st.subheader("Utilization Dashboard")

    # Calculate utilization metrics
    utilization_df = calculate_resource_utilization(filtered_data)

    if utilization_df.empty:
        st.info("No utilization data available with current filters.")
        return

    # Display utilization metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        avg_util = utilization_df["Utilization %"].mean()
        st.metric("Average Utilization", f"{avg_util:.1f}%")

    with col2:
        over_util = sum(utilization_df["Utilization %"] > 100)
        st.metric("Overallocated Resources", over_util)

    with col3:
        under_util = sum(utilization_df["Utilization %"] < 50)
        st.metric("Underutilized Resources", under_util)

    # Display bar chart of utilization by resource
    utilization_chart = px.bar(
        utilization_df.sort_values("Utilization %", ascending=False),
        x="Resource",
        y="Utilization %",
        color="Type",
        title="Resource Utilization",
        labels={"Resource": "Resource", "Utilization %": "Utilization %"},
    )

    # Add a 100% line to show full allocation
    utilization_chart.add_hline(y=100, line_width=2, line_dash="dash", line_color="red")

    st.plotly_chart(utilization_chart, use_container_width=True)


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
    st.subheader("Capacity Planning Dashboard")

    # Generate capacity data
    capacity_data = calculate_capacity_data(filtered_data, start_date, end_date)

    if capacity_data.empty:
        st.info("No capacity data available with current filters.")
        return

    # Create a heatmap of resource allocations over time
    # First, pivot the data to have resources as rows and dates as columns
    pivot_data = capacity_data.pivot_table(
        index="Resource", columns="Date", values="Allocation", aggfunc="sum"
    )

    # Create a heatmap using plotly
    heatmap = px.imshow(
        pivot_data.values,
        labels=dict(x="Date", y="Resource", color="Allocation"),
        x=pivot_data.columns.strftime("%Y-%m-%d"),
        y=pivot_data.index,
        color_continuous_scale=px.colors.sequential.Viridis,
        title="Resource Allocation Heatmap",
    )

    st.plotly_chart(heatmap, use_container_width=True)


def display_resource_calendar(
    filtered_data: pd.DataFrame, start_date: pd.Timestamp, end_date: pd.Timestamp
) -> None:
    """
    Display a calendar view of resource allocations.

    Args:
        filtered_data: Filtered DataFrame of resource allocation data
        start_date: Start date for the visualization
        end_date: End date for the visualization
    """
    st.subheader("Resource Calendar")

    if filtered_data.empty:
        st.info("No data available for the calendar view with current filters.")
        return

    # Select a resource to view
    resources = filtered_data["Resource"].unique()
    selected_resource = st.selectbox(
        "Select Resource", options=resources, key="calendar_resource"
    )

    # Filter for the selected resource
    resource_data = filtered_data[filtered_data["Resource"] == selected_resource]

    # Display calendar with allocations
    months = pd.date_range(start=start_date, end=end_date, freq="MS")

    for month_start in months:
        month_end = month_start + pd.offsets.MonthEnd(1)
        month_name = month_start.strftime("%B %Y")

        with st.expander(month_name, expanded=months[0] == month_start):
            # Get days in the month
            days_in_month = calendar.monthrange(month_start.year, month_start.month)[1]

            # Create a calendar grid
            rows = []
            week = []

            # Add empty cells for days before the 1st of the month
            first_day_weekday = month_start.weekday()
            for _ in range(first_day_weekday):
                week.append("")

            # Add days of the month
            for day in range(1, days_in_month + 1):
                date = pd.Timestamp(
                    year=month_start.year, month=month_start.month, day=day
                )

                # Check if this date has allocations
                day_allocations = resource_data[
                    (resource_data["Start"] <= date) & (resource_data["End"] >= date)
                ]

                if not day_allocations.empty:
                    # Calculate total allocation for this day
                    total_allocation = day_allocations["Allocation %"].sum() / 100
                    color = _get_allocation_color(total_allocation)

                    projects = day_allocations["Project"].tolist()
                    week.append(
                        f"<div style='background-color:{color};padding:10px;'>"
                        f"<strong>{day}</strong><br>"
                        f"{total_allocation:.0%}<br>"
                        f"{', '.join(projects)}"
                        f"</div>"
                    )
                else:
                    week.append(
                        f"<div style='padding:10px;'><strong>{day}</strong></div>"
                    )

                # Start a new week after Saturday
                if (first_day_weekday + day) % 7 == 0:
                    rows.append(week)
                    week = []

            # Add the last week if it's not complete
            if week:
                # Pad with empty cells to complete the week
                while len(week) < 7:
                    week.append("")
                rows.append(week)

            # Display the calendar
            calendar_html = "<table width='100%'><tr><th>Mon</th><th>Tue</th><th>Wed</th><th>Thu</th><th>Fri</th><th>Sat</th><th>Sun</th></tr>"
            for row in rows:
                calendar_html += "<tr>"
                for cell in row:
                    calendar_html += f"<td style='border:1px solid #ddd;'>{cell}</td>"
                calendar_html += "</tr>"
            calendar_html += "</table>"

            st.markdown(calendar_html, unsafe_allow_html=True)


def _get_allocation_color(allocation: float) -> str:
    """
    Get a color based on allocation percentage.

    Args:
        allocation: Allocation as a decimal (0.0 to 1.0+)

    Returns:
        Hex color code
    """
    if allocation < 0.5:
        return "#c6efce"  # Light green
    elif allocation < 0.8:
        return "#ffeb9c"  # Light yellow
    elif allocation <= 1.0:
        return "#ffc7ce"  # Light red
    else:
        return "#ff0000"  # Bright red for overallocation
