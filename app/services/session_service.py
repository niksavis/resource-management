"""
Session management service to handle Streamlit session state.
"""

import os
import json
import streamlit as st
import pandas as pd
import plotly.express as px

from app.services.data_service import load_demo_data, check_data_integrity


def initialize_session_state():
    """Initialize all session state variables used throughout the application."""
    # Initialize data if not present
    if "data" not in st.session_state:
        try:
            st.session_state.data = load_demo_data()
        except Exception as e:
            st.error(f"Error loading data: {str(e)}")
            st.session_state.data = {
                "people": [],
                "teams": [],
                "departments": [],
                "projects": [],
            }

    # Initialize settings configuration
    settings_file = "settings.json"
    if not os.path.exists(settings_file):
        _create_default_settings_file(settings_file)

    # Initialize active tab if not set
    if "active_tab" not in st.session_state:
        st.session_state.active_tab = "Dashboard"

    # Initialize resource view state
    if "resource_view" not in st.session_state:
        st.session_state.resource_view = "All Resources"

    # Initialize project form state variables
    _initialize_project_form_states()

    # Verify data integrity
    check_data_integrity()


def _create_default_settings_file(settings_file: str):
    """Create a default settings file with initial values."""
    departments = [d["name"] for d in st.session_state.data["departments"]]

    default_settings = {
        "currency": "EUR",
        "currency_format": {"symbol_position": "prefix", "decimal_places": 2},
        "department_colors": {},
        "heatmap_colorscale": [
            [0.0, "#f0f2f6"],  # No allocation
            [0.5, "#ffd700"],  # Moderate allocation
            [1.0, "#4b0082"],  # Full/over allocation
        ],
        "max_daily_cost": 2000.0,
        "work_schedule": {
            "work_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
            "work_hours": 8.0,
        },
        "utilization_thresholds": {"under": 50, "over": 100},
        "display_preferences": {
            "page_size": 10,
            "default_view": "Cards",
            "chart_height": 600,
        },
        "date_ranges": {"short": 30, "medium": 90, "long": 180},
    }

    # Generate colors for departments
    colorscale = px.colors.qualitative.Plotly + px.colors.qualitative.D3
    for i, dept in enumerate(departments):
        default_settings["department_colors"][dept] = colorscale[
            i % len(colorscale)
        ].lower()

    # Write to file
    try:
        with open(settings_file, "w") as file:
            json.dump(default_settings, file, indent=4)
    except Exception as e:
        st.error(f"Error creating settings file: {str(e)}")


def _initialize_project_form_states():
    """Initialize all project form related session state variables."""
    # For adding new projects
    if "new_project_people" not in st.session_state:
        st.session_state.new_project_people = []

    if "new_project_teams" not in st.session_state:
        st.session_state.new_project_teams = []

    if "new_project_departments" not in st.session_state:
        st.session_state.new_project_departments = []

    # For editing existing projects
    if "edit_project_people" not in st.session_state:
        st.session_state.edit_project_people = []

    if "edit_project_teams" not in st.session_state:
        st.session_state.edit_project_teams = []

    if "edit_project_departments" not in st.session_state:
        st.session_state.edit_project_departments = []

    # For tracking the currently edited project
    if "last_edited_project" not in st.session_state:
        st.session_state.last_edited_project = None

    if "edit_form_initialized" not in st.session_state:
        st.session_state.edit_form_initialized = False


def initialize_filter_state():
    """Initialize consistent filter state if not already present."""
    if "filter_state" not in st.session_state:
        st.session_state.filter_state = {
            "date_range": [
                pd.Timestamp.now(),
                pd.Timestamp.now() + pd.Timedelta(days=90),
            ],
            "resource_types": ["Person", "Team", "Department"],
            "dept_filter": [],
            "project_filter": [],
            "utilization_threshold": 0,
        }


def get_active_tab() -> str:
    """Get the currently active tab from session state."""
    return st.session_state.get("active_tab", "Dashboard")


def set_active_tab(tab_name: str):
    """Set the active tab in session state."""
    st.session_state.active_tab = tab_name

    # Reset any tab-specific state when changing tabs
    if tab_name == "Project Management":
        # Reset project form states
        st.session_state.edit_form_initialized = False
        st.session_state.last_edited_project = None
