import streamlit as st
import pandas as pd
from validation import validate_project_input
from configuration import load_currency_settings


def add_project_form():
    st.subheader("Add Project")

    with st.form("add_project"):
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
            start_date = st.date_input("Start Date")
        with col4:
            end_date = st.date_input("End Date")

        # Assigned resources section
        st.markdown("### Assigned Resources")
        assigned_resources = st.multiselect(
            "Select Resources",
            options=[
                *[p["name"] for p in st.session_state.data["people"]],
                *[t["name"] for t in st.session_state.data["teams"]],
            ],
        )

        # Resource allocation section
        st.markdown("### Resource Allocation")
        resource_allocations = []
        for resource in assigned_resources:
            st.markdown(f"**{resource}**")
            col5, col6, col7 = st.columns([1, 1, 2])
            with col5:
                allocation_percentage = st.slider(
                    f"Allocation % for {resource}",
                    min_value=10,
                    max_value=100,
                    value=100,
                    step=10,
                    key=f"alloc_{resource}",
                )
            with col6:
                resource_start_date = st.date_input(
                    f"Start Date for {resource}", key=f"start_{resource}"
                )
            with col7:
                resource_end_date = st.date_input(
                    f"End Date for {resource}", key=f"end_{resource}"
                )

            resource_allocations.append(
                {
                    "resource": resource,
                    "allocation_percentage": allocation_percentage,
                    "start_date": resource_start_date.strftime("%Y-%m-%d"),
                    "end_date": resource_end_date.strftime("%Y-%m-%d"),
                }
            )

        # Submit button
        submit = st.form_submit_button("Add Project")
        if submit:
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
                    "assigned_resources": assigned_resources,
                    "allocated_budget": budget,
                    "resource_allocations": resource_allocations,
                }
            )
            st.success(
                f"Project '{name}' added successfully with priority {new_priority}."
            )
            st.rerun()


def edit_project_form():
    st.subheader("Edit Project")

    if not st.session_state.data["projects"]:
        st.info("No projects available to edit.")
        return

    project_names = [p["name"] for p in st.session_state.data["projects"]]
    selected_project = st.selectbox("Select Project to Edit", project_names)

    project = next(
        (p for p in st.session_state.data["projects"] if p["name"] == selected_project),
        None,
    )

    if project:
        with st.form("edit_project"):
            # Group project details in a single row
            st.markdown("### Project Details")
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Project Name", value=project["name"])
            with col2:
                currency, _ = load_currency_settings()
                budget = st.number_input(
                    f"Budget ({currency})",
                    min_value=0.0,
                    step=1000.0,
                    value=project["allocated_budget"],
                )

            # Group date inputs in another row
            st.markdown("### Project Timeline")
            col3, col4 = st.columns(2)
            with col3:
                start_date = st.date_input(
                    "Start Date", value=pd.to_datetime(project["start_date"])
                )
            with col4:
                end_date = st.date_input(
                    "End Date", value=pd.to_datetime(project["end_date"])
                )

            # Assigned resources section
            st.markdown("### Assigned Resources")
            assigned_resources = st.multiselect(
                "Select Resources",
                options=[
                    *[p["name"] for p in st.session_state.data["people"]],
                    *[t["name"] for t in st.session_state.data["teams"]],
                ],
                default=project["assigned_resources"],
            )

            # Resource allocation section
            st.markdown("### Resource Allocation")
            edited_resource_allocations = []
            for resource in assigned_resources:
                st.markdown(f"**{resource}**")
                col5, col6, col7 = st.columns([2, 1, 1])  # Adjusted column widths
                with col5:
                    allocation_percentage = st.slider(
                        f"Allocation % for {resource}",
                        min_value=10,
                        max_value=100,
                        value=100,
                        step=10,
                        key=f"edit_alloc_{resource}",
                    )
                with col6:
                    resource_start_date = st.date_input(
                        f"Start Date for {resource}",
                        value=pd.to_datetime(project["start_date"]),
                        key=f"edit_start_{resource}",
                    )
                with col7:
                    resource_end_date = st.date_input(
                        f"End Date for {resource}",
                        value=pd.to_datetime(project["end_date"]),
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
                "Priority", min_value=1, step=1, value=project["priority"]
            )

            # Submit button
            submit = st.form_submit_button("Update Project")
            if submit:
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
                        "assigned_resources": assigned_resources,
                        "priority": priority,
                        "resource_allocations": edited_resource_allocations,
                    }
                )
                st.success(f"Project '{name}' updated successfully.")
                st.rerun()
