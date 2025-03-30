import streamlit as st
from configuration import (
    add_department_color,
    load_currency_settings,
    load_daily_cost_settings,
    load_work_schedule_settings,
)
from validation import (
    validate_daily_cost,
    validate_work_days,
    validate_work_hours,
    validate_name_field,
)
from utils import confirm_action


def person_crud_form():
    """Create, update, and delete people."""
    st.subheader("Manage People")

    # Load currency settings
    currency, _ = load_currency_settings()

    # Get work schedule defaults from settings
    work_schedule = load_work_schedule_settings()
    default_work_days = work_schedule.get(
        "work_days", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    )
    default_work_hours = work_schedule.get("work_hours", 8.0)

    # Load max daily cost
    max_daily_cost = load_daily_cost_settings()

    # Add Person Form
    with st.expander("Add New Person", expanded=False):
        with st.form("add_person_form"):
            name = st.text_input("Name", key="add_person_name")
            role = st.text_input("Role", key="add_person_role")

            # Get department options
            departments = [d["name"] for d in st.session_state.data["departments"]]
            department = st.selectbox(
                "Department", options=departments, key="add_person_department"
            )

            # Get team options for selected department
            team_options = ["None"] + [
                t["name"]
                for t in st.session_state.data["teams"]
                if t["department"] == department
            ]
            team = st.selectbox("Team", options=team_options, key="add_person_team")
            if team == "None":
                team = ""

            # Load daily cost from setting
            daily_cost = st.number_input(
                f"Daily Cost ({currency})",
                min_value=0.0,
                max_value=float(max_daily_cost),
                value=100.0,
                step=10.0,
                key="add_person_daily_cost",
            )

            # Use default work days from settings
            work_days = st.multiselect(
                "Work Days",
                options=[
                    "Monday",
                    "Tuesday",
                    "Wednesday",
                    "Thursday",
                    "Friday",
                    "Saturday",
                    "Sunday",
                ],
                default=default_work_days,
                key="add_person_work_days",
            )

            # Use default work hours from settings
            daily_work_hours = st.number_input(
                "Daily Work Hours",
                min_value=1.0,
                max_value=24.0,
                value=default_work_hours,
                step=0.5,
                key="add_person_daily_work_hours",
            )

            submitted = st.form_submit_button("Add Person")

            if submitted:
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
                        "team": team if team != "" else None,
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

    # Delete Person Form
    with st.expander("Delete Person", expanded=False):
        if not st.session_state.data["people"]:
            st.info("No people available to delete.")
            return

        person_names = [p["name"] for p in st.session_state.data["people"]]
        selected_person = st.selectbox("Select Person to Delete", [""] + person_names)

        if selected_person and confirm_action(
            f"deleting person {selected_person}", "delete_person"
        ):
            st.session_state.data["people"] = [
                p
                for p in st.session_state.data["people"]
                if p["name"] != selected_person
            ]
            st.success(f"Person '{selected_person}' deleted successfully.")
            st.rerun()
