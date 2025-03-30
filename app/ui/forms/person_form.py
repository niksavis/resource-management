"""
Person form components for the resource management application.

This module provides form components for creating, reading, updating, and deleting person resources.
"""

import streamlit as st
from typing import Dict, Any, Optional, List
from app.services.validation_service import validate_person
from app.utils.formatting import format_currency
from app.services.config_service import load_work_schedule_settings

# Add day code mapping
DAY_CODE_MAP = {
    # Full name to code
    "Monday": "MO",
    "Tuesday": "TU",
    "Wednesday": "WE",
    "Thursday": "TH",
    "Friday": "FR",
    "Saturday": "SA",
    "Sunday": "SU",
    # Code to full name (for reverse lookup)
    "MO": "Monday",
    "TU": "Tuesday",
    "WE": "Wednesday",
    "TH": "Thursday",
    "FR": "Friday",
    "SA": "Saturday",
    "SU": "Sunday",
}


def convert_days_to_display(day_codes: List[str]) -> List[str]:
    """Convert day codes (MO, TU) to display names (Monday, Tuesday)."""
    return [DAY_CODE_MAP.get(code, code) for code in day_codes]


def convert_days_to_codes(day_names: List[str]) -> List[str]:
    """Convert day names (Monday, Tuesday) to codes (MO, TU)."""
    return [DAY_CODE_MAP.get(name, name) for name in day_names]


def display_person_form(
    person_data: Optional[Dict[str, Any]] = None,
    on_submit: Optional[callable] = None,
    form_type: str = "add",  # Can be "add", "edit", or "delete"
) -> None:
    """
    Display a form for creating, editing, or deleting a person resource.

    Args:
        person_data: Existing data for the person (if editing)
        on_submit: Callback function to execute on form submission
        form_type: Type of form to display (add, edit, delete)
    """
    # Generate a unique form key to avoid duplicate element IDs
    form_key = f"person_form_{id(person_data)}_{form_type}"

    # Get default work schedule from settings
    work_schedule = load_work_schedule_settings()
    default_work_days = work_schedule.get(
        "work_days", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    )
    default_work_hours = work_schedule.get("work_hours", 8.0)

    # No header needed since we're using expanders in the parent component
    # Form does not need to be in an expander since the parent handles that

    # Pre-fill form fields if editing or deleting
    name = st.text_input(
        "Name",
        value=person_data.get("name", "") if person_data else "",
        key=f"{form_key}_name",
        disabled=form_type == "delete",
    )

    role = st.text_input(
        "Role",
        value=person_data.get("role", "") if person_data else "",
        key=f"{form_key}_role",
        disabled=form_type == "delete",
    )

    department = st.selectbox(
        "Department",
        options=[d["name"] for d in st.session_state.data["departments"]],
        index=0
        if not person_data
        or not person_data.get("department")
        in [d["name"] for d in st.session_state.data["departments"]]
        else [d["name"] for d in st.session_state.data["departments"]].index(
            person_data.get("department", "")
        ),
        key=f"{form_key}_department",
        disabled=form_type == "delete",
    )

    # Filter teams by selected department
    department_teams = [""] + [
        t["name"]
        for t in st.session_state.data["teams"]
        if t["department"] == department
    ]

    # Handle case when the person's current team is not in the filtered list
    team_index = 0
    if person_data and person_data.get("team"):
        if person_data["team"] in department_teams:
            team_index = department_teams.index(person_data["team"])
        else:
            # Add the team to options if it's valid but from a different department
            if any(
                t["name"] == person_data["team"] for t in st.session_state.data["teams"]
            ):
                department_teams.append(person_data["team"])
                team_index = len(department_teams) - 1
                st.warning(
                    f"Team '{person_data['team']}' is not from department '{department}'. "
                    f"Changing departments will reset this selection."
                )

    team = st.selectbox(
        "Team (Optional)",
        options=department_teams,
        index=team_index,
        key=f"{form_key}_team",
        disabled=form_type == "delete",
    )

    # Ensure the daily_cost is always a float
    cost_value = 0.0
    if person_data and "daily_cost" in person_data:
        # Convert to float explicitly to handle any integer values
        cost_value = float(person_data["daily_cost"])

    daily_cost = st.number_input(
        "Daily Cost",
        value=cost_value,  # Explicitly use float
        min_value=0.0,  # Explicitly use float
        step=50.0,  # Already float
        format="%.2f",
        key=f"{form_key}_daily_cost",
        disabled=form_type == "delete",
    )

    # Workdays as multiselect of actual days - with day code conversion
    all_days = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]

    # Convert day codes to display names for default values
    default_values = []
    if person_data and "work_days" in person_data:
        default_values = convert_days_to_display(person_data["work_days"])
    else:
        # Convert default_work_days to codes if they're not already
        if default_work_days and default_work_days[0] in DAY_CODE_MAP:
            default_values = default_work_days
        else:
            default_values = convert_days_to_display(
                convert_days_to_codes(default_work_days)
            )

    work_days = st.multiselect(
        "Work Days",
        options=all_days,
        default=default_values,
        key=f"{form_key}_work_days",
        disabled=form_type == "delete",
    )

    # Fix mixed numeric types by ensuring all are float
    # Get the daily work hours value, ensuring it's a float
    current_hours = 0.0
    if person_data and "daily_work_hours" in person_data:
        # Convert to float in case it's stored as an int
        current_hours = float(person_data["daily_work_hours"])
    else:
        # Ensure default is float
        current_hours = float(default_work_hours)

    daily_work_hours = st.number_input(
        "Daily Work Hours",
        value=current_hours,  # Now guaranteed to be float
        min_value=0.0,  # Using float
        max_value=24.0,  # Using float
        step=0.5,  # Already float
        format="%.1f",
        key=f"{form_key}_daily_work_hours",
        disabled=form_type == "delete",
    )

    # Skills field - maintain list of all skills in session state
    if "all_skills" not in st.session_state:
        st.session_state.all_skills = []

    # Get skills from person if editing
    person_skills = person_data.get("skills", []) if person_data else []

    # Ensure all person skills are in the all_skills list
    for skill in person_skills:
        if skill not in st.session_state.all_skills:
            st.session_state.all_skills.append(skill)

    # Option to select existing skills
    selected_skills = st.multiselect(
        "Skills",
        options=st.session_state.all_skills,
        default=person_skills,
        key=f"{form_key}_skills",
        disabled=form_type == "delete",
    )

    # Option to add new skills
    new_skill = st.text_input(
        "Add New Skill",
        key=f"{form_key}_new_skill",
        disabled=form_type == "delete",
    )

    if new_skill and new_skill not in st.session_state.all_skills:
        if st.button("Add Skill", key=f"{form_key}_add_skill"):
            st.session_state.all_skills.append(new_skill)
            selected_skills.append(new_skill)
            st.rerun()

    # Calculate capacity based on selected work days and hours
    if work_days and daily_work_hours > 0:
        capacity_week = len(work_days) * daily_work_hours
        capacity_month = capacity_week * 4.33  # Average weeks in a month

        st.metric("Capacity (Hours/Week)", f"{capacity_week:.1f}")
        st.metric("Capacity (Hours/Month)", f"{capacity_month:.1f}")

    # Submit button
    if form_type == "delete":
        button_label = "Delete Person"
        confirm = st.checkbox(
            "I confirm I want to delete this person", key=f"{form_key}_confirm"
        )
    else:
        button_label = "Submit"
        confirm = True

    if st.button(button_label, key=f"{form_key}_submit", use_container_width=True):
        if confirm:
            # Validate form data for add/edit
            if form_type != "delete":
                # Convert display day names back to day codes when saving
                day_codes = convert_days_to_codes(work_days)

                person = {
                    "name": name,
                    "role": role,
                    "department": department,
                    "team": team if team else "",
                    "daily_cost": daily_cost,
                    "work_days": day_codes,  # Use day codes for storage
                    "daily_work_hours": daily_work_hours,
                    "skills": selected_skills,
                    "capacity_hours_per_week": len(work_days) * daily_work_hours,
                    "capacity_hours_per_month": len(work_days)
                    * daily_work_hours
                    * 4.33,
                }

                validation_result, validation_errors = validate_person(person)
                if not validation_result:
                    st.error("Validation Errors: " + ", ".join(validation_errors))
                elif on_submit:
                    on_submit(person)
            # For delete, just pass the name
            elif on_submit:
                on_submit({"name": name})
        else:
            st.error("Please confirm the deletion by checking the box.")
