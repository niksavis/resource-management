"""
Department form components for the resource management application.

This module provides form components for creating, reading, updating, and deleting department resources.
"""

import streamlit as st
import random
from typing import Dict, Any, Optional, Callable
from app.services.config_service import (
    add_department_color,
    load_department_colors,
    save_department_colors,
    remove_department_color,
    get_department_color,
)
from app.utils.formatting import format_currency
from app.utils.resource_utils import calculate_department_cost
from app.services.validation_service import validate_department
from app.utils.form_utils import (
    display_form_header,
    display_form_feedback,
    display_confirm_checkbox,
    display_form_actions,
    display_form_section,
)


def get_unused_color():
    """
    Get a pleasing color not already used in department_colors settings.

    Returns:
        A hex color code not currently assigned to any department
    """
    # Visually pleasing color palette that works in both light and dark themes
    pleasing_colors = [
        "#3498db",  # Blue
        "#2ecc71",  # Green
        "#e74c3c",  # Red
        "#9b59b6",  # Purple
        "#f1c40f",  # Yellow
        "#1abc9c",  # Teal
        "#d35400",  # Orange
        "#34495e",  # Dark Blue
        "#16a085",  # Green Sea
        "#27ae60",  # Nephritis
        "#8e44ad",  # Wisteria
        "#f39c12",  # Orange
        "#c0392b",  # Pomegranate
        "#7f8c8d",  # Asbestos
        "#2980b9",  # Belize Hole
    ]

    # Get current colors
    current_colors = list(load_department_colors().values())

    # Find first color not already in use
    for color in pleasing_colors:
        if color not in current_colors:
            return color

    # If all colors are used, generate a new one by slightly modifying an existing color
    base_color = random.choice(pleasing_colors)

    # Adjust hue slightly to create a new color
    hex_color = base_color.lstrip("#")
    r, g, b = tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))

    # Adjust RGB values slightly
    r = (r + random.randint(-20, 20)) % 256
    g = (g + random.randint(-20, 20)) % 256
    b = (b + random.randint(-20, 20)) % 256

    return f"#{r:02x}{g:02x}{b:02x}"


def display_department_form(
    department_data: Optional[Dict[str, Any]] = None,
    on_submit: Optional[Callable[[Dict[str, Any]], None]] = None,
    on_cancel: Optional[Callable[[], None]] = None,
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

    # When editing, use the department name as part of the key for stable state
    dept_name_key = department_data.get("name", "new") if department_data else "new"
    stable_key = f"dept_form_{dept_name_key}_{form_type}"

    # Display appropriate form header
    display_form_header("Department", form_type)

    # Pre-fill form fields if editing
    name = st.text_input(
        "Department Name",
        value=department_data.get("name", "") if department_data else "",
        key=f"{stable_key}_name",
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

    # Initialize the teams state if not already done
    teams_key = f"{stable_key}_teams"
    if teams_key not in st.session_state:
        st.session_state[teams_key] = existing_teams

    # Store previous state to track changes
    prev_key = f"{stable_key}_prev_teams"
    if prev_key not in st.session_state:
        st.session_state[prev_key] = existing_teams.copy() if existing_teams else []

    # Use the teams multiselect with explicit session state
    teams = st.multiselect(
        "Teams",
        options=available_teams,
        default=st.session_state[teams_key],
        key=teams_key,
        disabled=form_type == "delete",
    )

    # Check if teams were added or removed and provide feedback
    added_teams = [t for t in teams if t not in st.session_state[prev_key]]
    removed_teams = [t for t in st.session_state[prev_key] if t not in teams]

    if added_teams:
        st.success(f"Teams added: {', '.join(added_teams)}")
    if removed_teams:
        st.warning(f"Teams removed: {', '.join(removed_teams)}")

    # Update previous state for next render
    st.session_state[prev_key] = teams.copy()

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

    # Department color selection using get_department_color
    current_color = get_department_color(name, "#1f77b4")

    if form_type == "add" and name not in load_department_colors():
        current_color = get_unused_color()

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
            if form_type == "delete":
                # Remove the department color when the department is deleted
                remove_department_color(name)
            elif form_type == "add":
                department_colors = load_department_colors()
                department_colors[name] = color
                save_department_colors(department_colors)
            else:
                # For edit operations
                add_department_color(name, color)

            # Submit the form
            if on_submit:
                on_submit(department_info)
        else:
            display_form_feedback(
                False, "Please confirm the deletion by checking the box."
            )
