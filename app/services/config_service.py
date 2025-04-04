"""
Configuration service for the resource management application.

This module handles loading, saving, and accessing application configuration.
"""

import os
import json
from typing import Dict, List, Any, Tuple
import streamlit as st
import plotly.express as px

SETTINGS_FILE = "settings.json"


def load_settings() -> Dict[str, Any]:
    """Load settings from the settings file with error handling."""
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r") as file:
                return json.load(file)
        else:
            # File doesn't exist, create default settings
            settings = _create_default_settings()
            save_settings(settings)
            return settings
    except Exception as e:
        st.error(f"Error loading settings: {str(e)}")
        return _create_default_settings()


def save_settings(settings: Dict[str, Any]) -> None:
    """Save settings to the settings file with error handling."""
    try:
        with open(SETTINGS_FILE, "w") as file:
            json.dump(settings, file, indent=4)
    except Exception as e:
        st.error(f"Error saving settings: {str(e)}")


def _create_default_settings() -> Dict[str, Any]:
    """Create default settings dictionary."""
    return {
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


def load_currency_settings() -> Tuple[str, Dict[str, Any]]:
    """Load currency settings from the settings file."""
    settings = load_settings()
    currency = settings.get("currency", "EUR")
    currency_format = settings.get(
        "currency_format", {"symbol_position": "prefix", "decimal_places": 2}
    )
    return currency, currency_format


def save_currency_settings(currency: str, currency_format: Dict[str, Any]) -> None:
    """Save currency settings to the settings file."""
    settings = load_settings()
    settings["currency"] = currency
    settings["currency_format"] = currency_format
    save_settings(settings)


def load_department_colors() -> Dict[str, str]:
    """Load department colors from the settings file."""
    settings = load_settings()
    return settings.get("department_colors", {})


def save_department_colors(colors: Dict[str, str]) -> None:
    """
    Save department colors to the settings file.

    Args:
        colors: Dictionary mapping department names to color values
    """
    settings = load_settings()
    settings["department_colors"] = colors
    save_settings(settings)


def regenerate_department_colors(departments: List[str]) -> None:
    """Regenerate colors for all departments."""
    settings = load_settings()
    department_colors = settings.get("department_colors", {})

    # Generate new colors for missing departments
    colorscale = px.colors.qualitative.Plotly + px.colors.qualitative.D3
    for i, department in enumerate(departments):
        if department not in department_colors:
            department_colors[department] = colorscale[i % len(colorscale)].lower()

    settings["department_colors"] = department_colors
    save_settings(settings)


def add_department_color(department: str, color: str) -> None:
    """
    Add a department color to the settings.

    Args:
        department: Name of the department
        color: Color value (hex code or named color)
    """
    settings = load_settings()
    if "department_colors" not in settings:
        settings["department_colors"] = {}

    settings["department_colors"][department] = color
    save_settings(settings)


def remove_department_color(department_name: str) -> None:
    """
    Remove a department color from settings.

    Args:
        department_name: Name of the department to remove color for
    """
    department_colors = load_department_colors()

    if department_name in department_colors:
        del department_colors[department_name]
        save_department_colors(department_colors)


def ensure_department_colors(departments: List[Dict[str, Any]]) -> None:
    """
    Ensure all departments have a color assigned in settings.

    Args:
        departments: List of department dictionaries
    """
    department_colors = load_department_colors()
    modified = False

    # Get department names
    department_names = [dept["name"] for dept in departments]

    # Remove colors for departments that no longer exist
    colors_to_remove = [
        name for name in department_colors if name not in department_names
    ]
    for name in colors_to_remove:
        del department_colors[name]
        modified = True

    # Add colors for departments that don't have one
    from app.ui.forms.department_form import get_unused_color

    for dept in departments:
        dept_name = dept["name"]
        if dept_name not in department_colors:
            department_colors[dept_name] = get_unused_color()
            modified = True

    # Save if changes were made
    if modified:
        save_department_colors(department_colors)


def get_department_color(department_name: str, default_color: str = "#cccccc") -> str:
    """
    Get the color for a department from settings.

    Args:
        department_name: Name of the department
        default_color: Default color to return if department color is not found

    Returns:
        Hex color code for the department
    """
    department_colors = load_department_colors()
    return department_colors.get(department_name, default_color)


def load_display_preferences() -> Dict[str, Any]:
    """Load display preferences from the settings file."""
    settings = load_settings()
    return settings.get(
        "display_preferences",
        {"page_size": 10, "default_view": "Cards", "chart_height": 600},
    )


def save_display_preferences(preferences: Dict[str, Any]) -> None:
    """Save display preferences to the settings file."""
    settings = load_settings()
    settings["display_preferences"] = preferences
    save_settings(settings)


def load_utilization_thresholds() -> Dict[str, int]:
    """Load utilization thresholds from the settings file."""
    settings = load_settings()
    return settings.get("utilization_thresholds", {"under": 50, "over": 100})


def save_utilization_thresholds(thresholds: Dict[str, int]) -> None:
    """Save utilization thresholds to the settings file."""
    settings = load_settings()
    settings["utilization_thresholds"] = thresholds
    save_settings(settings)


def load_daily_cost_settings() -> float:
    """Load maximum daily cost setting from the settings file."""
    settings = load_settings()
    return settings.get("max_daily_cost", 2000.0)


def save_daily_cost_settings(max_daily_cost: float) -> None:
    """Save maximum daily cost setting to the settings file."""
    settings = load_settings()
    settings["max_daily_cost"] = max_daily_cost
    save_settings(settings)


def load_work_schedule_settings() -> Dict[str, Any]:
    """Load default work schedule settings from the settings file."""
    settings = load_settings()
    return settings.get(
        "work_schedule",
        {
            "work_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
            "work_hours": 8.0,
        },
    )


def save_work_schedule_settings(work_schedule: Dict[str, Any]) -> None:
    """Save default work schedule settings to the settings file."""
    settings = load_settings()
    settings["work_schedule"] = work_schedule
    save_settings(settings)


def load_date_range_settings() -> Dict[str, int]:
    """Load default date range settings from the settings file."""
    settings = load_settings()
    return settings.get("date_ranges", {"short": 30, "medium": 90, "long": 180})


def save_date_range_settings(date_ranges: Dict[str, int]) -> None:
    """Save default date range settings to the settings file."""
    settings = load_settings()
    settings["date_ranges"] = date_ranges
    save_settings(settings)


def load_heatmap_colorscale() -> List[List[Any]]:
    """Load heatmap colorscale from settings."""
    settings = load_settings()
    return settings.get(
        "heatmap_colorscale",
        [
            [0.0, "#f0f2f6"],  # No allocation
            [0.5, "#ffd700"],  # Moderate allocation
            [1.0, "#4b0082"],  # Full/over allocation
        ],
    )


def save_heatmap_colorscale(colorscale: List[List[Any]]) -> None:
    """Save heatmap colorscale to settings."""
    settings = load_settings()
    settings["heatmap_colorscale"] = colorscale
    save_settings(settings)
