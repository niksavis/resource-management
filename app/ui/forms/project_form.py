"""
Project form components for the resource management application.

This module provides form components for creating, reading, updating, and deleting project resources.
"""

import streamlit as st
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from app.services.validation_service import validate_project
from app.services.data_service import parse_resources
from app.utils.formatting import format_currency


def display_project_form(
    project_data: Optional[Dict[str, Any]] = None, on_submit: Optional[callable] = None
) -> None:
    """
    Display a form for creating or editing a project.

    Args:
        project_data: Existing project data for editing (optional)
        on_submit: Callback function to execute on form submission (optional)
    """
    is_editing = project_data is not None

    st.header("Project Form")
    with st.form(key="project_form"):
        name = st.text_input(
            "Project Name",
            value=project_data.get("name", "") if is_editing else "",
            max_chars=100,
        )
        description = st.text_area(
            "Description",
            value=project_data.get("description", "") if is_editing else "",
        )
        start_date = st.date_input(
            "Start Date",
            value=pd.to_datetime(project_data.get("start_date"))
            if is_editing and "start_date" in project_data
            else datetime.now(),
        )
        end_date = st.date_input(
            "End Date",
            value=pd.to_datetime(project_data.get("end_date"))
            if is_editing and "end_date" in project_data
            else datetime.now() + timedelta(days=30),
        )
        priority = st.selectbox(
            "Priority",
            options=[1, 2, 3, 4, 5],
            index=(project_data.get("priority", 3) - 1) if is_editing else 2,
        )
        allocated_budget = st.number_input(
            "Allocated Budget",
            value=project_data.get("allocated_budget", 0.0) if is_editing else 0.0,
            min_value=0.0,
            format="%.2f",
        )
        assigned_resources = st.multiselect(
            "Assigned Resources",
            options=[
                r["name"]
                for r in st.session_state.data.get("people", [])
                + st.session_state.data.get("teams", [])
                + st.session_state.data.get("departments", [])
            ],
            default=project_data.get("assigned_resources", []) if is_editing else [],
        )

        # Submit button
        submitted = st.form_submit_button("Save Project")
        if submitted:
            # Validate project data
            validation_errors = validate_project(
                name=name,
                description=description,
                start_date=start_date,
                end_date=end_date,
                priority=priority,
                allocated_budget=allocated_budget,
                assigned_resources=assigned_resources,
            )
            if validation_errors:
                st.error("Validation Errors:")
                for error in validation_errors:
                    st.error(f"- {error}")
                return

            # Prepare project data
            new_project_data = {
                "name": name,
                "description": description,
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                "priority": priority,
                "allocated_budget": allocated_budget,
                "assigned_resources": assigned_resources,
            }

            # Execute callback if provided
            if on_submit:
                on_submit(new_project_data)

            st.success("Project saved successfully!")
