"""
Project CRUD operations module.

This module provides functions for creating, reading, updating, and deleting projects.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from validation import validate_name_field, validate_date_range, validate_project_input
from configuration import load_currency_settings


def add_project_form():
    """Display form for adding a new project."""
    with st.expander("Add New Project", expanded=False):
        with st.form("add_project_form"):
            # Basic project information
            name = st.text_input("Project Name")

            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Start Date", value=datetime.now().date())
            with col2:
                end_date = st.date_input(
                    "End Date", value=(datetime.now() + timedelta(days=30)).date()
                )

            # Priority
            priority = st.slider(
                "Priority", min_value=1, max_value=5, value=3, help="1 = Low, 5 = High"
            )

            # Budget
            currency, _ = load_currency_settings()
            allocated_budget = st.number_input(
                f"Allocated Budget ({currency})", min_value=0.0, step=1000.0
            )

            # Resource assignment
            st.write("**Resource Assignment**")

            # Initialize session state for resource selection
            if "new_project_people" not in st.session_state:
                st.session_state.new_project_people = []

            if "new_project_teams" not in st.session_state:
                st.session_state.new_project_teams = []

            # Tabs for different resource types
            resource_tabs = st.tabs(["People", "Teams", "Departments"])

            with resource_tabs[0]:
                # Get all people
                people = [p["name"] for p in st.session_state.data["people"]]
                selected_people = st.multiselect(
                    "Select People",
                    options=people,
                    default=st.session_state.new_project_people,
                )
                st.session_state.new_project_people = selected_people

            with resource_tabs[1]:
                # Get all teams
                teams = [t["name"] for t in st.session_state.data["teams"]]
                selected_teams = st.multiselect(
                    "Select Teams",
                    options=teams,
                    default=st.session_state.new_project_teams,
                )
                st.session_state.new_project_teams = selected_teams

            with resource_tabs[2]:
                # Get all departments
                departments = [d["name"] for d in st.session_state.data["departments"]]
                selected_departments = st.multiselect(
                    "Select Departments", options=departments
                )

            # Project description
            description = st.text_area("Project Description")

            submitted = st.form_submit_button("Add Project")

            if submitted:
                # Validate project inputs
                if not validate_name_field(name, "project"):
                    st.error("Invalid project name. Please try again.")
                    return

                if not validate_date_range(start_date, end_date):
                    st.error("End date must be after or equal to start date.")
                    return

                # Check if project name is unique
                if any(p["name"] == name for p in st.session_state.data["projects"]):
                    st.error(f"Project '{name}' already exists.")
                    return

                # Combine all selected resources
                all_resources = selected_people + selected_teams + selected_departments

                if not all_resources:
                    st.warning("No resources assigned to project. Are you sure?")

                # Create project object
                project = {
                    "name": name,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "priority": priority,
                    "assigned_resources": all_resources,
                    "description": description,
                    "allocated_budget": allocated_budget,
                }

                # Add project to session state
                st.session_state.data["projects"].append(project)

                # Reset resource selection
                st.session_state.new_project_people = []
                st.session_state.new_project_teams = []

                st.success(f"Project '{name}' added successfully.")
                st.rerun()


def edit_project_form():
    """Display form for editing a project."""
    if not st.session_state.data["projects"]:
        return

    with st.expander("Edit Project", expanded=False):
        # Project selection
        project_names = [p["name"] for p in st.session_state.data["projects"]]
        selected_project_name = st.selectbox(
            "Select Project to Edit", options=project_names, key="edit_project_select"
        )

        # Get the selected project
        project = next(
            (
                p
                for p in st.session_state.data["projects"]
                if p["name"] == selected_project_name
            ),
            None,
        )

        if not project:
            st.info("Please select a project to edit.")
            return

        # Initialize edit form state if needed
        if (
            "last_edited_project" not in st.session_state
            or st.session_state.last_edited_project != selected_project_name
            or not st.session_state.get("edit_form_initialized", False)
        ):
            st.session_state.last_edited_project = selected_project_name

            # Parse assigned resources
            assigned_resources = project.get("assigned_resources", [])

            # Determine resource types (simplified approach)
            people = [p["name"] for p in st.session_state.data["people"]]
            teams = [t["name"] for t in st.session_state.data["teams"]]
            departments = [d["name"] for d in st.session_state.data["departments"]]

            project_people = [r for r in assigned_resources if r in people]
            project_teams = [r for r in assigned_resources if r in teams]
            project_departments = [r for r in assigned_resources if r in departments]

            st.session_state.edit_project_people = project_people
            st.session_state.edit_project_teams = project_teams
            st.session_state.edit_project_departments = project_departments
            st.session_state.edit_form_initialized = True

        with st.form("edit_project_form"):
            # Basic project information
            name = st.text_input("Project Name", value=project["name"])

            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input(
                    "Start Date", value=pd.to_datetime(project["start_date"]).date()
                )
            with col2:
                end_date = st.date_input(
                    "End Date", value=pd.to_datetime(project["end_date"]).date()
                )

            # Priority
            priority = st.slider(
                "Priority",
                min_value=1,
                max_value=5,
                value=project["priority"],
                help="1 = Low, 5 = High",
            )

            # Budget
            currency, _ = load_currency_settings()
            allocated_budget = st.number_input(
                f"Allocated Budget ({currency})",
                min_value=0.0,
                value=float(project.get("allocated_budget", 0)),
                step=1000.0,
            )

            # Resource assignment
            st.write("**Resource Assignment**")

            # Tabs for different resource types
            resource_tabs = st.tabs(["People", "Teams", "Departments"])

            with resource_tabs[0]:
                # Get all people
                people = [p["name"] for p in st.session_state.data["people"]]
                selected_people = st.multiselect(
                    "Select People",
                    options=people,
                    default=st.session_state.edit_project_people,
                )
                st.session_state.edit_project_people = selected_people

            with resource_tabs[1]:
                # Get all teams
                teams = [t["name"] for t in st.session_state.data["teams"]]
                selected_teams = st.multiselect(
                    "Select Teams",
                    options=teams,
                    default=st.session_state.edit_project_teams,
                )
                st.session_state.edit_project_teams = selected_teams

            with resource_tabs[2]:
                # Get all departments
                departments = [d["name"] for d in st.session_state.data["departments"]]
                # Use the persisted value if it exists
                default_deps = getattr(st.session_state, "edit_project_departments", [])
                selected_departments = st.multiselect(
                    "Select Departments", options=departments, default=default_deps
                )
                # Store the value for persistence
                st.session_state.edit_project_departments = selected_departments

            # Project description
            description = st.text_area(
                "Project Description", value=project.get("description", "")
            )

            submit_update = st.form_submit_button("Update Project")

            if submit_update:
                # Validate project inputs
                if not validate_name_field(name, "project"):
                    st.error("Invalid project name. Please try again.")
                    return

                if not validate_date_range(start_date, end_date):
                    st.error("End date must be after or equal to start date.")
                    return

                # Check for name conflicts
                if name != project["name"] and any(
                    p["name"] == name for p in st.session_state.data["projects"]
                ):
                    st.error(f"Project '{name}' already exists.")
                    return

                # Combine all selected resources
                all_resources = selected_people + selected_teams + selected_departments

                if not all_resources:
                    st.warning("No resources assigned to project. Are you sure?")

                # Update project
                project["name"] = name
                project["start_date"] = start_date.isoformat()
                project["end_date"] = end_date.isoformat()
                project["priority"] = priority
                project["assigned_resources"] = all_resources
                project["description"] = description
                project["allocated_budget"] = allocated_budget

                st.success(f"Project '{name}' updated successfully.")
                st.rerun()


def delete_project_form():
    """Display form for deleting a project."""
    if not st.session_state.data["projects"]:
        return

    with st.expander("Delete Project", expanded=False):
        # Project selection
        project_names = [p["name"] for p in st.session_state.data["projects"]]
        selected_project = st.selectbox(
            "Select Project to Delete",
            options=[""] + project_names,
            key="delete_project_select",
        )

        if not selected_project:
            st.info("Please select a project to delete.")
            return

        # Find project details for confirmation
        project = next(
            (
                p
                for p in st.session_state.data["projects"]
                if p["name"] == selected_project
            ),
            None,
        )

        if project:
            # Display project details for confirmation
            st.write(f"**Project:** {project['name']}")
            st.write(f"**Duration:** {project['start_date']} to {project['end_date']}")
            st.write(f"**Priority:** {project['priority']}")
            st.write(f"**Resources:** {len(project.get('assigned_resources', []))}")

            # Confirmation mechanism
            from utils import confirm_action

            if confirm_action(f"deleting project {selected_project}", "delete_project"):
                # Remove project
                st.session_state.data["projects"] = [
                    p
                    for p in st.session_state.data["projects"]
                    if p["name"] != selected_project
                ]

                st.success(f"Project '{selected_project}' deleted successfully.")
                st.rerun()
