"""
Team form components for the resource management application.

This module provides form components for creating, reading, updating, and deleting team resources.
"""

import streamlit as st
from typing import Dict, Any, Optional, Callable
from app.utils.formatting import format_currency
from app.utils.resource_utils import calculate_team_cost
from app.services.validation_service import validate_team
from app.utils.form_utils import (
    display_form_header,
    display_form_feedback,
    display_confirm_checkbox,
    display_form_actions,
    display_form_section,
)


def display_team_form(
    team_data: Optional[Dict[str, Any]] = None,
    on_submit: Optional[Callable[[Dict[str, Any]], None]] = None,
    on_cancel: Optional[Callable[[], None]] = None,
    form_type: str = "add",  # Can be "add", "edit", or "delete"
) -> None:
    """
    Display a form for creating, editing, or deleting a team.

    Args:
        team_data: Existing team data for editing (optional)
        on_submit: Callback function to execute on form submission (optional)
        on_cancel: Callback function to execute on form cancellation (optional)
        form_type: Type of form to display (add, edit, delete)
    """
    # Generate a unique form key based on the team data to avoid duplicate element IDs
    form_key = f"team_form_{id(team_data)}_{form_type}"

    # When editing, use the team name as part of the key for stable state
    team_name_key = team_data.get("name", "new") if team_data else "new"
    stable_key = f"team_form_{team_name_key}_{form_type}"

    # Display appropriate form header
    display_form_header("Team", form_type)

    # Pre-fill form fields if editing
    name = st.text_input(
        "Team Name",
        value=team_data.get("name", "") if team_data else "",
        key=f"{stable_key}_name",
        disabled=form_type == "delete",
    )

    # Department selection - all departments available
    departments = [d["name"] for d in st.session_state.data["departments"]]

    # Safely determine department index
    dept_index = 0  # Default to no department selected
    if team_data and team_data.get("department"):
        try:
            dept_index = departments.index(team_data["department"]) + 1
        except ValueError:
            # Department not found in list, use default index
            dept_index = 0

    department = st.selectbox(
        "Department",
        options=[""] + departments,
        index=dept_index,
        key=f"{stable_key}_department",
        disabled=form_type == "delete",
    )

    # Members selection
    available_people = [p["name"] for p in st.session_state.data["people"]]

    # Filter out people that no longer exist
    existing_members = []
    if team_data and "members" in team_data:
        existing_members = [m for m in team_data["members"] if m in available_people]
        if len(existing_members) != len(team_data.get("members", [])):
            # Some members were removed, update the team data
            if team_data:
                team_data["members"] = existing_members

    # Initialize the members state if not already done
    members_key = f"{stable_key}_members"
    if members_key not in st.session_state:
        st.session_state[members_key] = existing_members

    # Store previous state to track changes
    prev_key = f"{stable_key}_prev_members"
    if prev_key not in st.session_state:
        st.session_state[prev_key] = existing_members.copy() if existing_members else []

    # Use the members multiselect with explicit session state
    members = st.multiselect(
        "Team Members",
        options=available_people,
        default=st.session_state[members_key],
        key=members_key,
        disabled=form_type == "delete",
    )

    # Check if members were added or removed and provide feedback
    added_members = [m for m in members if m not in st.session_state[prev_key]]
    removed_members = [m for m in st.session_state[prev_key] if m not in members]

    if added_members:
        st.success(f"Members added: {', '.join(added_members)}")
    if removed_members:
        st.warning(f"Members removed: {', '.join(removed_members)}")

    # Update previous state for next render
    st.session_state[prev_key] = members.copy()

    # Cost calculation and display
    if members:
        display_form_section("Team Cost")

        # Calculate the cost if editing an existing team
        if form_type in ["edit", "delete"]:
            people_data = st.session_state.data["people"]

            # We need to create a temporary team object with the current form values
            temp_team = {"name": name, "department": department, "members": members}

            cost = calculate_team_cost(temp_team, people_data)
            st.info(f"Total Daily Cost: {format_currency(cost)}")

    # Form buttons
    if form_type == "delete":
        confirm = display_confirm_checkbox(
            "I confirm I want to delete this team", key=f"{form_key}_confirm"
        )
        button_label = "Delete Team"
    else:
        confirm = True
        button_label = "Save" if form_type == "edit" else "Add Team"

    if display_form_actions(
        primary_label=button_label,
        primary_key=f"{form_key}_submit",
        is_delete=form_type == "delete",
        is_disabled=form_type == "delete" and not confirm,
        secondary_label="Cancel" if on_cancel else None,
        secondary_key=f"{form_key}_cancel" if on_cancel else None,
        secondary_action=on_cancel,
    ):
        if confirm:
            # Basic validation
            validation_result, validation_errors = validate_team(
                {"name": name, "department": department, "members": members}
            )

            if not validation_result:
                display_form_feedback(False, "Validation failed", validation_errors)
                return

            # Prepare team data
            team_info = {
                "name": name,
                "department": department,
                "members": members,
            }

            # Submit the form
            if on_submit:
                on_submit(team_info)
        else:
            display_form_feedback(
                False, "Please confirm the deletion by checking the box."
            )
