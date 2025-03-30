"""
Team form components for the resource management application.

This module provides form components for creating, reading, updating, and deleting team resources.
"""

import streamlit as st
from typing import Dict, Any, Optional, List


def display_team_form(
    team_data: Optional[Dict[str, Any]] = None,
    on_submit: Optional[callable] = None,
    on_cancel: Optional[callable] = None,
    form_type: str = "add",  # Can be "add", "edit", or "delete"
) -> None:
    """
    Display a form for creating, editing, or deleting a team.

    Args:
        team_data: Existing team data for editing (None for creating a new team)
        on_submit: Callback function to execute on form submission
        on_cancel: Callback function to execute on form cancellation
        form_type: Type of form to display (add, edit, delete)
    """
    # Generate a unique form key to avoid duplicate element IDs
    form_key = f"team_form_{id(team_data)}_{form_type}"

    # No header needed since the parent component uses expanders

    # Pre-fill form fields if editing an existing team
    team_name = team_data.get("name", "") if team_data else ""
    department = team_data.get("department", "") if team_data else ""
    members = team_data.get("members", []) if team_data else []

    # Get available people options
    available_people = [p["name"] for p in st.session_state.data["people"]]

    # Filter out any members that no longer exist in the people list
    existing_members = [m for m in members if m in available_people]
    if len(existing_members) != len(members):
        # Some members were removed, update the team data
        if team_data:
            team_data["members"] = existing_members
        members = existing_members

    # Form fields - Add unique keys to all form elements
    team_name = st.text_input(
        "Team Name",
        value=team_name,
        key=f"{form_key}_name",
        disabled=form_type == "delete",
    )

    department_options = [d["name"] for d in st.session_state.data["departments"]]
    dept_index = 0
    if department in department_options:
        dept_index = department_options.index(department)

    department = st.selectbox(
        "Department",
        options=department_options,
        index=dept_index,
        key=f"{form_key}_department",
        disabled=form_type == "delete",
    )

    members = st.multiselect(
        "Members",
        options=available_people,
        default=existing_members,  # Use filtered list of existing members
        key=f"{form_key}_members",
        disabled=form_type == "delete",
    )

    # Display requirement for at least 2 members
    if not form_type == "delete" and len(members) < 2:
        st.warning("Teams must have at least 2 members.")

    # Form buttons
    if form_type == "delete":
        confirm = st.checkbox(
            "I confirm I want to delete this team", key=f"{form_key}_confirm"
        )
        submit_disabled = not confirm
        button_label = "Delete Team"
    else:
        submit_disabled = len(members) < 2
        button_label = "Submit"

    if st.button(
        button_label,
        key=f"{form_key}_submit",
        disabled=submit_disabled,
        use_container_width=True,
    ):
        if form_type == "delete":
            if on_submit:
                on_submit({"name": team_name})
        else:
            team_info = {
                "name": team_name,
                "department": department,
                "members": members,
            }
            if on_submit:
                on_submit(team_info)
