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
) -> None:
    """
    Display a form for creating or editing a department.

    Args:
        department_data: Existing department data for editing (optional)
        on_submit: Callback function to execute on form submission (optional)
        on_cancel: Callback function to execute on form cancellation (optional)
    """
    st.header("Department Form")

    # Generate a unique form key based on the department data to avoid duplicate element IDs
    form_key = f"dept_form_{id(department_data)}"

    # Pre-fill form fields if editing
    name = st.text_input(
        "Department Name",
        value=department_data.get("name", "") if department_data else "",
        key=f"{form_key}_name",
    )

    # Teams selection
    available_teams = [t["name"] for t in st.session_state.data["teams"]]
    teams = st.multiselect(
        "Teams",
        options=available_teams,
        default=department_data.get("teams", []) if department_data else [],
        key=f"{form_key}_teams",
    )

    # Members selection (direct department members, not through teams)
    available_people = [p["name"] for p in st.session_state.data["people"]]
    members = st.multiselect(
        "Direct Members",
        options=available_people,
        default=department_data.get("members", []) if department_data else [],
        key=f"{form_key}_members",
    )

    # Department color selection
    department_colors = load_department_colors()
    current_color = department_colors.get(name, "#1f77b4")

    color = st.color_picker("Department Color", current_color, key=f"{form_key}_color")

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
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Submit", key=f"{form_key}_submit"):
            # Basic validation
            if not name:
                st.error("Department name is required")
                return

            # Prepare department data
            department_info = {
                "name": name,
                "teams": teams,
                "members": members,
            }

            # Save the department color
            add_department_color(name, color)

            # Submit the form
            if on_submit:
                on_submit(department_info)

    with col2:
        if st.button("Cancel", key=f"{form_key}_cancel") and on_cancel:
            on_cancel()
