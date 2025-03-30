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

    # Don't show a header since we're using expanders in the parent
    # st.header("Department Form")

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
        st.subheader("Department Cost")

        # Calculate the cost if editing an existing department
        if department_data:
            people_data = st.session_state.data["people"]
            teams_data = st.session_state.data["teams"]

            # We need to create a temporary department object with the current form values
            temp_department = {"name": name, "teams": teams, "members": members}

            cost = calculate_department_cost(temp_department, teams_data, people_data)
            st.info(f"Total Daily Cost: {format_currency(cost)}")

    # Form buttons
    if form_type == "delete":
        button_label = "Delete Department"
        confirm = st.checkbox(
            "I confirm I want to delete this department", key=f"{form_key}_confirm"
        )
    else:
        button_label = "Submit"
        confirm = True

    if st.button(button_label, key=f"{form_key}_submit", use_container_width=True):
        if confirm:
            # Basic validation
            if not name and form_type != "delete":
                st.error("Department name is required")
                return

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
            st.error("Please confirm the deletion by checking the box.")
