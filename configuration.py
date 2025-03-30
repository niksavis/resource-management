import json
import os
import random
import streamlit as st
import plotly.express as px
from typing import Dict, List

SETTINGS_FILE = "settings.json"


def create_default_settings() -> Dict:
    """Creates a dictionary with default settings."""
    return {
        "currency": "€",
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


def ensure_settings_directory():
    """Ensure the directory for settings.json exists."""
    directory = os.path.dirname(SETTINGS_FILE)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)


def load_settings_safely() -> Dict:
    """
    Loads the settings from the file, with error handling.
    If loading fails, regenerates default settings.
    """
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r") as file:
                settings = json.load(file)
                return settings
        else:
            # File doesn't exist, create default settings
            settings = create_default_settings()
            save_settings(settings)
            return settings
    except json.JSONDecodeError as e:
        # Handle corrupted JSON
        st.warning(
            f"Settings file is corrupted: {str(e)}. Regenerating default settings."
        )

        # Create backup of corrupted file
        try:
            backup_file = f"{SETTINGS_FILE}.backup"
            with open(SETTINGS_FILE, "r") as src, open(backup_file, "w") as dst:
                dst.write(src.read())
            st.info(f"Backup of corrupted settings saved to {backup_file}")
        except Exception:
            pass

        # Generate and save default settings
        settings = create_default_settings()
        save_settings(settings)
        return settings
    except (FileNotFoundError, PermissionError) as e:
        # Handle file access issues
        st.warning(f"Cannot access settings file: {str(e)}. Using default settings.")
        settings = create_default_settings()
        try:
            save_settings(settings)
        except Exception:
            pass
        return settings
    except Exception as e:
        # Catch any other unexpected errors
        st.error(
            f"Unexpected error loading settings: {str(e)}. Using default settings."
        )
        return create_default_settings()


def load_settings() -> Dict:
    """
    Loads the settings from file, with fallback to safe loading if it fails.
    This maintains compatibility with existing code.
    """
    return load_settings_safely()


def save_settings(settings: Dict) -> None:
    """Saves the settings to the settings file with error handling."""
    try:
        ensure_settings_directory()
        with open(SETTINGS_FILE, "w") as file:
            json.dump(settings, file, indent=4)
    except Exception as e:
        st.error(f"Failed to save settings: {str(e)}")


def regenerate_department_colors(departments: List[str]) -> None:
    """Regenerates colors for all departments."""
    settings = load_settings()
    department_colors = settings.get("department_colors", {})

    # Generate new colors for missing departments
    colorscale = px.colors.qualitative.Plotly + px.colors.qualitative.D3
    for i, department in enumerate(departments):
        if department not in department_colors:
            department_colors[department] = colorscale[i % len(colorscale)].lower()

    settings["department_colors"] = department_colors
    save_settings(settings)


def add_department_color(department: str) -> None:
    """Adds a color for a new department."""
    settings = load_settings()
    department_colors = settings.get("department_colors", {})

    if department not in department_colors:
        colorscale = px.colors.qualitative.Plotly + px.colors.qualitative.D3
        department_colors[department] = colorscale[
            len(department_colors) % len(colorscale)
        ].lower()

    settings["department_colors"] = department_colors
    save_settings(settings)


def delete_department_color(department: str) -> None:
    """Deletes the color associated with a department."""
    settings = load_settings()
    department_colors = settings.get("department_colors", {})

    if department in department_colors:
        del department_colors[department]

    settings["department_colors"] = department_colors
    save_settings(settings)


def load_utilization_colorscale() -> List:
    """Loads the utilization colorscale from the settings file."""
    settings = load_settings()
    return settings.get("utilization_colorscale", [])


def save_utilization_colorscale(colorscale: List) -> None:
    """Save utilization colorscale to settings."""
    settings = load_settings()
    settings["utilization_colorscale"] = colorscale
    save_settings(settings)


def manage_visualization_colors(departments: List[str]) -> Dict[str, str]:
    """
    Ensures all departments have assigned colors and returns the updated color mapping.
    """
    regenerate_department_colors(departments)
    return load_department_colors()


def load_currency_settings() -> tuple[str, Dict]:
    """Loads the currency settings from the settings file."""
    settings = load_settings()
    currency = settings.get("currency", "EUR")
    currency_format = settings.get(
        "currency_format", {"symbol_position": "prefix", "decimal_places": 2}
    )
    return currency, currency_format


def save_currency_settings(currency: str, currency_format: Dict) -> None:
    """Saves the currency settings to the settings file."""
    settings = load_settings()
    settings["currency"] = currency
    settings["currency_format"] = currency_format
    save_settings(settings)


def load_daily_cost_settings() -> float:
    """Loads the maximum daily cost setting from the settings file."""
    settings = load_settings()
    return settings.get("max_daily_cost", 2000.0)


def save_daily_cost_settings(max_daily_cost: float) -> None:
    """Saves the maximum daily cost setting to the settings file."""
    settings = load_settings()
    settings["max_daily_cost"] = max_daily_cost
    save_settings(settings)


def display_color_settings():
    """Display and configure color settings for visualizations."""
    st.subheader("Color Settings")

    # Department Colors Section
    with st.expander("Department Colors", expanded=False):
        departments = [d["name"] for d in st.session_state.data["departments"]]
        dept_colors = load_department_colors()

        st.markdown("**Department Color Configuratrion**")
        new_colors = {}
        for dept in departments:
            new_colors[dept] = st.color_picker(
                f"{dept}",
                value=dept_colors.get(dept, "#4B0082"),
            )

        if st.button("Save Department Colors"):
            save_department_colors(new_colors)
            st.success("Department colors updated")

    # Gantt Chart Colors Section
    with st.expander("Gantt Chart Colors", expanded=False):
        colors = load_gantt_chart_colors()

        st.markdown("**Project Colors by Priority**")
        priority_colors = {}
        for priority in range(1, 6):
            priority_colors[priority] = st.color_picker(
                f"Priority {priority}",
                value=colors.get(
                    f"priority_{priority}",
                    "#" + "".join([f"{random.randint(0, 255):02x}" for _ in range(3)]),
                ),
            )

        if st.button("Save Chart Colors"):
            # Convert the priority colors to the expected format
            colors_dict = {f"priority_{p}": c for p, c in priority_colors.items()}
            save_gantt_chart_colors(colors_dict)
            st.success("Chart colors updated")

    # Matrix View Colors Section - FIXED FORM IMPLEMENTATION
    with st.expander("Matrix View Colors", expanded=False):
        heatmap_colorscale = load_heatmap_colorscale()

        # Single form for matrix colors
        with st.form(key="matrix_color_form"):
            st.markdown("**Matrix View Color Configuration**")
            col1, col2, col3 = st.columns(3)

            with col1:
                low_color = st.color_picker(
                    "No Allocation (0%)",
                    value=heatmap_colorscale[0][1]
                    if len(heatmap_colorscale) > 0
                    else "#f0f2f6",
                )

            with col2:
                medium_color = st.color_picker(
                    "Medium Allocation (50%)",
                    value=heatmap_colorscale[1][1]
                    if len(heatmap_colorscale) > 1
                    else "#ffd700",
                )

            with col3:
                high_color = st.color_picker(
                    "Full Allocation (100%+)",
                    value=heatmap_colorscale[2][1]
                    if len(heatmap_colorscale) > 2
                    else "#4b0082",
                )

            # Submit button within the form
            submit = st.form_submit_button("Save Matrix Colors")

        # Process form submission outside the form
        if submit:
            new_colorscale = [[0.0, low_color], [0.5, medium_color], [1.0, high_color]]
            save_heatmap_colorscale(new_colorscale)
            st.success("Matrix view colors updated")


def save_gantt_chart_colors(colors_dict):
    """Save Gantt chart colors to settings."""
    settings = load_settings()
    settings["gantt_chart_colors"] = colors_dict
    save_settings(settings)


def save_department_colors(colors_dict):
    """Save department colors to settings."""
    settings = load_settings()
    settings["department_colors"] = colors_dict
    save_settings(settings)


def load_heatmap_colorscale():
    """Load heatmap colorscale from settings"""
    settings = load_settings()
    return settings.get(
        "heatmap_colorscale",
        [
            (0.0, "#f0f2f6"),  # No allocation
            (0.5, "#ffd700"),  # Moderate allocation
            (1.0, "#4b0082"),  # Full/over allocation
        ],
    )


def save_heatmap_colorscale(colorscale):
    """Save heatmap colorscale to settings"""
    settings = load_settings()
    settings["heatmap_colorscale"] = colorscale
    save_settings(settings)


def load_gantt_chart_colors():
    """Load Gantt chart colors from settings."""
    settings = load_settings()
    return settings.get("gantt_chart_colors", {})


def load_department_colors():
    """Load department colors from settings."""
    settings = load_settings()
    return settings.get("department_colors", {})


def load_work_schedule_settings():
    """Load default work schedule settings from the settings file."""
    settings = load_settings()
    return settings.get(
        "work_schedule",
        {
            "work_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
            "work_hours": 8.0,
        },
    )


def save_work_schedule_settings(work_schedule):
    """Save default work schedule settings to the settings file."""
    settings = load_settings()
    settings["work_schedule"] = work_schedule
    save_settings(settings)


def load_utilization_thresholds():
    """Load utilization threshold settings from the settings file."""
    settings = load_settings()
    return settings.get("utilization_thresholds", {"under": 50, "over": 100})


def save_utilization_thresholds(thresholds):
    """Save utilization threshold settings to the settings file."""
    settings = load_settings()
    settings["utilization_thresholds"] = thresholds
    save_settings(settings)


def load_display_preferences():
    """Load display preference settings from the settings file."""
    settings = load_settings()
    return settings.get(
        "display_preferences",
        {"page_size": 10, "default_view": "Cards", "chart_height": 600},
    )


def save_display_preferences(preferences):
    """Save display preference settings to the settings file."""
    settings = load_settings()
    settings["display_preferences"] = preferences
    save_settings(settings)


def load_date_range_settings():
    """Load default date range settings from the settings file."""
    settings = load_settings()
    return settings.get("date_ranges", {"short": 30, "medium": 90, "long": 180})


def save_date_range_settings(date_ranges):
    """Save default date range settings to the settings file."""
    settings = load_settings()
    settings["date_ranges"] = date_ranges
    save_settings(settings)
