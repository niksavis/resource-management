"""
Person form components for the resource management application.

This module provides form components for creating, reading, updating, and deleting person resources.
"""

import streamlit as st
from typing import Dict, Any, Optional, List
from app.services.validation_service import validate_person
from app.utils.formatting import format_currency


def display_person_form(
    person_data: Optional[Dict[str, Any]] = None, on_submit: Optional[callable] = None
) -> None:
    """
    Display a form for creating or editing a person resource.

    Args:
        person_data: Existing data for the person (if editing)
        on_submit: Callback function to execute on form submission
    """
    st.header("Person Form")

    # Pre-fill form fields if editing
    name = st.text_input(
        "Name", value=person_data.get("name", "") if person_data else ""
    )
    role = st.text_input(
        "Role", value=person_data.get("role", "") if person_data else ""
    )
    department = st.selectbox(
        "Department",
        options=[d["name"] for d in st.session_state.data["departments"]],
        index=0
        if not person_data
        else [d["name"] for d in st.session_state.data["departments"]].index(
            person_data.get("department", "")
        ),
    )
    daily_cost = st.number_input(
        "Daily Cost",
        value=person_data.get("daily_cost", 0.0) if person_data else 0.0,
        format="%.2f",
    )
    work_days = st.number_input(
        "Work Days",
        value=person_data.get("work_days", 0) if person_data else 0,
        min_value=0,
        max_value=7,
    )
    daily_work_hours = st.number_input(
        "Daily Work Hours",
        value=person_data.get("daily_work_hours", 0.0) if person_data else 0.0,
        format="%.1f",
    )

    # Submit button
    if st.button("Submit"):
        # Validate form data
        person = {
            "name": name,
            "role": role,
            "department": department,
            "daily_cost": daily_cost,
            "work_days": work_days,
            "daily_work_hours": daily_work_hours,
        }
        validation_errors = validate_person(person)
        if validation_errors:
            st.error("Validation Errors: " + ", ".join(validation_errors))
        else:
            if on_submit:
                on_submit(person)
            st.success("Person data submitted successfully!")
