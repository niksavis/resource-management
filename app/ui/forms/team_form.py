"""
Team form components for the resource management application.

This module provides form components for creating, reading, updating, and deleting team resources.
"""

import streamlit as st
from typing import Dict, Any, Optional
from app.services.validation_service import validate_team
from app.utils.form_utils import (
    display_form_header,
    display_form_feedback,
    display_confirm_checkbox,
    display_form_actions,
)


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

    # Display appropriate form header
    display_form_header("Team", form_type)

    # Pre-fill form fields if editing an existing team
    team_name = team_data.get("name", "") if team_data else ""
    department = team_data.get("department", "") if team_data else ""
    description = team_data.get("description", "") if team_data else ""
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

    # Add description field
    description = st.text_area(
        "Description",
        value=description,
        key=f"{form_key}_description",
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
        confirm = display_confirm_checkbox(
            "I confirm I want to delete this team", key=f"{form_key}_confirm"
        )
        button_label = "Delete Team"
        is_disabled = not confirm
    else:
        confirm = True
        button_label = "Save" if form_type == "edit" else "Add Team"
        is_disabled = len(members) < 2

    if display_form_actions(
        primary_label=button_label,
        primary_key=f"{form_key}_submit",
        is_delete=form_type == "delete",
        is_disabled=is_disabled,
        secondary_label="Cancel" if on_cancel else None,
        secondary_key=f"{form_key}_cancel" if on_cancel else None,
        secondary_action=on_cancel,
    ):
        if form_type == "delete":
            if on_submit:
                on_submit({"name": team_name})
        else:
            team_info = {
                "name": team_name,
                "department": department,
                "description": description,
                "members": members,
            }

            # Add validation before submitting
            validation_result, validation_errors = validate_team(team_info)
            if not validation_result:
                display_form_feedback(False, "Validation failed", validation_errors)
            elif on_submit:
                on_submit(team_info)
