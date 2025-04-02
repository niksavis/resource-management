"""
Project form components for the resource management application.

This module provides form components for creating, reading, updating, and deleting project resources.
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from app.utils.form_utils import (
    display_form_header,
    display_form_feedback,
    display_confirm_checkbox,
    display_form_section,
    display_resource_icon,
)


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
    form_key = f"project_form_{id(project_data)}_{form_type}_{st.session_state.get('form_counter', 0)}"
    # Increment form counter to ensure uniqueness across reruns
    if "form_counter" not in st.session_state:
        st.session_state.form_counter = 0
    st.session_state.form_counter += 1

    # Display appropriate form header
    display_form_header("Project", form_type)

    # Use a container instead of an expander to avoid nesting issues
    with st.form(key=form_key):
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

        # Calculate the default priority - for new projects, it's max priority + 1
        existing_priorities = [
            p.get("priority", 1) for p in st.session_state.data["projects"]
        ]
        if project_data and "priority" in project_data:
            # For editing, use current priority
            default_priority = project_data.get("priority", 1)
        else:
            # For new projects, set default as one less priority than current min
            default_priority = max(existing_priorities, default=[0]) + 1

        # Replace dropdown with number input for priority
        priority = st.number_input(
            "Priority (1 = highest)",
            value=default_priority,
            min_value=1,
            step=1,
            help="Each project must have a unique priority. Lower numbers = higher priority.",
            disabled=is_deleting,
        )

        allocated_budget = st.number_input(
            "Allocated Budget",
            value=project_data.get("allocated_budget", 0.0) if project_data else 0.0,
            min_value=0.0,
            step=1000.0,
            format="%.2f",
            disabled=is_deleting,
        )

        # Resource assignment - match other forms' style
        display_form_section("Resource Assignment")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("#### 👤 People")
            people_options = [p["name"] for p in st.session_state.data["people"]]
            selected_people = st.multiselect(
                "Select People",
                options=people_options,
                default=[
                    r
                    for r in project_data.get("assigned_resources", [])
                    if r in people_options
                ]
                if project_data
                else [],
                key=f"{form_key}_people",
                disabled=is_deleting,
            )

        with col2:
            st.markdown("#### 👥 Teams")
            team_options = [t["name"] for t in st.session_state.data["teams"]]
            selected_teams = st.multiselect(
                "Select Teams",
                options=team_options,
                default=[
                    r
                    for r in project_data.get("assigned_resources", [])
                    if r in team_options
                ]
                if project_data
                else [],
                key=f"{form_key}_teams",
                disabled=is_deleting,
            )

        with col3:
            st.markdown("#### 🏢 Departments")
            dept_options = [d["name"] for d in st.session_state.data["departments"]]
            selected_depts = st.multiselect(
                "Select Departments",
                options=dept_options,
                default=[
                    r
                    for r in project_data.get("assigned_resources", [])
                    if r in dept_options
                ]
                if project_data
                else [],
                key=f"{form_key}_departments",
                disabled=is_deleting,
            )

        # Combine all selected resources
        assigned_resources = selected_people + selected_teams + selected_depts

        # Resource allocation section - dynamic based on selected resources
        if not is_deleting and assigned_resources:
            display_form_section("Resource Allocation")
            st.info(
                "Set allocation percentage and time period for each resource. Time periods must be within project dates."
            )

            # Get existing allocations if available
            existing_allocations = (
                project_data.get("resource_allocations", []) if project_data else []
            )

            # Prepare UI for resource allocations
            resource_allocations = []

            for resource in assigned_resources:
                # Determine resource type for visual distinction
                resource_type = "Person"
                resource_icon = "👤"
                if any(t["name"] == resource for t in st.session_state.data["teams"]):
                    resource_type = "Team"
                    resource_icon = "👥"
                elif any(
                    d["name"] == resource for d in st.session_state.data["departments"]
                ):
                    resource_type = "Department"
                    resource_icon = "🏢"

                # Find existing allocation for this resource
                existing = next(
                    (a for a in existing_allocations if a["resource"] == resource), None
                )

                # Use a container with a divider and header instead of an expander
                st.markdown(f"#### {resource_icon} {resource} ({resource_type})")

                col1, col2, col3 = st.columns([1, 2, 2])

                with col1:
                    allocation_pct = st.slider(
                        "Allocation %",
                        min_value=10,
                        max_value=100,
                        value=existing["allocation_percentage"] if existing else 100,
                        step=10,
                        key=f"{form_key}_alloc_{resource}",
                    )

                # Set date range boundaries based on project dates
                with col2:
                    resource_start = st.date_input(
                        "Start Date",
                        value=pd.to_datetime(existing["start_date"])
                        if existing
                        else start_date,
                        min_value=start_date,
                        max_value=end_date,
                        key=f"{form_key}_start_{resource}",
                    )

                with col3:
                    resource_end = st.date_input(
                        "End Date",
                        value=pd.to_datetime(existing["end_date"])
                        if existing
                        else end_date,
                        min_value=resource_start,
                        max_value=end_date,
                        key=f"{form_key}_end_{resource}",
                    )

                # Validation feedback
                if resource_start < start_date or resource_end > end_date:
                    st.error("Resource allocation dates must be within project dates!")
                elif resource_start > resource_end:
                    st.error("Start date must be before end date!")

                # Add allocation details to the list
                resource_allocations.append(
                    {
                        "resource": resource,
                        "resource_type": resource_type.lower(),
                        "allocation_percentage": allocation_pct,
                        "start_date": resource_start.strftime("%Y-%m-%d"),
                        "end_date": resource_end.strftime("%Y-%m-%d"),
                    }
                )

                # Add a divider between resources
                st.divider()

        # Form submission section
        if is_deleting:
            confirm = display_confirm_checkbox(
                "I confirm I want to delete this project", key=f"{form_key}_confirm"
            )
            submit_label = "Delete Project"
        else:
            confirm = True
            submit_label = "Save" if form_type == "edit" else "Add Project"

        submitted = st.form_submit_button(
            label=f"{display_resource_icon('project')} {submit_label}",
            type="primary" if not is_deleting else "danger",
            disabled=is_deleting and not confirm,
            use_container_width=True,
        )

        if submitted:
            if not confirm and is_deleting:
                display_form_feedback(
                    False, "Please confirm the deletion by checking the box."
                )
                return

            if not is_deleting:
                # Basic validation - just check required fields
                if not name:
                    display_form_feedback(
                        False,
                        "Project name is required",
                        ["Please enter a project name"],
                    )
                    return

                if not assigned_resources:
                    display_form_feedback(
                        False,
                        "No resources assigned",
                        ["Please assign at least one resource to the project"],
                    )
                    return

                if start_date > end_date:
                    display_form_feedback(
                        False,
                        "Invalid date range",
                        ["Start date must be before end date"],
                    )
                    return

                # Check if priority is already taken by another project
                priority_conflict = False
                if form_type == "add":
                    priority_conflict = any(
                        p.get("priority") == priority
                        for p in st.session_state.data["projects"]
                    )
                elif form_type == "edit":
                    # For edit, check all projects except the one being edited
                    priority_conflict = any(
                        p.get("priority") == priority
                        and p.get("name") != project_data.get("name")
                        for p in st.session_state.data["projects"]
                    )

                if priority_conflict:
                    display_form_feedback(
                        False,
                        f"Priority {priority} is already taken by another project",
                        [
                            "Each project must have a unique priority. Please select a different value."
                        ],
                    )
                    return

                # Create project data dictionary
                new_project_data = {
                    "name": name,
                    "description": description,
                    "start_date": start_date.strftime("%Y-%m-%d"),
                    "end_date": end_date.strftime("%Y-%m-%d"),
                    "priority": priority,
                    "allocated_budget": float(allocated_budget),  # Ensure it's float
                    "assigned_resources": assigned_resources,
                }

                # Add resource allocations if any resources are assigned
                if assigned_resources:
                    new_project_data["resource_allocations"] = resource_allocations

                # Execute callback if provided
                if on_submit:
                    try:
                        on_submit(new_project_data)
                        st.success(
                            f"Project {name} successfully {'updated' if is_editing else 'added'}!"
                        )

                        # Reset form visibility
                        if form_type == "add":
                            st.session_state.show_add_project_form = False
                        elif form_type == "edit":
                            st.session_state.show_edit_project_form = False

                        # Schedule a rerun after the form is processed
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
                        return

            # For delete, just pass the name
            elif on_submit and project_data:
                try:
                    on_submit({"name": project_data.get("name", "")})
                    st.success(
                        f"Project {project_data.get('name', '')} successfully deleted!"
                    )

                    # Reset form visibility
                    st.session_state.show_delete_project_form = False

                    # Schedule a rerun after the form is processed
                    st.rerun()
                except Exception as e:
                    st.error(f"Error deleting project: {str(e)}")
                    return
