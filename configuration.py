import json
import os
import streamlit as st
from typing import Dict, List
import plotly.express as px

SETTINGS_FILE = "settings.json"


def ensure_settings_directory():
    """Ensure the directory for settings.json exists."""
    directory = os.path.dirname(SETTINGS_FILE)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)


def load_settings() -> Dict:
    """Loads the settings from the settings file."""
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as file:
            return json.load(file)
    return {}


def save_settings(settings: Dict) -> None:
    """Saves the settings to the settings file."""
    ensure_settings_directory()
    with open(SETTINGS_FILE, "w") as file:
        json.dump(settings, file, indent=4)


def load_department_colors() -> Dict[str, str]:
    """Loads department colors from the settings file."""
    settings = load_settings()
    return settings.get("department_colors", {})


def save_department_colors(colors: Dict[str, str]) -> None:
    """Save department colors to settings."""
    settings = load_settings()
    settings["department_colors"] = colors
    save_settings(settings)


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
    """Allow users to customize visualization colors."""
    st.subheader("Colors Settings")

    # Load current colors
    department_colors = load_department_colors()
    utilization_colorscale = load_utilization_colorscale()

    with st.expander("Customize Department Colors", expanded=False):
        modified = False
        with st.form("color_settings"):
            for dept, color in department_colors.items():
                new_color = st.color_picker(
                    f"{dept}", color
                ).lower()  # Ensure lowercase
                if new_color != color:
                    department_colors[dept] = new_color
                    modified = True

            submit = st.form_submit_button("Save Colors")
            if submit and modified:
                save_department_colors(department_colors)
                st.success("Department colors updated")

    with st.expander("Customize Utilization Colors", expanded=False):
        modified = False
        with st.form("utilization_color_settings"):
            new_utilization_colorscale = []
            for i, (value, color) in enumerate(utilization_colorscale):
                new_color = st.color_picker(
                    f"Value {value * 100:.0f}%", color
                ).lower()  # Ensure lowercase

                if not new_color.startswith("#") or len(new_color) not in [4, 7]:
                    st.error(
                        f"Invalid hex color: {new_color}. Please use a valid hex code."
                    )
                    continue

                new_utilization_colorscale.append([value, new_color])
                if new_color != color:
                    modified = True

            submit = st.form_submit_button("Save Utilization Colors")
            if submit and modified:
                save_utilization_colorscale(new_utilization_colorscale)
                st.success("Utilization colors updated")
