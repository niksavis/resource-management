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
            if not validate_project_input(name, start_date, end_date, budget):
                st.error("Invalid project details. Please try again.")
                return

            st.session_state.data["projects"].append(
                {
                    "name": name,
                    "start_date": start_date.strftime("%Y-%m-%d"),
                    "end_date": end_date.strftime("%Y-%m-%d"),
                    "priority": len(st.session_state.data["projects"]) + 1,
                    "assigned_resources": assigned_resources,
                    "allocated_budget": budget,
                }
            )
            st.success(f"Project '{name}' added successfully.")
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

            submit = st.form_submit_button("Update Project")
            if submit:
                if not validate_project_input(name, start_date, end_date, budget):
                    st.error("Invalid project details. Please try again.")
                    return

                project.update(
                    {
                        "name": name,
                        "start_date": start_date.strftime("%Y-%m-%d"),
                        "end_date": end_date.strftime("%Y-%m-%d"),
                        "allocated_budget": budget,
                        "assigned_resources": assigned_resources,
                    }
                )
                st.success(f"Project '{name}' updated successfully.")
                st.rerun()
