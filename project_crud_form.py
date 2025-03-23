import streamlit as st
import pandas as pd
from validation import validate_project_input


def add_project_form():
    st.subheader("Add Project")

    with st.form("add_project"):
        name = st.text_input("Project Name")
        start_date = st.date_input("Start Date")
        end_date = st.date_input("End Date")
        budget = st.number_input("Budget (€)", min_value=0.0, step=1000.0)
        assigned_resources = st.multiselect(
            "Assigned Resources",
            options=[
                *[p["name"] for p in st.session_state.data["people"]],
                *[t["name"] for t in st.session_state.data["teams"]],
            ],
        )

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
            name = st.text_input("Project Name", value=project["name"])
            start_date = st.date_input(
                "Start Date", value=pd.to_datetime(project["start_date"])
            )
            end_date = st.date_input(
                "End Date", value=pd.to_datetime(project["end_date"])
            )
            budget = st.number_input(
                "Budget (€)",
                min_value=0.0,
                step=1000.0,
                value=project["allocated_budget"],
            )
            assigned_resources = st.multiselect(
                "Assigned Resources",
                options=[
                    *[p["name"] for p in st.session_state.data["people"]],
                    *[t["name"] for t in st.session_state.data["teams"]],
                ],
                default=project["assigned_resources"],
            )
            priority = st.number_input(
                "Priority", min_value=1, step=1, value=project["priority"]
            )

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

                project.update(
                    {
                        "name": name,
                        "start_date": start_date.strftime("%Y-%m-%d"),
                        "end_date": end_date.strftime("%Y-%m-%d"),
                        "allocated_budget": budget,
                        "assigned_resources": assigned_resources,
                        "priority": priority,
                    }
                )
                st.success(f"Project '{name}' updated successfully.")
                st.rerun()
