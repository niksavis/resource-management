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
    currency, _ = load_currency_settings()

    # Add Person Form
    with st.expander("Add Person"):
        # Track selected department in session state
        if "add_person_department" not in st.session_state:
            st.session_state.add_person_department = None

        def update_teams():
            st.session_state.add_person_team = None  # Reset team selection

        department = st.selectbox(
            "Department",
            options=[d["name"] for d in st.session_state.data["departments"]],
            key="add_person_department",
            on_change=update_teams,  # Callback to update teams
        )

        # Dynamically update team options based on selected department
        teams_in_department = [
            t["name"]
            for t in st.session_state.data["teams"]
            if t["department"] == st.session_state.add_person_department
        ]
        team = st.selectbox(
            "Team",
            options=["None"] + teams_in_department,
            key="add_person_team",
        )

        with st.form("add_person"):
            name = st.text_input("Name")
            role = st.text_input("Role")
            daily_cost = st.number_input(
                f"Daily Cost ({currency})", min_value=0.0, step=50.0
            )
            work_days = st.multiselect(
                "Work Days",
                options=["MO", "TU", "WE", "TH", "FR", "SA", "SU"],
                default=["MO", "TU", "WE", "TH", "FR"],
            )
            daily_work_hours = st.number_input(
                "Daily Work Hours",
                min_value=1.0,
                max_value=24.0,
                step=1.0,
                value=8.0,
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

                # Calculate capacity attributes
                capacity_hours_per_week = daily_work_hours * len(work_days)
                capacity_hours_per_month = capacity_hours_per_week * 4.33

                st.session_state.data["people"].append(
                    {
                        "name": name,
                        "role": role,
                        "department": department,
                        "team": team if team != "None" else None,
                        "daily_cost": daily_cost,
                        "work_days": work_days,
                        "daily_work_hours": daily_work_hours,
                        "capacity_hours_per_week": capacity_hours_per_week,
                        "capacity_hours_per_month": capacity_hours_per_month,
                    }
                )
                add_department_color(department)
                st.success(f"Person '{name}' added successfully.")
                st.rerun()

    # Edit Person Form
    with st.expander("Edit Person"):
        if not st.session_state.data["people"]:
            st.info("No people available to edit.")
            return

        person_names = [p["name"] for p in st.session_state.data["people"]]
        selected_person = st.selectbox("Select Person to Edit", person_names)

        person = next(
            (
                p
                for p in st.session_state.data["people"]
                if p["name"] == selected_person
            ),
            None,
        )

        if person:
            # Track selected department in session state
            if "edit_person_department" not in st.session_state:
                st.session_state.edit_person_department = person["department"]

            def update_edit_teams():
                st.session_state.edit_person_team = None  # Reset team selection

            department = st.selectbox(
                "Department",
                options=[d["name"] for d in st.session_state.data["departments"]],
                index=[d["name"] for d in st.session_state.data["departments"]].index(
                    person["department"]
                ),
                key="edit_person_department",
                on_change=update_edit_teams,  # Callback to update teams
            )

            # Dynamically update team options based on selected department
            teams_in_department = [
                t["name"]
                for t in st.session_state.data["teams"]
                if t["department"] == st.session_state.edit_person_department
            ]
            # Ensure the selected team is valid for the current department
            current_team = (
                person["team"] if person["team"] in teams_in_department else "None"
            )
            team = st.selectbox(
                "Team",
                options=["None"] + teams_in_department,
                index=(["None"] + teams_in_department).index(current_team),
                key="edit_person_team",
            )

            with st.form("edit_person"):
                name = st.text_input("Name", value=person["name"])
                role = st.text_input("Role", value=person["role"])
                daily_cost = st.number_input(
                    f"Daily Cost ({currency})",
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

                submit = st.form_submit_button("Update Person")
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

                    # Recalculate capacity attributes
                    capacity_hours_per_week = daily_work_hours * len(work_days)
                    capacity_hours_per_month = capacity_hours_per_week * 4.33

                    person.update(
                        {
                            "name": name,
                            "role": role,
                            "department": department,
                            "team": team if team != "None" else None,
                            "daily_cost": daily_cost,
                            "work_days": work_days,
                            "daily_work_hours": daily_work_hours,
                            "capacity_hours_per_week": capacity_hours_per_week,
                            "capacity_hours_per_month": capacity_hours_per_month,
                        }
                    )
                    st.success(f"Person '{name}' updated successfully.")
                    st.rerun()

            # Delete person
            delete = st.button("Delete Person")
            if delete:
                st.session_state.data["people"] = [
                    p
                    for p in st.session_state.data["people"]
                    if p["name"] != person["name"]
                ]
                st.rerun()
