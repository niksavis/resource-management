"""
Department form components for the resource management application.

This module provides form components for creating, reading, updating, and deleting department resources.
"""

import streamlit as st
from typing import Dict, Any, Optional, List, Tuple
import plotly.express as px

from app.services.config_service import add_department_color, load_department_colors
from app.utils.formatting import format_currency
from app.utils.resource_utils import (
    calculate_department_cost,
    find_resource_by_name,
    update_resource,
)
from app.services.validation_service import validate_department
from app.utils.form_utils import (
    display_form_header,
    display_form_feedback,
    display_confirm_checkbox,
    display_form_actions,
    display_form_section,
)


def display_department_form(
    department_data: Optional[Dict[str, Any]] = None,
    on_submit: Optional[callable] = None,
    on_cancel: Optional[callable] = None,
    form_type: str = "add",  # Can be "add", "edit", or "delete"
) -> None:
    """
    Display a form for creating, editing, or deleting a department.

    Args:
        department_data: Existing department data for editing (optional)
        on_submit: Callback function to execute on form submission (optional)
        on_cancel: Callback function to execute on form cancellation (optional)
        form_type: Type of form to display (add, edit, delete)
    """
    # Generate a unique form key based on the department data to avoid duplicate element IDs
    form_key = f"dept_form_{id(department_data)}_{form_type}"

    # Display appropriate form header
    display_form_header("Department", form_type)

    # Pre-fill form fields if editing
    name = st.text_input(
        "Department Name",
        value=department_data.get("name", "") if department_data else "",
        key=f"{form_key}_name",
        disabled=form_type == "delete",
    )

    # Teams selection
    available_teams = [t["name"] for t in st.session_state.data["teams"]]
    # Filter out teams that no longer exist
    existing_teams = []
    if department_data and "teams" in department_data:
        existing_teams = [t for t in department_data["teams"] if t in available_teams]
        if len(existing_teams) != len(department_data.get("teams", [])):
            # Some teams were removed, update the department data
            if department_data:
                department_data["teams"] = existing_teams

    teams = st.multiselect(
        "Teams",
        options=available_teams,
        default=existing_teams,
        key=f"{form_key}_teams",
        disabled=form_type == "delete",
    )

    # Members selection (direct department members, not through teams)
    available_people = [p["name"] for p in st.session_state.data["people"]]
    # Filter out people that no longer exist
    existing_members = []
    if department_data and "members" in department_data:
        existing_members = [
            m for m in department_data["members"] if m in available_people
        ]
        if len(existing_members) != len(department_data.get("members", [])):
            # Some members were removed, update the department data
            if department_data:
                department_data["members"] = existing_members

    members = st.multiselect(
        "Direct Members",
        options=available_people,
        default=existing_members,
        key=f"{form_key}_members",
        disabled=form_type == "delete",
    )

    # Department color selection
    department_colors = load_department_colors()
    current_color = department_colors.get(name, "#1f77b4")

    color = st.color_picker(
        "Department Color",
        current_color,
        key=f"{form_key}_color",
        disabled=form_type == "delete",
    )

    # Cost calculation and display
    if teams or members:
        display_form_section("Department Cost")

        # Calculate the cost if editing an existing department
        if department_data:
            people_data = st.session_state.data["people"]
            teams_data = st.session_state.data["teams"]

            # We need to create a temporary department object with the current form values
            temp_department = {"name": name, "teams": teams, "members": members}

            cost = calculate_department_cost(temp_department, teams_data, people_data)
            st.info(f"Total Daily Cost: {format_currency(cost)}")

    # Check for conflicts between direct members and team members
    temp_department = {"name": name, "teams": teams, "members": members}
    _, _, conflicts = validate_department(temp_department)

    if conflicts:
        st.warning("⚠️ **Member-Team Conflict Detected**")
        st.markdown(
            "The following members are both direct members and part of teams in this department:"
        )

        for conflict in conflicts:
            st.markdown(
                f"- **{conflict['member']}** is in teams: {', '.join(conflict['teams'])}"
            )

        st.markdown("**Solution Options:**")
        st.markdown("1. Remove the person from direct members")
        st.markdown("2. Remove the teams containing this person")
        st.markdown("3. Remove the person from the teams in Team Management")

        st.info(
            "Having a person both as a direct member and as part of a team will result in double allocation."
        )

    # Form buttons
    if form_type == "delete":
        confirm = display_confirm_checkbox(
            "I confirm I want to delete this department", key=f"{form_key}_confirm"
        )
        button_label = "Delete Department"
    else:
        confirm = True
        button_label = "Save" if form_type == "edit" else "Add Department"

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
            validation_result, validation_errors, conflicts = validate_department(
                {"name": name, "teams": teams, "members": members}
            )

            if not validation_result:
                display_form_feedback(False, "Validation failed", validation_errors)
                return

            # Warn about conflicts but allow submission
            if conflicts and form_type != "delete":
                st.warning(
                    f"Note: {len(conflicts)} member-team conflicts detected. These may cause double allocation."
                )

            # Prepare department data
            department_info = {
                "name": name,
                "teams": teams,
                "members": members,
            }

            # Save the department color
            if form_type != "delete":
                add_department_color(name, color)

            # Submit the form
            if on_submit:
                on_submit(department_info)
        else:
            display_form_feedback(
                False, "Please confirm the deletion by checking the box."
            )
