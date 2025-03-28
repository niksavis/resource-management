import streamlit as st
import pandas as pd
from validation import validate_project_input
from configuration import load_currency_settings
from utils import confirm_action


def add_project_form():
    with st.expander("Add Project", expanded=False):  # Set expanded=False
        # Initialize session state for resources and allocations
        if "new_project_resources" not in st.session_state:
            st.session_state.new_project_resources = []
        if "new_project_allocations" not in st.session_state:
            st.session_state.new_project_allocations = {}

        # Function to update resource allocations dynamically
        def update_new_project_allocations():
            for resource in st.session_state.new_project_resources:
                if resource not in st.session_state.new_project_allocations:
                    st.session_state.new_project_allocations[resource] = {
                        "allocation_percentage": 100,
                        "start_date": st.session_state.get("add_project_start_date"),
                        "end_date": st.session_state.get("add_project_end_date"),
                    }
            # Remove allocations for unselected resources
            for resource in list(st.session_state.new_project_allocations.keys()):
                if resource not in st.session_state.new_project_resources:
                    del st.session_state.new_project_allocations[resource]

        # Group project details in a single row
        st.markdown("### Project Details")
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Project Name")
        with col2:
            currency, _ = load_currency_settings()
            budget = st.number_input(f"Budget ({currency})", min_value=0.0, step=1000.0)

        # Group date inputs in another row
        st.markdown("### Project Timeline")
        col3, col4 = st.columns(2)
        with col3:
            start_date = st.date_input(
                "Start Date",
                key="add_project_start_date",
            )
        with col4:
            end_date = st.date_input(
                "End Date",
                key="add_project_end_date",
            )

        # Assigned resources section
        st.markdown("### Assigned Resources")
        selected_resources = st.multiselect(
            "Select Resources",
            options=[
                *[p["name"] for p in st.session_state.data["people"]],
                *[t["name"] for t in st.session_state.data["teams"]],
            ],
            default=st.session_state.new_project_resources,
            key="add_assigned_resources",
        )

        # Update session state for assigned resources and allocations
        if selected_resources != st.session_state.new_project_resources:
            st.session_state.new_project_resources = selected_resources
            update_new_project_allocations()
            st.rerun()  # Force rerun to immediately reflect changes

        # Resource allocation section
        st.markdown("### Resource Allocation")
        resource_allocations = []
        for resource in st.session_state.new_project_resources:
            st.markdown(f"**{resource}**")
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                allocation_percentage = st.slider(
                    f"Allocation % for {resource}",
                    min_value=10,
                    max_value=100,
                    value=st.session_state.new_project_allocations[resource][
                        "allocation_percentage"
                    ],
                    step=10,
                    key=f"add_alloc_{resource}",
                )
            with col2:
                resource_start_date = st.date_input(
                    f"Start Date for {resource}",
                    value=st.session_state.new_project_allocations[resource][
                        "start_date"
                    ],
                    min_value=start_date,
                    max_value=end_date,
                    key=f"add_start_{resource}",
                )
            with col3:
                resource_end_date = st.date_input(
                    f"End Date for {resource}",
                    value=st.session_state.new_project_allocations[resource][
                        "end_date"
                    ],
                    min_value=start_date,
                    max_value=end_date,
                    key=f"add_end_{resource}",
                )

            # Update session state with the latest values
            st.session_state.new_project_allocations[resource] = {
                "allocation_percentage": allocation_percentage,
                "start_date": resource_start_date,
                "end_date": resource_end_date,
            }

            resource_allocations.append(
                {
                    "resource": resource,
                    "allocation_percentage": allocation_percentage,
                    "start_date": resource_start_date.strftime("%Y-%m-%d"),
                    "end_date": resource_end_date.strftime("%Y-%m-%d"),
                }
            )

        # Submit button (no form wrapper)
        if st.button("Add Project", key="add_project_button"):
            # Ensure dates are converted to pd.Timestamp
            start_date = pd.to_datetime(start_date)
            end_date = pd.to_datetime(end_date)

            # Pass all fields as a dictionary to match validate_project_input's expected input
            project_data = {
                "name": name,
                "start_date": start_date,
                "end_date": end_date,
                "budget": budget,
            }
            if not validate_project_input(project_data):
                st.error("Invalid project details. Please try again.")
                return

            # Assign the lowest priority (highest number)
            new_priority = (
                max(
                    [p["priority"] for p in st.session_state.data["projects"]],
                    default=0,
                )
                + 1
            )

            st.session_state.data["projects"].append(
                {
                    "name": name,
                    "start_date": start_date.strftime("%Y-%m-%d"),
                    "end_date": end_date.strftime("%Y-%m-%d"),
                    "priority": new_priority,
                    "assigned_resources": st.session_state.new_project_resources,
                    "allocated_budget": budget,
                    "resource_allocations": resource_allocations,
                }
            )
            st.success(
                f"Project '{name}' added successfully with priority {new_priority}."
            )
            st.rerun()


def edit_project_form():
    with st.expander("Edit Project", expanded=False):  # Set expanded=False
        if not st.session_state.data["projects"]:
            st.info("No projects available to edit.")
            return

        project_names = [p["name"] for p in st.session_state.data["projects"]]
        selected_project = st.selectbox(
            "Select Project to Edit",
            project_names,
            key="selected_project",
            on_change=lambda: reset_edit_project_state(),
        )

        project = next(
            (
                p
                for p in st.session_state.data["projects"]
                if p["name"] == selected_project
            ),
            None,
        )

        if project:
            # Initialize session state for dynamic resource rows
            if "selected_resources" not in st.session_state:
                st.session_state.selected_resources = project["assigned_resources"]

            # Callback to update selected resources dynamically
            def update_selected_resources():
                st.session_state.selected_resources = (
                    st.session_state.edit_assigned_resources
                )

            # Group project details in a single row
            st.markdown("### Project Details")
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input(
                    "Project Name", value=project["name"], key="edit_name"
                )
            with col2:
                currency, _ = load_currency_settings()
                budget = st.number_input(
                    f"Budget ({currency})",
                    min_value=0.0,
                    step=1000.0,
                    value=project["allocated_budget"],
                    key="edit_budget",
                )

            # Group date inputs in another row
            st.markdown("### Project Timeline")
            col3, col4 = st.columns(2)
            with col3:
                start_date = st.date_input(
                    "Start Date",
                    value=pd.to_datetime(project["start_date"]),
                    min_value=pd.to_datetime(project["start_date"]),
                    max_value=pd.to_datetime(project["end_date"]),
                    key="edit_start_date",
                )
            with col4:
                end_date = st.date_input(
                    "End Date",
                    value=pd.to_datetime(project["end_date"]),
                    min_value=pd.to_datetime(project["start_date"]),
                    max_value=pd.to_datetime(project["end_date"]),
                    key="edit_end_date",
                )

            # Assigned resources section
            st.markdown("### Assigned Resources")
            st.multiselect(
                "Select Resources",
                options=[
                    *[p["name"] for p in st.session_state.data["people"]],
                    *[t["name"] for t in st.session_state.data["teams"]],
                ],
                default=st.session_state.selected_resources,
                key="edit_assigned_resources",
                on_change=update_selected_resources,  # Trigger callback on change
            )

            # Resource allocation section
            st.markdown("### Resource Allocation")
            edited_resource_allocations = []
            for resource in st.session_state.selected_resources:
                st.markdown(f"**{resource}**")

                # Validate and adjust resource allocation dates
                resource_allocation = next(
                    (
                        alloc
                        for alloc in project["resource_allocations"]
                        if alloc["resource"] == resource
                    ),
                    None,
                )
                if resource_allocation:
                    resource_start_date = pd.to_datetime(
                        resource_allocation["start_date"]
                    )
                    resource_end_date = pd.to_datetime(resource_allocation["end_date"])

                    # Adjust dates to fit within project bounds
                    resource_start_date = max(
                        resource_start_date, pd.to_datetime(project["start_date"])
                    )
                    resource_end_date = min(
                        resource_end_date, pd.to_datetime(project["end_date"])
                    )
                else:
                    # Default to project start and end dates if no allocation exists
                    resource_start_date = pd.to_datetime(project["start_date"])
                    resource_end_date = pd.to_datetime(project["end_date"])

                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    allocation_percentage = st.slider(
                        f"Allocation % for {resource}",
                        min_value=10,
                        max_value=100,
                        value=st.session_state.get(
                            f"edit_alloc_{resource}", 100
                        ),  # Use session state to persist values
                        step=10,
                        key=f"edit_alloc_{resource}",
                    )
                with col2:
                    resource_start_date = st.date_input(
                        f"Start Date for {resource}",
                        value=resource_start_date,
                        min_value=pd.to_datetime(project["start_date"]),
                        max_value=pd.to_datetime(project["end_date"]),
                        key=f"edit_start_{resource}",
                    )
                with col3:
                    resource_end_date = st.date_input(
                        f"End Date for {resource}",
                        value=resource_end_date,
                        min_value=pd.to_datetime(project["start_date"]),
                        max_value=pd.to_datetime(project["end_date"]),
                        key=f"edit_end_{resource}",
                    )

                edited_resource_allocations.append(
                    {
                        "resource": resource,
                        "allocation_percentage": allocation_percentage,
                        "start_date": resource_start_date.strftime("%Y-%m-%d"),
                        "end_date": resource_end_date.strftime("%Y-%m-%d"),
                    }
                )

            # Priority input
            st.markdown("### Project Priority")
            priority = st.number_input(
                "Priority",
                min_value=1,
                step=1,
                value=project["priority"],
                key="edit_priority",
            )

            # Submit button
            if st.button("Update Project", key="update_project"):
                # Ensure dates are converted to pd.Timestamp
                start_date = pd.to_datetime(start_date)
                end_date = pd.to_datetime(end_date)

                # Pass all fields as a dictionary to match validate_project_input's expected input
                project_data = {
                    "name": name,
                    "start_date": start_date,
                    "end_date": end_date,
                    "budget": budget,
                }
                if not validate_project_input(project_data):
                    st.error("Invalid project details. Please try again.")
                    return

                # Check for duplicate priorities
                duplicate_projects = [
                    p
                    for p in st.session_state.data["projects"]
                    if p["priority"] == priority and p["name"] != project["name"]
                ]
                if duplicate_projects:
                    with st.expander("⚠️ Duplicate Priority Detected", expanded=True):
                        st.warning(
                            f"The priority {priority} is already assigned to the following projects:"
                        )
                        for p in duplicate_projects:
                            st.write(
                                f"- {p['name']} (Start: {p['start_date']}, End: {p['end_date']})"
                            )
                        st.info("Please assign a unique priority to each project.")
                    return

                # Update project details
                project.update(
                    {
                        "name": name,
                        "start_date": start_date.strftime("%Y-%m-%d"),
                        "end_date": end_date.strftime("%Y-%m-%d"),
                        "allocated_budget": budget,
                        "assigned_resources": st.session_state.selected_resources,
                        "priority": priority,
                        "resource_allocations": edited_resource_allocations,
                    }
                )
                st.success(f"Project '{name}' updated successfully.")
                st.rerun()


def reset_edit_project_state():
    """Reset session state variables for editing a project."""
    selected_project = st.session_state.get("selected_project")
    if selected_project:
        project = next(
            (
                p
                for p in st.session_state.data["projects"]
                if p["name"] == selected_project
            ),
            None,
        )
        if project:
            st.session_state.selected_resources = project["assigned_resources"]
            # Reset other session state variables related to resource allocation
            for resource in project["assigned_resources"]:
                st.session_state[f"edit_alloc_{resource}"] = next(
                    (
                        alloc["allocation_percentage"]
                        for alloc in project["resource_allocations"]
                        if alloc["resource"] == resource
                    ),
                    100,
                )
                st.session_state[f"edit_start_{resource}"] = pd.to_datetime(
                    next(
                        (
                            alloc["start_date"]
                            for alloc in project["resource_allocations"]
                            if alloc["resource"] == resource
                        ),
                        project["start_date"],
                    )
                )
                st.session_state[f"edit_end_{resource}"] = pd.to_datetime(
                    next(
                        (
                            alloc["end_date"]
                            for alloc in project["resource_allocations"]
                            if alloc["resource"] == resource
                        ),
                        project["end_date"],
                    )
                )


def delete_project_form():
    with st.expander("Delete Project", expanded=False):  # Set expanded=False
        if not st.session_state.data["projects"]:
            st.info("No projects available to delete.")
            return

        delete_project = st.selectbox(
            "Select project to Delete",
            [p["name"] for p in st.session_state.data["projects"]],
            key="delete_project",
        )

        if confirm_action(f"deleting project {delete_project}", "delete_project"):
            st.session_state.data["projects"] = [
                p
                for p in st.session_state.data["projects"]
                if p["name"] != delete_project
            ]

            st.success(f"Deleted project {delete_project}")
            st.rerun()
