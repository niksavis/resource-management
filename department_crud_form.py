"""
Department CRUD Form Module

This module contains the Streamlit form for managing departments.
"""

import streamlit as st
from color_management import add_department_color
from validation import validate_name_field


def department_crud_form():
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
            st.experimental_rerun()
