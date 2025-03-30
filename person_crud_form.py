"""
Person CRUD operations module.

This module provides functions for creating, reading, updating, and deleting people.
"""

import streamlit as st
from typing import Dict, List, Any, Optional
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
    currency, _ = load_currency_settings()
    max_daily_cost = load_daily_cost_settings()
    work_schedule = load_work_schedule_settings()

    # Add Person Form
    with st.expander("Add New Person", expanded=False):
        _display_add_person_form(currency, work_schedule, max_daily_cost)

    # Edit Person Form
    with st.expander("Edit Person", expanded=False):
        _display_edit_person_form(currency, max_daily_cost)

    # Delete Person Form
    with st.expander("Delete Person", expanded=False):
        _display_delete_person_form()


def _display_add_person_form(
    currency: str, work_schedule: Dict[str, Any], max_daily_cost: float
):
    """
    Display the form for adding a new person.

    Args:
        currency: Currency symbol to display
        work_schedule: Default work schedule settings
        max_daily_cost: Maximum daily cost allowed
    """
    with st.form("add_person_form"):
        # Basic information
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Name", key="add_person_name")
        with col2:
            role = st.text_input("Role", key="add_person_role")

        # Department and team selection
        col3, col4 = st.columns(2)
        with col3:
            departments = [d["name"] for d in st.session_state.data["departments"]]
            department = st.selectbox(
                "Department", options=departments, key="add_person_department"
            )

        with col4:
            # Filter teams by selected department
            team_options = ["None"] + [
                t["name"]
                for t in st.session_state.data["teams"]
                if t["department"] == department
            ]
            team = st.selectbox("Team", options=team_options, key="add_person_team")
            if team == "None":
                team = None

        # Cost and schedule information
        col5, col6 = st.columns(2)
        with col5:
            daily_cost = st.number_input(
                f"Daily Cost ({currency})",
                min_value=0.0,
                max_value=float(max_daily_cost),
                value=100.0,
                step=10.0,
                key="add_person_daily_cost",
                help=f"Maximum allowed: {currency} {max_daily_cost}",
            )

        with col6:
            # Get default days from settings
            default_work_days = work_schedule.get(
                "work_days",
                ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
            )

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

        # Default work hours from settings
        default_work_hours = work_schedule.get("work_hours", 8.0)
        daily_work_hours = st.number_input(
            "Daily Work Hours",
            min_value=1.0,
            max_value=24.0,
            value=default_work_hours,
            step=0.5,
            key="add_person_daily_work_hours",
            help="Hours per workday",
        )

        # Additional information
        skills = st.multiselect(
            "Skills",
            options=[
                "Project Management",
                "Programming",
                "Design",
                "Marketing",
                "Sales",
                "HR",
                "Finance",
                "Operations",
                "Other",
            ],
            key="add_person_skills",
        )

        notes = st.text_area(
            "Notes",
            key="add_person_notes",
            placeholder="Additional information about this person...",
        )

        submitted = st.form_submit_button("Add Person")

        if submitted:
            result = _validate_and_add_person(
                name=name,
                role=role,
                department=department,
                team=team,
                daily_cost=daily_cost,
                work_days=work_days,
                daily_work_hours=daily_work_hours,
                skills=skills,
                notes=notes,
            )

            if result:
                st.success(f"Person '{name}' added successfully.")
                st.rerun()


def _validate_and_add_person(
    name: str,
    role: str,
    department: str,
    team: Optional[str],
    daily_cost: float,
    work_days: List[str],
    daily_work_hours: float,
    skills: Optional[List[str]] = None,
    notes: Optional[str] = None,
) -> bool:
    """
    Validate person data and add to session state if valid.

    Args:
        name: Person's name
        role: Person's role
        department: Person's department
        team: Person's team (optional)
        daily_cost: Person's daily cost
        work_days: List of work days
        daily_work_hours: Daily work hours
        skills: List of skills (optional)
        notes: Additional notes (optional)

    Returns:
        True if person was successfully added, False otherwise
    """
    # Validate required fields
    if not validate_name_field(name, "person"):
        st.error("Invalid name. Please try again.")
        return False

    if not validate_daily_cost(daily_cost):
        st.error("Invalid daily cost. Please try again.")
        return False

    if not validate_work_days(work_days):
        st.error("Invalid work days. Please select at least one day.")
        return False

    if not validate_work_hours(daily_work_hours):
        st.error("Invalid daily work hours. Must be between 1 and 24.")
        return False

    # Check for duplicate name
    if any(p["name"] == name for p in st.session_state.data["people"]):
        st.error(f"A person with the name '{name}' already exists.")
        return False

    # Calculate capacity attributes
    capacity_hours_per_week = daily_work_hours * len(work_days)
    capacity_hours_per_month = capacity_hours_per_week * 4.33  # Average weeks per month

    # Create person data
    person_data = {
        "name": name,
        "role": role,
        "department": department,
        "team": team,
        "daily_cost": daily_cost,
        "work_days": work_days,
        "daily_work_hours": daily_work_hours,
        "capacity_hours_per_week": capacity_hours_per_week,
        "capacity_hours_per_month": capacity_hours_per_month,
    }

    # Add optional fields if provided
    if skills:
        person_data["skills"] = skills
    if notes:
        person_data["notes"] = notes

    # Add to session state
    st.session_state.data["people"].append(person_data)

    # Ensure department has a color
    add_department_color(department)

    return True


def _display_edit_person_form(currency: str, max_daily_cost: float):
    """Display form for editing an existing person."""
    if not st.session_state.data["people"]:
        st.info("No people available to edit.")
        return

    # Initialize the form state variables if not already set
    if "edit_person_role" not in st.session_state:
        st.session_state.edit_person_role = ""
    if "edit_person_work_days" not in st.session_state:
        st.session_state.edit_person_work_days = []

    # Get person names
    person_names = [p["name"] for p in st.session_state.data["people"]]

    # Select person to edit
    selected_person = st.selectbox(
        "Select Person to Edit",
        options=person_names,
        key="edit_person_select",
    )

    # Find the selected person
    person = next(
        (p for p in st.session_state.data["people"] if p["name"] == selected_person),
        None,
    )

    if not person:
        st.info("Please select a person to edit.")
        return

    # Get current values for the form fields - don't try to set session state directly
    current_name = person["name"]
    current_role = person.get("role", "")
    current_department = person.get("department", "")
    current_team = person.get("team", None)
    current_daily_cost = person.get("daily_cost", 0)
    current_work_days = person.get(
        "work_days", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    )
    current_daily_work_hours = person.get("daily_work_hours", 8.0)

    # Convert abbreviated day names to full names if needed
    day_mapping = {
        "MO": "Monday",
        "TU": "Tuesday",
        "WE": "Wednesday",
        "TH": "Thursday",
        "FR": "Friday",
        "SA": "Saturday",
        "SU": "Sunday",
    }

    # Convert current work days to full names if they're abbreviations
    formatted_work_days = []
    for day in current_work_days:
        if day in day_mapping:
            formatted_work_days.append(day_mapping[day])
        else:
            formatted_work_days.append(day)

    with st.form("edit_person_form"):
        # Basic information
        name = st.text_input("Name", value=current_name)
        role = st.text_input("Role", value=current_role)

        # Department selection
        departments = [d["name"] for d in st.session_state.data["departments"]]
        # Instead of trying to set the session state variable directly, just use the index parameter
        dept_index = (
            departments.index(current_department)
            if current_department in departments
            else 0
        )
        department = st.selectbox(
            "Department",
            options=departments,
            index=dept_index,
            key="edit_person_department_select",
        )

        # Team selection
        teams_in_dept = ["None"] + [
            t["name"]
            for t in st.session_state.data["teams"]
            if t["department"] == department
        ]
        team_index = (
            teams_in_dept.index(current_team) if current_team in teams_in_dept else 0
        )
        team = st.selectbox(
            "Team",
            options=teams_in_dept,
            index=team_index,
            key="edit_person_team_select",
        )

        # Cost and availability
        daily_cost = st.number_input(
            f"Daily Cost ({currency})",
            min_value=0.0,
            max_value=max_daily_cost,
            value=float(current_daily_cost),
            step=50.0,
        )

        # Week days selection - use full names in both options and defaults
        work_days_options = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]
        work_days = st.multiselect(
            "Work Days",
            options=work_days_options,
            default=formatted_work_days,
            key="edit_person_work_days_select",
        )

        # Daily work hours
        daily_work_hours = st.number_input(
            "Daily Work Hours",
            min_value=1.0,
            max_value=24.0,
            value=float(current_daily_work_hours),
            step=0.5,
        )

        # Submit button
        submitted = st.form_submit_button("Update Person")

        if submitted:
            # Validate inputs
            if not validate_name_field(name, "person"):
                st.error("Invalid name. Please use a different name.")
                return

            if not validate_daily_cost(daily_cost):
                st.error(f"Daily cost must be between 0 and {max_daily_cost}.")
                return

            if not validate_work_days(work_days):
                st.error("Please select at least one work day.")
                return

            if not validate_work_hours(daily_work_hours):
                st.error("Daily work hours must be between 1 and 24.")
                return

            # Update person in session state
            for p in st.session_state.data["people"]:
                if p["name"] == current_name:
                    p["name"] = name
                    p["role"] = role
                    p["department"] = department
                    p["team"] = None if team == "None" else team
                    p["daily_cost"] = daily_cost
                    p["work_days"] = work_days
                    p["daily_work_hours"] = daily_work_hours

                    # Update capacity calculations based on work days and hours
                    p["capacity_hours_per_week"] = len(work_days) * daily_work_hours
                    p["capacity_hours_per_month"] = (
                        p["capacity_hours_per_week"] * 4.33
                    )  # Average weeks per month

                    break

            # Update teams if team changed
            if current_team != team:
                # Remove from old team if any
                if current_team and current_team != "None":
                    old_team = next(
                        (
                            t
                            for t in st.session_state.data["teams"]
                            if t["name"] == current_team
                        ),
                        None,
                    )
                    if (
                        old_team
                        and "members" in old_team
                        and current_name in old_team["members"]
                    ):
                        old_team["members"].remove(current_name)

                # Add to new team if any
                if team and team != "None":
                    new_team = next(
                        (
                            t
                            for t in st.session_state.data["teams"]
                            if t["name"] == team
                        ),
                        None,
                    )
                    if new_team:
                        if "members" not in new_team:
                            new_team["members"] = []
                        if current_name not in new_team["members"]:
                            new_team["members"].append(name)

            # Update project references if name changed
            if name != current_name:
                for project in st.session_state.data["projects"]:
                    if (
                        "assigned_resources" in project
                        and current_name in project["assigned_resources"]
                    ):
                        project["assigned_resources"].remove(current_name)
                        project["assigned_resources"].append(name)

                    # Update resource allocations
                    if "resource_allocations" in project:
                        for allocation in project["resource_allocations"]:
                            if allocation["resource"] == current_name:
                                allocation["resource"] = name

            st.success(f"Person '{name}' updated successfully.")
            st.rerun()


def _display_delete_person_form():
    """Display the form for deleting a person."""
    if not st.session_state.data["people"]:
        st.info("No people available to delete.")
        return

    # Person selection
    person_names = [p["name"] for p in st.session_state.data["people"]]
    selected_person = st.selectbox(
        "Select Person to Delete",
        options=[""] + person_names,
        key="delete_person_select",
    )

    if not selected_person:
        return

    # Get person details for confirmation
    person = next(
        (p for p in st.session_state.data["people"] if p["name"] == selected_person),
        None,
    )

    if person:
        # Display project assignments for warning
        person_projects = [
            p["name"]
            for p in st.session_state.data["projects"]
            if selected_person in p.get("assigned_resources", [])
        ]

        if person_projects:
            st.warning("⚠️ This person is assigned to the following projects:")
            st.write(", ".join(person_projects))
            st.info("Deleting this person will remove them from these projects.")

        # Confirmation mechanism
        if confirm_action(f"deleting {selected_person}", "delete_person"):
            # Remove from projects
            for project in st.session_state.data["projects"]:
                if selected_person in project.get("assigned_resources", []):
                    project["assigned_resources"].remove(selected_person)

            # Remove from teams
            for team in st.session_state.data["teams"]:
                if selected_person in team.get("members", []):
                    team["members"].remove(selected_person)

            # Remove the person
            st.session_state.data["people"] = [
                p
                for p in st.session_state.data["people"]
                if p["name"] != selected_person
            ]

            st.success(f"Person '{selected_person}' deleted successfully.")
            st.rerun()
