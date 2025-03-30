"""
Project form components for the resource management application.

This module provides form components for creating, reading, updating, and deleting project resources.
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from app.services.validation_service import validate_project
from app.services.data_service import parse_resources
from app.utils.formatting import format_currency


def display_project_form(
    project_data: Optional[Dict[str, Any]] = None,
    on_submit: Optional[callable] = None,
    form_type: str = "add",  # Can be "add", "edit", or "delete"
) -> None:
    """
    Display a form for creating, editing, or deleting a project.

    Args:
        project_data: Existing project data for editing (optional)
        on_submit: Callback function to execute on form submission (optional)
        form_type: Type of form to display (add, edit, delete)
    """
    is_editing = project_data is not None and form_type == "edit"
    is_deleting = form_type == "delete"

    # Generate a unique form key to avoid duplicate element IDs
    form_key = f"project_form_{id(project_data)}_{form_type}"

    title = f"{form_type.capitalize()} Project"
    with st.expander(title):
        st.header(title)

        with st.form(key=f"{form_key}_form"):
            name = st.text_input(
                "Project Name",
                value=project_data.get("name", "") if project_data else "",
                max_chars=100,
                disabled=is_deleting,
            )

            description = st.text_area(
                "Description",
                value=project_data.get("description", "") if project_data else "",
                disabled=is_deleting,
            )

            start_date = st.date_input(
                "Start Date",
                value=pd.to_datetime(project_data.get("start_date"))
                if project_data and "start_date" in project_data
                else datetime.now(),
                disabled=is_deleting,
            )

            end_date = st.date_input(
                "End Date",
                value=pd.to_datetime(project_data.get("end_date"))
                if project_data and "end_date" in project_data
                else datetime.now() + timedelta(days=30),
                disabled=is_deleting,
            )

            priority = st.selectbox(
                "Priority",
                options=[1, 2, 3, 4, 5],
                index=(project_data.get("priority", 3) - 1) if project_data else 2,
                disabled=is_deleting,
            )

            allocated_budget = st.number_input(
                "Allocated Budget",
                value=project_data.get("allocated_budget", 0.0)
                if project_data
                else 0.0,
                min_value=0.0,
                format="%.2f",
                disabled=is_deleting,
            )

            # Assign resources
            resource_options = [
                r["name"]
                for r in st.session_state.data.get("people", [])
                + st.session_state.data.get("teams", [])
                + st.session_state.data.get("departments", [])
            ]

            assigned_resources = st.multiselect(
                "Assigned Resources",
                options=resource_options,
                default=project_data.get("assigned_resources", [])
                if project_data
                else [],
                disabled=is_deleting,
            )

            # Resource allocation section
            if not is_deleting and assigned_resources:
                st.subheader("Resource Allocation")
                st.write("Set allocation percentage and time period for each resource:")

                # Get existing allocations if available
                existing_allocations = (
                    project_data.get("resource_allocations", []) if project_data else []
                )

                # Prepare UI for resource allocations
                resource_allocations = []

                for resource in assigned_resources:
                    st.markdown(f"**{resource}**")
                    col1, col2, col3 = st.columns([1, 2, 2])

                    # Find existing allocation for this resource
                    existing = next(
                        (a for a in existing_allocations if a["resource"] == resource),
                        None,
                    )

                    with col1:
                        allocation_pct = st.slider(
                            f"Allocation % for {resource}",
                            min_value=10,
                            max_value=100,
                            value=existing["allocation_percentage"]
                            if existing
                            else 100,
                            step=10,
                            key=f"{form_key}_alloc_{resource}",
                        )

                    with col2:
                        resource_start = st.date_input(
                            f"Start Date for {resource}",
                            value=pd.to_datetime(existing["start_date"])
                            if existing
                            else start_date,
                            min_value=start_date,
                            max_value=end_date,
                            key=f"{form_key}_start_{resource}",
                        )

                    with col3:
                        resource_end = st.date_input(
                            f"End Date for {resource}",
                            value=pd.to_datetime(existing["end_date"])
                            if existing
                            else end_date,
                            min_value=resource_start,
                            max_value=end_date,
                            key=f"{form_key}_end_{resource}",
                        )

                    # Add allocation details to the list
                    resource_allocations.append(
                        {
                            "resource": resource,
                            "allocation_percentage": allocation_pct,
                            "start_date": resource_start.strftime("%Y-%m-%d"),
                            "end_date": resource_end.strftime("%Y-%m-%d"),
                        }
                    )

                    st.markdown("---")

            # Form submission
            if is_deleting:
                confirm = st.checkbox(
                    "I confirm I want to delete this project", key=f"{form_key}_confirm"
                )
                submit_label = "Delete Project"
            else:
                confirm = True
                submit_label = "Save Project"

            submitted = st.form_submit_button(submit_label)

            if submitted:
                if not confirm and is_deleting:
                    st.error("Please confirm the deletion by checking the box.")
                    return

                if not is_deleting:
                    # Validate project data
                    validation_result, validation_errors = validate_project(
                        name=name,
                        description=description,
                        start_date=start_date,
                        end_date=end_date,
                        priority=priority,
                        allocated_budget=allocated_budget,
                        assigned_resources=assigned_resources,
                    )

                    if not validation_result:
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

                    # Add resource allocations if any
                    if assigned_resources:
                        new_project_data["resource_allocations"] = resource_allocations

                    # Execute callback if provided
                    if on_submit:
                        on_submit(new_project_data)
                        st.success(f"Project {form_type}d successfully!")

                # For delete, just pass the name
                elif on_submit:
                    on_submit({"name": project_data.get("name", "")})
                    st.success("Project deleted successfully!")
