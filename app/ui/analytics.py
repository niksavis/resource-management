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

    # Display the matrix view with filtered data
    display_resource_matrix_view(filtered_data, start_date, end_date)

    # Display resource conflicts section
    _display_resource_conflicts(filtered_data)


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
