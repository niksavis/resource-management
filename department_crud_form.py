"""
Department CRUD Form Module

This module contains the Streamlit form for managing departments.
"""

import streamlit as st
from color_management import add_department_color
from validation import validate_name_field


def department_crud_form():
    st.subheader("Manage Departments")

    # Select a department to delete
    departments = st.session_state.data["departments"]
    department_names = [d["name"] for d in departments]
    selected_department = st.selectbox(
        "Select a department to delete", [""] + department_names
    )

    if selected_department:
        delete = st.button("Delete Department")
        if delete:
            st.session_state.data["departments"] = [
                d for d in departments if d["name"] != selected_department
            ]
            for person in st.session_state.data["people"]:
                if person["department"] == selected_department:
                    person["department"] = None
            for team in st.session_state.data["teams"]:
                if team["department"] == selected_department:
                    team["department"] = None
            st.success(f"Department '{selected_department}' deleted successfully.")
            st.rerun()

    # Add a new department
    st.subheader("Add Department")
    with st.form("add_department"):
        name = st.text_input("Department Name")
        submit = st.form_submit_button("Add Department")

        if submit:
            if not validate_name_field(name):
                st.error("Invalid department name. Please try again.")
                return

            st.session_state.data["departments"].append({"name": name, "teams": []})
            add_department_color(name)
            st.success(f"Department '{name}' added successfully.")
            st.rerun()
