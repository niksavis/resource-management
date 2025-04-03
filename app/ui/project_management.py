"""
Project Management UI module.

This module provides the UI components for managing projects.
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from app.utils.ui_components import display_action_bar, paginate_dataframe
from app.services.config_service import load_display_preferences, load_currency_settings
from app.services.data_service import parse_resources


def display_manage_projects_tab():
    """Display the project management tab with project list and CRUD forms."""
    display_action_bar()
    st.subheader("Project Management")

    # Create tabs similar to resource management
    project_tabs = st.tabs(["All Projects", "Manage Projects"])

    with project_tabs[0]:
        display_projects_overview()

    with project_tabs[1]:
        display_projects_management()


def display_projects_overview():
    """Display the projects overview with cards."""
    st.write("### Projects Overview")

    # Only proceed if there are projects
    if not st.session_state.data["projects"]:
        st.info("No projects found. Please add a project first.")
        return

    # Create projects dataframe
    projects_df = _create_projects_dataframe()
    projects = st.session_state.data["projects"]

    # Search, Sort, and Filter UI
    with st.expander("🔍 Search, Sort, and Filter Projects", expanded=False):
        # First row: Search, Date Range, and Sort options
        col1, col2, col3 = st.columns([1, 1, 1])

        with col1:
            search_term = st.text_input("Search Projects", key="search_projects_cards")

        with col2:
            date_range = st.date_input(
                "Filter by Date Range",
                value=(
                    pd.to_datetime(projects_df["Start Date"]).min().date(),
                    pd.to_datetime(projects_df["End Date"]).max().date(),
                ),
                min_value=pd.to_datetime(projects_df["Start Date"]).min().date(),
                max_value=pd.to_datetime(projects_df["End Date"]).max().date(),
                key="date_range_cards",
            )

        with col3:
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
                key="sort_by_projects_cards",
            )
            sort_ascending = st.checkbox(
                "Ascending", value=True, key="sort_ascending_projects_cards"
            )

        # Second row: Resource filters
        col5, col6, col7 = st.columns(3)

        with col5:
            people_filter = st.multiselect(
                "Filter by Assigned People",
                options=[p["name"] for p in st.session_state.data["people"]],
                default=[],
                key="filter_people_projects_cards",
            )

        with col6:
            teams_filter = st.multiselect(
                "Filter by Assigned Team",
                options=[t["name"] for t in st.session_state.data["teams"]],
                default=[],
                key="filter_teams_projects_cards",
            )

        with col7:
            departments_filter = st.multiselect(
                "Filter by Assigned Department",
                options=[d["name"] for d in st.session_state.data["departments"]],
                default=[],
                key="filter_departments_projects_cards",
            )

    # Filter projects based on search and filters
    filtered_projects = projects.copy()

    # Apply search filter
    if search_term:
        filtered_projects = [
            p for p in filtered_projects if search_term.lower() in str(p).lower()
        ]

    # Apply date filter
    if len(date_range) == 2:
        start_date, end_date = (
            pd.to_datetime(date_range[0]),
            pd.to_datetime(date_range[1]),
        )
        filtered_projects = [
            p
            for p in filtered_projects
            if (
                pd.to_datetime(p["start_date"]) >= start_date
                and pd.to_datetime(p["end_date"]) <= end_date
            )
        ]

    # Apply resource filters
    if people_filter:
        filtered_projects = [
            p
            for p in filtered_projects
            if any(
                person in p.get("assigned_resources", []) for person in people_filter
            )
        ]

    if teams_filter:
        filtered_projects = [
            p
            for p in filtered_projects
            if any(team in p.get("assigned_resources", []) for team in teams_filter)
        ]

    if departments_filter:
        filtered_projects = [
            p
            for p in filtered_projects
            if any(
                dept in p.get("assigned_resources", []) for dept in departments_filter
            )
        ]

    # Apply sorting
    if sort_by == "Name":
        filtered_projects.sort(key=lambda p: p["name"], reverse=not sort_ascending)
    elif sort_by == "Start Date":
        filtered_projects.sort(
            key=lambda p: p["start_date"], reverse=not sort_ascending
        )
    elif sort_by == "End Date":
        filtered_projects.sort(key=lambda p: p["end_date"], reverse=not sort_ascending)
    elif sort_by == "Priority":
        filtered_projects.sort(key=lambda p: p["priority"], reverse=not sort_ascending)
    elif sort_by == "Duration (Days)":
        filtered_projects.sort(
            key=lambda p: (
                pd.to_datetime(p["end_date"]) - pd.to_datetime(p["start_date"])
            ).days
            + 1,
            reverse=not sort_ascending,
        )
    elif sort_by == "Budget":
        filtered_projects.sort(
            key=lambda p: p.get("allocated_budget", 0), reverse=not sort_ascending
        )

    # Display projects as cards
    _display_project_cards(filtered_projects)


def _display_project_cards(projects):
    """Display project cards in a consistent grid."""
    currency, _ = load_currency_settings()

    # Display projects summary
    total_projects = len(projects)
    if total_projects > 0:
        avg_budget = (
            sum(p.get("allocated_budget", 0) for p in projects) / total_projects
        )
        st.write(f"**Total Projects:** {total_projects}")
        st.write(f"**Average Budget:** {currency} {avg_budget:,.2f}")

    # Create grid of cards
    cols = st.columns(3)
    for idx, project in enumerate(projects):
        with cols[idx % 3]:
            with st.container():
                # Calculate duration
                start_date = pd.to_datetime(project["start_date"])
                end_date = pd.to_datetime(project["end_date"])
                duration = (end_date - start_date).days + 1

                # Parse resources
                people, teams, departments = parse_resources(
                    project["assigned_resources"]
                )

                # Create priority background color based on priority
                # Higher priority (lower number) gets more saturated color
                priority_color = (
                    f"rgba(255,99,71,{min(1.0, 1.0 / project['priority'])})"
                )

                # Display card with project info
                st.markdown(
                    f"""
                    <div class="card project-card">
                        <h3>📋 {project["name"]}</h3>
                        <div style="background-color: {priority_color}; padding: 5px; border-radius: 4px; margin-bottom: 10px;">
                            <span style="font-weight: bold;">Priority: {project["priority"]}</span>
                        </div>
                        <p><strong>Duration:</strong> {start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")}</p>
                        <p><strong>Days:</strong> {duration}</p>
                        <p><strong>Budget:</strong> {currency} {project.get("allocated_budget", 0):,.2f}</p>
                        <p><strong>Resources:</strong> {len(people)} people, {len(teams)} teams, {len(departments)} departments</p>
                        <p><strong>Description:</strong> {project.get("description", "")[:50]}{"..." if len(project.get("description", "")) > 50 else ""}</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


def display_projects_management():
    """Display the project management functionality with CRUD forms."""
    st.write("### Manage Projects")

    # Create and filter projects dataframe
    if st.session_state.data["projects"]:
        projects_df = _create_projects_dataframe()
        projects_df = _filter_projects_dataframe(projects_df)

        # Ensure horizontal scrolling is available if needed
        st.markdown(
            """
            <style>
            .stDataFrame {
                width: 100%;
                overflow-x: auto;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
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
    # Use a cache key to store the dataframe
    if "projects_df_cache" not in st.session_state:
        # Load currency settings
        currency, _ = load_currency_settings()

        st.session_state["projects_df_cache"] = pd.DataFrame(
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
                    "Budget": f"{currency} {p.get('allocated_budget', 0):,.2f}",
                    "Assigned People": parse_resources(p["assigned_resources"])[0],
                    "Assigned Teams": parse_resources(p["assigned_resources"])[1],
                    "Assigned Departments": parse_resources(p["assigned_resources"])[2],
                }
                for p in st.session_state.data["projects"]
            ]
        )

    return st.session_state["projects_df_cache"]


def _filter_projects_dataframe(projects_df: pd.DataFrame) -> pd.DataFrame:
    """
    Filter projects DataFrame based on user-selected filters.

    Args:
        projects_df: DataFrame containing project data

    Returns:
        Filtered DataFrame
    """
    # Clear the cached dataframe when filters are changed
    filter_key = "project_filter_changed"

    with st.expander("🔍 Search, Sort, and Filter Projects", expanded=False):
        # First row: Search, Date Range, and Sort options
        col1, col2, col3 = st.columns([1, 1, 1])

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

        with col3:
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
            sort_ascending = st.checkbox(
                "Ascending", value=True, key="sort_ascending_projects"
            )

        # Second row: Resource filters
        col5, col6, col7 = st.columns(3)

        with col5:
            people_filter = st.multiselect(
                "Filter by Assigned People",
                options=[p["name"] for p in st.session_state.data["people"]],
                default=[],
                key="filter_people_projects",
            )

        with col6:
            teams_filter = st.multiselect(
                "Filter by Assigned Team",
                options=[t["name"] for t in st.session_state.data["teams"]],
                default=[],
                key="filter_teams_projects",
            )

        with col7:
            departments_filter = st.multiselect(
                "Filter by Assigned Department",
                options=[d["name"] for d in st.session_state.data["departments"]],
                default=[],
                key="filter_departments_projects",
            )

        # Apply filters (any filter change should update the UI)
        if any_filter_changed():
            if "projects_df_cache" in st.session_state:
                del st.session_state["projects_df_cache"]
            if filter_key not in st.session_state:
                st.session_state[filter_key] = True
                st.rerun()

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
    projects_df = paginate_dataframe(projects_df, "projects", items_per_page=page_size)

    return projects_df


def any_filter_changed() -> bool:
    """Check if any filter has changed since last render."""
    filter_keys = [
        "search_projects",
        "sort_by_projects",
        "sort_ascending_projects",
        "filter_people_projects",
        "filter_teams_projects",
        "filter_departments_projects",
    ]

    current_values = {
        key: st.session_state.get(key) for key in filter_keys if key in st.session_state
    }

    if "prev_filter_values" not in st.session_state:
        st.session_state["prev_filter_values"] = current_values
        return False

    changed = current_values != st.session_state["prev_filter_values"]
    st.session_state["prev_filter_values"] = current_values

    return changed


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
                    "Allocation %",
                    min_value=10,
                    max_value=100,
                    value=100,
                    step=10,
                    key=f"add_project_alloc_{resource}",
                )

            with col2:
                resource_start = st.date_input(
                    "Start Date",
                    value=start_date,
                    min_value=start_date,
                    max_value=end_date,
                    key=f"add_project_start_{resource}",
                )

            with col3:
                resource_end = st.date_input(
                    "End Date",
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

            # Clear the dataframe cache to force a refresh of the table
            if "projects_df_cache" in st.session_state:
                del st.session_state["projects_df_cache"]

            # Display a more prominent success message
            st.success(f"✅ Project '{project_name}' added successfully!")

            # Clear any form state to prepare for next add
            for key in list(st.session_state.keys()):
                if key.startswith("add_project_"):
                    del st.session_state[key]

            # Refresh UI immediately
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
        # Edit form
        project_name = st.text_input(
            "Project Name", value=project["name"], key="edit_project_name"
        )
        project_desc = st.text_area(
            "Description", value=project.get("description", ""), key="edit_project_desc"
        )

        col1, col2 = st.columns(2)
        with col1:
            # Format dates for date input
            start_date = pd.to_datetime(project["start_date"]).date()
            start_date = st.date_input(
                "Start Date", value=start_date, key="edit_project_start_date"
            )

        with col2:
            end_date = pd.to_datetime(project["end_date"]).date()
            end_date = st.date_input(
                "End Date", value=end_date, key="edit_project_end_date"
            )

        # Use str(project["priority"]) to ensure consistent session state keys
        priority_key = f"edit_project_priority_{selected_project}"

        # Initialize session state for priority if not already done
        if priority_key not in st.session_state:
            st.session_state[priority_key] = int(project["priority"])

        priority = st.number_input(
            "Priority (1 is highest)",
            min_value=1,
            value=st.session_state[priority_key],
            key=priority_key,
        )

        # Convert budget to float before passing to number_input to ensure type consistency
        current_budget = float(project.get("allocated_budget", 0))
        budget = st.number_input(
            "Budget",
            min_value=0.0,
            value=current_budget,
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
                        "Allocation %",
                        min_value=10,
                        max_value=100,
                        value=existing["allocation_percentage"] if existing else 100,
                        step=10,
                        key=f"edit_project_alloc_{resource}",
                    )

                with col2:
                    resource_start = st.date_input(
                        "Start Date",
                        value=pd.to_datetime(existing["start_date"])
                        if existing
                        else start_date,
                        min_value=start_date,
                        max_value=end_date,
                        key=f"edit_project_start_{resource}",
                    )

                with col3:
                    resource_end = st.date_input(
                        "End Date",
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

                    # Clear the cached dataframe if it exists to force a refresh
                    if "projects_df_cache" in st.session_state:
                        del st.session_state["projects_df_cache"]

                    # Display a more prominent success message
                    st.success(f"✅ Project '{project_name}' updated successfully!")

                    # Important: Force complete reinitialization of the form
                    for key in list(st.session_state.keys()):
                        if (
                            key.startswith("edit_project_")
                            and key != "edit_project_select"
                        ):
                            del st.session_state[key]

                    # Refresh UI immediately
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

                # Display a more prominent success message
                st.success(f"✅ Project '{selected_project}' deleted successfully!")

                # Refresh UI immediately
                st.rerun()
