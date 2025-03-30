"""
Department CRUD operations module.

This module provides functions for creating, reading, updating, and deleting departments.
"""

import streamlit as st
from typing import Dict, List, Any
from configuration import add_department_color, load_department_colors
from validation import validate_name_field
from utils import confirm_action


def department_crud_form():
    """Create, update, and delete departments."""
    st.subheader("Manage Departments")

    # Add Department Form
    with st.expander("Add New Department", expanded=False):
        with st.form("add_department_form"):
            name = st.text_input("Department Name", key="add_department_name")

            # Optional: Department leaders
            leader_options = ["None"] + [
                p["name"] for p in st.session_state.data["people"] if not p["team"]
            ]
            leader = st.selectbox(
                "Department Leader", leader_options, key="add_department_leader"
            )

            # Initialize empty lists for teams and members
            teams = []
            members = []

            submitted = st.form_submit_button("Add Department")

            if submitted:
                if not validate_name_field(name, "department"):
                    st.error("Invalid department name. Please try again.")
                    return

                # Check if department already exists
                if any(d["name"] == name for d in st.session_state.data["departments"]):
                    st.error(f"Department '{name}' already exists.")
                    return

                # Create department with leader if selected
                department_data = {"name": name, "teams": teams, "members": members}

                if leader != "None":
                    department_data["leader"] = leader

                # Add to session state
                st.session_state.data["departments"].append(department_data)

                # Generate color for the new department
                add_department_color(name)

                st.success(f"Department '{name}' added successfully.")
                st.rerun()

    # Edit Department Form
    with st.expander("Edit Department", expanded=False):
        if not st.session_state.data["departments"]:
            st.info("No departments available to edit.")
        else:
            department_names = [d["name"] for d in st.session_state.data["departments"]]
            selected_department = st.selectbox(
                "Select Department to Edit",
                department_names,
                key="edit_department_select",
            )

            department = next(
                (
                    d
                    for d in st.session_state.data["departments"]
                    if d["name"] == selected_department
                ),
                None,
            )

            if department:
                with st.form("edit_department_form"):
                    name = st.text_input("Department Name", value=department["name"])

                    # Get currently assigned teams
                    current_teams = department.get("teams", [])

                    # Team assignment options
                    all_teams = [t["name"] for t in st.session_state.data["teams"]]
                    selected_teams = st.multiselect(
                        "Assign Teams",
                        options=all_teams,
                        default=current_teams,
                        key="edit_department_teams",
                    )

                    # Leader selection
                    leader_options = ["None"] + [
                        p["name"]
                        for p in st.session_state.data["people"]
                        if not p["team"] or p["name"] == department.get("leader", "")
                    ]
                    current_leader = department.get("leader", "None")
                    if (
                        current_leader not in leader_options
                        and current_leader != "None"
                    ):
                        leader_options.append(current_leader)

                    leader = st.selectbox(
                        "Department Leader",
                        leader_options,
                        index=leader_options.index(current_leader)
                        if current_leader in leader_options
                        else 0,
                    )

                    update_submitted = st.form_submit_button("Update Department")

                    if update_submitted:
                        if not validate_name_field(name, "department"):
                            st.error("Invalid department name. Please try again.")
                            return

                        # Check if new name conflicts with existing departments
                        if name != department["name"] and any(
                            d["name"] == name
                            for d in st.session_state.data["departments"]
                        ):
                            st.error(f"Department '{name}' already exists.")
                            return

                        # Update department in session state
                        department["name"] = name
                        department["teams"] = selected_teams

                        if leader != "None":
                            department["leader"] = leader
                        elif "leader" in department:
                            del department["leader"]

                        # Update people's department if department name changed
                        old_name = department["name"]
                        if name != old_name:
                            for person in st.session_state.data["people"]:
                                if person["department"] == old_name:
                                    person["department"] = name

                            # Update teams' department
                            for team in st.session_state.data["teams"]:
                                if team["department"] == old_name:
                                    team["department"] = name

                        st.success(f"Department '{name}' updated successfully.")
                        st.rerun()

    # Delete Department Form
    with st.expander("Delete Department", expanded=False):
        if not st.session_state.data["departments"]:
            st.info("No departments available to delete.")
        else:
            department_names = [d["name"] for d in st.session_state.data["departments"]]
            selected_department = st.selectbox(
                "Select Department to Delete",
                [""] + department_names,
                key="delete_department_select",
            )

            if selected_department:
                # Check for affected resources
                affected_people = [
                    p["name"]
                    for p in st.session_state.data["people"]
                    if p["department"] == selected_department
                ]

                affected_teams = [
                    t["name"]
                    for t in st.session_state.data["teams"]
                    if t["department"] == selected_department
                ]

                if affected_people or affected_teams:
                    st.warning("⚠️ This department has associated resources!")

                    if affected_people:
                        st.info(
                            f"People ({len(affected_people)}): {', '.join(affected_people)}"
                        )

                    if affected_teams:
                        st.info(
                            f"Teams ({len(affected_teams)}): {', '.join(affected_teams)}"
                        )

                if confirm_action(
                    f"deleting department {selected_department}", "delete_department"
                ):
                    # Remove department from session state
                    st.session_state.data["departments"] = [
                        d
                        for d in st.session_state.data["departments"]
                        if d["name"] != selected_department
                    ]

                    # Update affected resources
                    for person in st.session_state.data["people"]:
                        if person["department"] == selected_department:
                            person["department"] = "Unassigned"  # Default department

                    for team in st.session_state.data["teams"]:
                        if team["department"] == selected_department:
                            team["department"] = "Unassigned"  # Default department

                    st.success(
                        f"Department '{selected_department}' deleted successfully."
                    )
                    st.rerun()
