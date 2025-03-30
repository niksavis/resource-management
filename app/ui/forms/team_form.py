"""
Team form components for the resource management application.

This module provides form components for creating, reading, updating, and deleting team resources.
"""

import streamlit as st
from typing import Dict, Any, Optional, List
from app.services.validation_service import validate_team


def display_team_form(
    team_data: Optional[Dict[str, Any]] = None,
    on_submit: Optional[callable] = None,
    on_cancel: Optional[callable] = None,
) -> None:
    """
    Display a form for creating or editing a team.

    Args:
        team_data: Existing team data for editing (None for creating a new team)
        on_submit: Callback function to execute on form submission
        on_cancel: Callback function to execute on form cancellation
    """
    st.header("Team Form")

    # Pre-fill form fields if editing an existing team
    team_name = team_data.get("name", "") if team_data else ""
    department = team_data.get("department", "") if team_data else ""
    members = team_data.get("members", []) if team_data else []

    # Form fields
    team_name = st.text_input("Team Name", value=team_name)
    department = st.selectbox(
        "Department",
        options=[d["name"] for d in st.session_state.data["departments"]],
        index=0
        if not department
        else [d["name"] for d in st.session_state.data["departments"]].index(
            department
        ),
    )
    members = st.multiselect(
        "Members",
        options=[p["name"] for p in st.session_state.data["people"]],
        default=members,
    )

    # Form buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Submit"):
            if validate_team(team_name, department, members):
                team_info = {
                    "name": team_name,
                    "department": department,
                    "members": members,
                }
                if on_submit:
                    on_submit(team_info)
            else:
                st.error("Validation failed. Please check the form fields.")
    with col2:
        if st.button("Cancel"):
            if on_cancel:
                on_cancel()
