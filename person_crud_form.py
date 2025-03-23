"""
Person CRUD Form Module

This module contains the Streamlit form for managing people.
"""

import streamlit as st
from color_management import add_department_color, load_currency_settings
from validation import (
    validate_daily_cost,
    validate_work_days,
    validate_work_hours,
    validate_name_field,
)


def person_crud_form():
    st.subheader("Manage People")

    # Load currency settings
    currency, currency_format = load_currency_settings()

    # Select a person to edit or delete
    people = st.session_state.data["people"]
    person_names = [person["name"] for person in people]
    selected_person = st.selectbox(
        "Select a person to edit or delete", [""] + person_names, key="selected_person"
    )

    if selected_person:
        person = next((p for p in people if p["name"] == selected_person), None)

        if person:
            with st.form("edit_person"):
                name = st.text_input("Name", value=person["name"])
                role = st.text_input("Role", value=person["role"])
                department = st.selectbox(
                    "Department",
                    options=[d["name"] for d in st.session_state.data["departments"]],
                    index=[
                        d["name"] for d in st.session_state.data["departments"]
                    ].index(person["department"]),
                )
                daily_cost = st.number_input(
                    "Daily Cost",
                    min_value=0.0,
                    step=50.0,
                    value=float(person["daily_cost"]),
                )
                work_days = st.multiselect(
                    "Work Days",
                    options=["MO", "TU", "WE", "TH", "FR", "SA", "SU"],
                    default=person["work_days"],
                )
                daily_work_hours = st.number_input(
                    "Daily Work Hours",
                    min_value=1.0,
                    max_value=24.0,
                    step=1.0,
                    value=float(person["daily_work_hours"]),
                )

                update = st.form_submit_button("Update Person")
                if update:
                    if not validate_name_field(name, "person"):
                        st.error("Invalid name. Please try again.")
                        return
                    if not validate_daily_cost(daily_cost):
                        st.error("Invalid daily cost. Please try again.")
                        return
                    if not validate_work_days(work_days):
                        st.error("Invalid work days. Please try again.")
                        return
                    if not validate_work_hours(daily_work_hours):
                        st.error("Invalid daily work hours. Please try again.")
                        return

                    person.update(
                        {
                            "name": name,
                            "role": role,
                            "department": department,
                            "daily_cost": daily_cost,
                            "work_days": work_days,
                            "daily_work_hours": daily_work_hours,
                        }
                    )
                    st.success(f"Person '{name}' updated successfully.")
                    st.rerun()  # Updated from st.experimental_rerun()

            # Delete person
            delete = st.button("Delete Person")
            if delete:
                st.session_state.data["people"] = [
                    p for p in people if p["name"] != person["name"]
                ]
                st.rerun()  # Updated from st.experimental_rerun()

    # Add a new person
    st.subheader("Add Person")
    with st.form("add_person"):
        name = st.text_input("Name")
        role = st.text_input("Role")
        department = st.selectbox(
            "Department",
            options=[d["name"] for d in st.session_state.data["departments"]],
        )
        daily_cost = st.number_input("Daily Cost", min_value=0.0, step=50.0)
        work_days = st.multiselect(
            "Work Days", options=["MO", "TU", "WE", "TH", "FR", "SA", "SU"]
        )
        daily_work_hours = st.number_input(
            "Daily Work Hours",
            min_value=1.0,
            max_value=24.0,
            step=1.0,
        )

        submit = st.form_submit_button("Add Person")
        if submit:
            if not validate_name_field(name, "person"):
                st.error("Invalid name. Please try again.")
                return
            if not validate_daily_cost(daily_cost):
                st.error("Invalid daily cost. Please try again.")
                return
            if not validate_work_days(work_days):
                st.error("Invalid work days. Please try again.")
                return
            if not validate_work_hours(daily_work_hours):
                st.error("Invalid daily work hours. Please try again.")
                return

            st.session_state.data["people"].append(
                {
                    "name": name,
                    "role": role,
                    "department": department,
                    "team": None,
                    "daily_cost": daily_cost,
                    "work_days": work_days,
                    "daily_work_hours": daily_work_hours,
                }
            )
            add_department_color(department)
            st.success(f"Person '{name}' added successfully.")
            st.rerun()  # Updated from st.experimental_rerun()
