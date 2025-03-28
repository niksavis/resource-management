import streamlit as st
from configuration import add_department_color
from validation import validate_name_field
from utils import confirm_action


def department_crud_form():
    st.subheader("Manage Departments")

    # Add Department Form
    with st.expander("Add Department", expanded=False):
        with st.form("add_department"):
            name = st.text_input("Department Name")
            submit = st.form_submit_button("Add Department")
            if submit:
                if not validate_name_field(name, "department"):
                    st.error("Invalid department name. Please try again.")
                else:
                    st.session_state.data["departments"].append(
                        {"name": name, "teams": [], "members": []}
                    )
                    add_department_color(name)
                    st.success(f"Department '{name}' added successfully.")
                    st.rerun()

    # Edit Department Form
    with st.expander("Edit Department", expanded=False):
        if not st.session_state.data["departments"]:
            st.info("No departments available to edit.")
            return

        department_names = [d["name"] for d in st.session_state.data["departments"]]
        selected_department = st.selectbox(
            "Select Department to Edit", [""] + department_names
        )

        if selected_department:
            department = next(
                (
                    d
                    for d in st.session_state.data["departments"]
                    if d["name"] == selected_department
                ),
                None,
            )
            if department:
                with st.form("edit_department"):
                    name = st.text_input("Department Name", value=department["name"])
                    update_button = st.form_submit_button("Update Department")
                    if update_button:
                        if not validate_name_field(name, "department"):
                            st.error("Invalid department name. Please try again.")
                        else:
                            # Update department name in teams and people
                            for person in st.session_state.data["people"]:
                                if person["department"] == selected_department:
                                    person["department"] = name

                            for team in st.session_state.data["teams"]:
                                if team["department"] == selected_department:
                                    team["department"] = name

                            # Update department name
                            department["name"] = name
                            st.success(f"Department '{name}' updated successfully.")
                            st.rerun()

    # Delete Department Form
    with st.expander("Delete Department", expanded=False):
        if not st.session_state.data["departments"]:
            st.info("No departments available to delete.")
            return

        department_names = [d["name"] for d in st.session_state.data["departments"]]
        selected_department = st.selectbox(
            "Select Department to Delete", [""] + department_names
        )

        if selected_department and confirm_action(
            f"deleting department {selected_department}", "delete_department"
        ):
            st.session_state.data["departments"] = [
                d
                for d in st.session_state.data["departments"]
                if d["name"] != selected_department
            ]

            # Update people and teams associated with the deleted department
            for person in st.session_state.data["people"]:
                if person["department"] == selected_department:
                    person["department"] = None

            for team in st.session_state.data["teams"]:
                if team["department"] == selected_department:
                    team["department"] = None

            st.success(f"Department '{selected_department}' deleted successfully.")
            st.rerun()
