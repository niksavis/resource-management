"""
Project Management UI module.

This module provides the UI components for managing projects.
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any

from app.utils.ui_components import display_action_bar, paginate_dataframe
from app.services.config_service import load_display_preferences
from app.services.data_service import parse_resources


def display_manage_projects_tab():
    """Display the project management tab with project list and CRUD forms."""
    display_action_bar()
    st.subheader("Project Management")

    # Create and filter projects dataframe
    if st.session_state.data["projects"]:
        projects_df = _create_projects_dataframe()
        projects_df = _filter_projects_dataframe(projects_df)
        st.dataframe(projects_df, use_container_width=True)
    else:
        st.warning("No projects found. Please add a project first.")

    # Project CRUD Forms in expanders
    with st.expander("➕ Add Project"):
        add_project_form()

    if st.session_state.data["projects"]:
        with st.expander("✏️ Edit Project"):
            edit_project_form()

        with st.expander("🗑️ Delete Project"):
            delete_project_form()


def _create_projects_dataframe() -> pd.DataFrame:
    """
    Create a DataFrame from project data.

    Returns:
        DataFrame with project information
    """
    return pd.DataFrame(
        [
            {
                "Name": p["name"],
                "Start Date": pd.to_datetime(p["start_date"]).strftime("%Y-%m-%d"),
                "End Date": pd.to_datetime(p["end_date"]).strftime("%Y-%m-%d"),
                "Priority": p["priority"],
                "Duration (Days)": (
                    pd.to_datetime(p["end_date"]) - pd.to_datetime(p["start_date"])
                ).days
                + 1,
                "Budget": p.get("allocated_budget", 0),
                "Assigned People": parse_resources(p["assigned_resources"])[0],
                "Assigned Teams": parse_resources(p["assigned_resources"])[1],
                "Assigned Departments": parse_resources(p["assigned_resources"])[2],
            }
            for p in st.session_state.data["projects"]
        ]
    )


def _filter_projects_dataframe(projects_df: pd.DataFrame) -> pd.DataFrame:
    """
    Filter projects DataFrame based on user-selected filters.

    Args:
        projects_df: DataFrame containing project data

    Returns:
        Filtered DataFrame
    """
    with st.expander("Search and Filter Projects", expanded=False):
        col1, col2 = st.columns([1, 1])

        with col1:
            search_term = st.text_input("Search Projects", key="search_projects")

        with col2:
            date_range = st.date_input(
                "Filter by Date Range",
                value=(
                    pd.to_datetime(projects_df["Start Date"]).min().date(),
                    pd.to_datetime(projects_df["End Date"]).max().date(),
                ),
                min_value=pd.to_datetime(projects_df["Start Date"]).min().date(),
                max_value=pd.to_datetime(projects_df["End Date"]).max().date(),
            )

        # Resource filters
        col3, col4, col5 = st.columns(3)

        with col3:
            people_filter = st.multiselect(
                "Filter by Assigned People",
                options=[p["name"] for p in st.session_state.data["people"]],
                default=[],
                key="filter_people_projects",
            )

        with col4:
            teams_filter = st.multiselect(
                "Filter by Assigned Team",
                options=[t["name"] for t in st.session_state.data["teams"]],
                default=[],
                key="filter_teams_projects",
            )

        with col5:
            departments_filter = st.multiselect(
                "Filter by Assigned Department",
                options=[d["name"] for d in st.session_state.data["departments"]],
                default=[],
                key="filter_departments_projects",
            )

        # Sort options
        sort_col, sort_dir = st.columns(2)
        with sort_col:
            sort_by = st.selectbox(
                "Sort by",
                options=[
                    "Name",
                    "Start Date",
                    "End Date",
                    "Priority",
                    "Duration (Days)",
                    "Budget",
                ],
                index=3,  # Default to Priority
                key="sort_by_projects",
            )

        with sort_dir:
            sort_ascending = st.checkbox(
                "Ascending", value=True, key="sort_ascending_projects"
            )

        # Apply search filter
        if search_term:
            mask = np.column_stack(
                [
                    projects_df[col]
                    .fillna("")
                    .astype(str)
                    .str.contains(search_term, case=False, na=False)
                    for col in projects_df.columns
                ]
            )
            projects_df = projects_df[mask.any(axis=1)]

        # Apply date filter
        if len(date_range) == 2:
            start_date, end_date = (
                pd.to_datetime(date_range[0]),
                pd.to_datetime(date_range[1]),
            )
            projects_df = projects_df[
                (pd.to_datetime(projects_df["Start Date"]) >= start_date)
                & (pd.to_datetime(projects_df["End Date"]) <= end_date)
            ]

        # Apply resource filters
        if people_filter:
            projects_df = projects_df[
                projects_df["Assigned People"].apply(
                    lambda x: any(person in x for person in people_filter)
                )
            ]

        if teams_filter:
            projects_df = projects_df[
                projects_df["Assigned Teams"].apply(
                    lambda x: any(team in x for team in teams_filter)
                )
            ]

        if departments_filter:
            projects_df = projects_df[
                projects_df["Assigned Departments"].apply(
                    lambda x: any(dept in x for dept in departments_filter)
                )
            ]

        # Apply sorting
        projects_df = projects_df.sort_values(by=sort_by, ascending=sort_ascending)

        # Apply pagination with configured page size
        display_prefs = load_display_preferences()
        page_size = display_prefs.get("page_size", 10)
        projects_df = paginate_dataframe(
            projects_df, "projects", items_per_page=page_size
        )

    return projects_df


def add_project_form():
    """Form to add a project."""
    st.write("### Add New Project")

    project_name = st.text_input("Project Name", key="add_project_name")
    project_desc = st.text_area("Description", key="add_project_desc")

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "Start Date", value=datetime.now(), key="add_project_start"
        )
    with col2:
        end_date = st.date_input(
            "End Date", value=datetime.now() + timedelta(days=30), key="add_project_end"
        )

    # Calculate default priority
    existing_priorities = [
        p.get("priority", 0) for p in st.session_state.data["projects"]
    ]
    default_priority = 1 if not existing_priorities else max(existing_priorities) + 1

    priority = st.number_input(
        "Priority (1 is highest)",
        min_value=1,
        value=default_priority,
        help="Each project must have a unique priority. Lower number = higher priority.",
        key="add_project_priority",
    )

    budget = st.number_input(
        "Budget", min_value=0.0, step=1000.0, format="%.2f", key="add_project_budget"
    )

    # Resource assignment
    st.markdown("### Resource Assignment")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("#### 👤 People")
        people = st.multiselect(
            "Select People",
            options=[p["name"] for p in st.session_state.data["people"]],
            key="add_project_people",
        )

    with col2:
        st.markdown("#### 👥 Teams")
        teams = st.multiselect(
            "Select Teams",
            options=[t["name"] for t in st.session_state.data["teams"]],
            key="add_project_teams",
        )

    with col3:
        st.markdown("#### 🏢 Departments")
        departments = st.multiselect(
            "Select Departments",
            options=[d["name"] for d in st.session_state.data["departments"]],
            key="add_project_departments",
        )

    # Combined resources
    resources = people + teams + departments

    # Resource allocation section
    if resources:
        st.markdown("### Resource Allocation")
        st.info(
            "Set allocation percentage and time period for each resource. Time periods must be within project dates."
        )

        resource_allocations = []

        for resource in resources:
            # Determine resource type
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

            st.markdown(f"#### {resource_icon} {resource} ({resource_type})")

            col1, col2, col3 = st.columns([1, 2, 2])

            with col1:
                allocation_pct = st.slider(
                    f"Allocation %",
                    min_value=10,
                    max_value=100,
                    value=100,
                    step=10,
                    key=f"add_project_alloc_{resource}",
                )

            with col2:
                resource_start = st.date_input(
                    f"Start Date",
                    value=start_date,
                    min_value=start_date,
                    max_value=end_date,
                    key=f"add_project_start_{resource}",
                )

            with col3:
                resource_end = st.date_input(
                    f"End Date",
                    value=end_date,
                    min_value=resource_start,
                    max_value=end_date,
                    key=f"add_project_end_{resource}",
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

            st.divider()

    if st.button("Add Project", type="primary", key="add_project_submit"):
        # Validation
        errors = []

        if not project_name:
            errors.append("Project name is required")

        if start_date > end_date:
            errors.append("Start date must be before end date")

        if any(p["name"] == project_name for p in st.session_state.data["projects"]):
            errors.append(f"Project '{project_name}' already exists")

        if any(p["priority"] == priority for p in st.session_state.data["projects"]):
            errors.append(f"Priority {priority} is already assigned to another project")

        if not resources:
            errors.append("At least one resource must be assigned")

        if errors:
            for error in errors:
                st.error(error)
        else:
            # Create project
            new_project = {
                "name": project_name,
                "description": project_desc,
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                "priority": priority,
                "allocated_budget": float(budget),
                "assigned_resources": resources,
            }

            # Add resource allocations
            if resources:
                new_project["resource_allocations"] = resource_allocations

            # Add to session state
            st.session_state.data["projects"].append(new_project)
            st.success(f"Project '{project_name}' added successfully!")
            st.rerun()


def edit_project_form():
    """Form to edit a project."""
    st.write("### Edit Project")

    # Project selection
    project_names = [p["name"] for p in st.session_state.data["projects"]]
    selected_project = st.selectbox(
        "Select Project", options=project_names, key="edit_project_select"
    )

    # Find the selected project
    project = next(
        (p for p in st.session_state.data["projects"] if p["name"] == selected_project),
        None,
    )

    if project:
        project_name = st.text_input(
            "Project Name", value=project["name"], key="edit_project_name"
        )
        project_desc = st.text_area(
            "Description", value=project.get("description", ""), key="edit_project_desc"
        )

        col1, col2 = st.columns(2)
        with col1:
            # Use get() with default value for start_date
            default_start = datetime.now()
            try:
                if "start_date" in project:
                    default_start = pd.to_datetime(project["start_date"])
            except:
                pass

            start_date = st.date_input(
                "Start Date",
                value=default_start,
                key="edit_project_start",
            )
        with col2:
            # Use get() with default value for end_date
            default_end = datetime.now() + timedelta(days=30)
            try:
                if "end_date" in project:
                    default_end = pd.to_datetime(project["end_date"])
            except:
                pass

            end_date = st.date_input(
                "End Date",
                value=default_end,
                key="edit_project_end",
            )

        priority = st.number_input(
            "Priority (1 is highest)",
            min_value=1,
            value=project.get("priority", 1),
            help="Each project must have a unique priority. Lower number = higher priority.",
            key="edit_project_priority",
        )

        budget = st.number_input(
            "Budget",
            min_value=0.0,
            value=project.get("allocated_budget", 0.0),
            step=1000.0,
            format="%.2f",
            key="edit_project_budget",
        )

        # Resource assignment
        st.markdown("### Resource Assignment")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("#### 👤 People")
            people = st.multiselect(
                "Select People",
                options=[p["name"] for p in st.session_state.data["people"]],
                default=[
                    r
                    for r in project.get("assigned_resources", [])
                    if r in [p["name"] for p in st.session_state.data["people"]]
                ],
                key="edit_project_people",
            )

        with col2:
            st.markdown("#### 👥 Teams")
            teams = st.multiselect(
                "Select Teams",
                options=[t["name"] for t in st.session_state.data["teams"]],
                default=[
                    r
                    for r in project.get("assigned_resources", [])
                    if r in [t["name"] for t in st.session_state.data["teams"]]
                ],
                key="edit_project_teams",
            )

        with col3:
            st.markdown("#### 🏢 Departments")
            departments = st.multiselect(
                "Select Departments",
                options=[d["name"] for d in st.session_state.data["departments"]],
                default=[
                    r
                    for r in project.get("assigned_resources", [])
                    if r in [d["name"] for d in st.session_state.data["departments"]]
                ],
                key="edit_project_departments",
            )

        # Combined resources
        resources = people + teams + departments

        # Resource allocation section
        if resources:
            st.markdown("### Resource Allocation")
            st.info(
                "Set allocation percentage and time period for each resource. Time periods must be within project dates."
            )

            # Get existing allocations if available
            existing_allocations = project.get("resource_allocations", [])
            resource_allocations = []

            for resource in resources:
                # Determine resource type
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

                st.markdown(f"#### {resource_icon} {resource} ({resource_type})")

                col1, col2, col3 = st.columns([1, 2, 2])

                with col1:
                    allocation_pct = st.slider(
                        f"Allocation %",
                        min_value=10,
                        max_value=100,
                        value=existing["allocation_percentage"] if existing else 100,
                        step=10,
                        key=f"edit_project_alloc_{resource}",
                    )

                with col2:
                    resource_start = st.date_input(
                        f"Start Date",
                        value=pd.to_datetime(existing["start_date"])
                        if existing
                        else start_date,
                        min_value=start_date,
                        max_value=end_date,
                        key=f"edit_project_start_{resource}",
                    )

                with col3:
                    resource_end = st.date_input(
                        f"End Date",
                        value=pd.to_datetime(existing["end_date"])
                        if existing
                        else end_date,
                        min_value=resource_start,
                        max_value=end_date,
                        key=f"edit_project_end_{resource}",
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

                st.divider()

        if st.button("Update Project", type="primary", key="edit_project_submit"):
            # Validation
            errors = []

            if not project_name:
                errors.append("Project name is required")

            if start_date > end_date:
                errors.append("Start date must be before end date")

            # Check for duplicate name only if the name was changed
            if project_name != project["name"] and any(
                p["name"] == project_name for p in st.session_state.data["projects"]
            ):
                errors.append(f"Project '{project_name}' already exists")

            # Check for duplicate priority only if the priority was changed
            if priority != project["priority"] and any(
                p["priority"] == priority and p["name"] != project["name"]
                for p in st.session_state.data["projects"]
            ):
                errors.append(
                    f"Priority {priority} is already assigned to another project"
                )

            if not resources:
                errors.append("At least one resource must be assigned")

            if errors:
                for error in errors:
                    st.error(error)
            else:
                # Find the project index
                project_index = next(
                    (
                        i
                        for i, p in enumerate(st.session_state.data["projects"])
                        if p["name"] == selected_project
                    ),
                    None,
                )

                if project_index is not None:
                    # Create updated project
                    updated_project = {
                        "name": project_name,
                        "description": project_desc,
                        "start_date": start_date.strftime("%Y-%m-%d"),
                        "end_date": end_date.strftime("%Y-%m-%d"),
                        "priority": priority,
                        "allocated_budget": float(budget),
                        "assigned_resources": resources,
                    }

                    # Add resource allocations
                    if resources:
                        updated_project["resource_allocations"] = resource_allocations

                    # Update in session state
                    st.session_state.data["projects"][project_index] = updated_project
                    st.success(f"Project '{project_name}' updated successfully!")
                    st.rerun()


def delete_project_form():
    """Form to delete a project."""
    st.write("### Delete Project")

    # Project selection
    project_names = [p["name"] for p in st.session_state.data["projects"]]
    selected_project = st.selectbox(
        "Select Project to Delete", options=project_names, key="delete_project_select"
    )

    # Show project details to confirm
    project = next(
        (p for p in st.session_state.data["projects"] if p["name"] == selected_project),
        None,
    )

    if project:
        st.write(f"**Project:** {project['name']}")
        st.write(f"**Description:** {project.get('description', 'N/A')}")
        st.write(f"**Duration:** {project['start_date']} to {project['end_date']}")
        st.write(f"**Priority:** {project['priority']}")
        st.write(f"**Budget:** {project.get('allocated_budget', 0)}")
        st.write(f"**Resources:** {', '.join(project['assigned_resources'])}")

        st.warning(
            "⚠️ This action cannot be undone. All project data will be permanently deleted."
        )

    if st.checkbox(
        "I confirm I want to delete this project", key="delete_project_confirm"
    ):
        if st.button("Delete Project", type="primary", key="delete_project_submit"):
            # Find and delete the project
            project_index = next(
                (
                    i
                    for i, p in enumerate(st.session_state.data["projects"])
                    if p["name"] == selected_project
                ),
                None,
            )

            if project_index is not None:
                del st.session_state.data["projects"][project_index]
                st.success(f"Project '{selected_project}' deleted successfully!")
                st.rerun()
