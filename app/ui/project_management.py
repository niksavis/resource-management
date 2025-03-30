"""
Project Management UI module.

This module provides the UI components for managing projects.
"""

import streamlit as st
import pandas as pd
import numpy as np
from typing import List, Dict, Any

from app.utils.ui_components import display_action_bar, paginate_dataframe
from app.services.config_service import load_display_preferences
from app.ui.forms.project_form import display_project_form as add_project_form
from app.ui.forms.project_form import display_project_form as edit_project_form
from app.ui.forms.project_form import display_project_form as delete_project_form
from app.services.data_service import parse_resources


def display_manage_projects_tab():
    """Display the project management tab with project list and CRUD forms."""
    display_action_bar()
    st.subheader("Project Management")

    if not st.session_state.data["projects"]:
        st.warning("No projects found. Please add a project first.")
        add_project_form()
        return

    # Create and filter projects dataframe
    projects_df = _create_projects_dataframe()
    projects_df = _filter_projects_dataframe(projects_df)

    # Display projects in a dataframe
    st.dataframe(projects_df, use_container_width=True)

    # Project CRUD Forms
    add_project_form()
    edit_project_form()
    delete_project_form()


def _create_projects_dataframe() -> pd.DataFrame:
    """
    Create a DataFrame from project data.

    Returns:
        DataFrame with project information
    """
    return pd.DataFrame(
        [
            {
                "Name": p["name"],
                "Start Date": pd.to_datetime(p["start_date"]).strftime("%Y-%m-%d"),
                "End Date": pd.to_datetime(p["end_date"]).strftime("%Y-%m-%d"),
                "Priority": p["priority"],
                "Duration (Days)": (
                    pd.to_datetime(p["end_date"]) - pd.to_datetime(p["start_date"])
                ).days
                + 1,
                "Assigned People": parse_resources(p["assigned_resources"])[0],
                "Assigned Teams": parse_resources(p["assigned_resources"])[1],
                "Assigned Departments": parse_resources(p["assigned_resources"])[2],
            }
            for p in st.session_state.data["projects"]
        ]
    )


def _filter_projects_dataframe(projects_df: pd.DataFrame) -> pd.DataFrame:
    """
    Filter projects DataFrame based on user-selected filters.

    Args:
        projects_df: DataFrame containing project data

    Returns:
        Filtered DataFrame
    """
    with st.expander("Search and Filter Projects", expanded=False):
        # First row: Search and Date Filter
        col1, col3 = st.columns([1, 1])

        with col1:
            search_term = st.text_input("Search Projects", key="search_projects")

        with col3:
            date_range = st.date_input(
                "Filter by Date Range",
                value=(
                    pd.to_datetime(projects_df["Start Date"]).min().date(),
                    pd.to_datetime(projects_df["End Date"]).max().date(),
                ),
                min_value=pd.to_datetime(projects_df["Start Date"]).min().date(),
                max_value=pd.to_datetime(projects_df["End Date"]).max().date(),
            )

        # Second row: Resource filters
        col4, col5, col6 = st.columns(3)

        with col4:
            people_filter = st.multiselect(
                "Filter by Assigned People",
                options=[p["name"] for p in st.session_state.data["people"]],
                default=[],
                key="filter_people_projects",
            )

        with col5:
            teams_filter = st.multiselect(
                "Filter by Assigned Team",
                options=[t["name"] for t in st.session_state.data["teams"]],
                default=[],
                key="filter_teams_projects",
            )

        with col6:
            departments_filter = st.multiselect(
                "Filter by Assigned Department",
                options=[d["name"] for d in st.session_state.data["departments"]],
                default=[],
                key="filter_departments_projects",
            )

        # Apply search filter
        if search_term:
            mask = np.column_stack(
                [
                    projects_df[col]
                    .fillna("")
                    .astype(str)
                    .str.contains(search_term, case=False, na=False)
                    for col in projects_df.columns
                ]
            )
            projects_df = projects_df[mask.any(axis=1)]

        # Apply date filter
        if len(date_range) == 2:
            start_date, end_date = (
                pd.to_datetime(date_range[0]),
                pd.to_datetime(date_range[1]),
            )
            projects_df = projects_df[
                (pd.to_datetime(projects_df["Start Date"]) >= start_date)
                & (pd.to_datetime(projects_df["End Date"]) <= end_date)
            ]

        # Apply resource filters
        if people_filter:
            projects_df = projects_df[
                projects_df["Assigned People"].apply(
                    lambda x: any(person in x for person in people_filter)
                )
            ]

        if teams_filter:
            projects_df = projects_df[
                projects_df["Assigned Teams"].apply(
                    lambda x: any(team in x for team in teams_filter)
                )
            ]

        if departments_filter:
            projects_df = projects_df[
                projects_df["Assigned Departments"].apply(
                    lambda x: any(dept in x for dept in departments_filter)
                )
            ]

        # Apply pagination with configured page size
        display_prefs = load_display_preferences()
        page_size = display_prefs.get("page_size", 10)
        projects_df = paginate_dataframe(
            projects_df, "projects", items_per_page=page_size
        )

    return projects_df
