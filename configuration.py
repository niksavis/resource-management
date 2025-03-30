"""
Configuration module for resource management application.

This module provides functions for loading, saving, and managing application settings.
"""

import os
import json
import streamlit as st
import plotly.express as px
from typing import Dict, List, Tuple, Any, Optional

SETTINGS_FILE = "settings.json"


def create_default_settings() -> Dict[str, Any]:
    """
    Create default settings dictionary.

    Returns:
        Dictionary containing default application settings
    """
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


def ensure_settings_directory():
    """
    Ensure the directory for settings file exists.
    """
    try:
        # Get directory from settings file path
        settings_dir = os.path.dirname(SETTINGS_FILE)

        # If directory isn't empty string and doesn't exist, create it
        if settings_dir and not os.path.exists(settings_dir):
            os.makedirs(settings_dir)
    except Exception as e:
        st.error(f"Error ensuring settings directory: {str(e)}")


def load_settings_safely() -> Dict[str, Any]:
    """
    Load settings from file with error handling.

    Returns:
        Settings dictionary from file or default settings if loading fails
    """
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r") as file:
                return json.load(file)
        else:
            # Create default settings if file doesn't exist
            settings = create_default_settings()
            save_settings(settings)
            return settings
    except Exception as e:
        st.error(f"Error loading settings: {str(e)}")
        return create_default_settings()


def load_settings() -> Dict[str, Any]:
    """
    Load settings from file, falling back to defaults if needed.

    Returns:
        Settings dictionary
    """
    return load_settings_safely()


def save_settings(settings: Dict[str, Any]) -> None:
    """
    Save settings to file.

    Args:
        settings: Settings dictionary to save
    """
    try:
        ensure_settings_directory()
        with open(SETTINGS_FILE, "w") as file:
            json.dump(settings, file, indent=4)
    except Exception as e:
        st.error(f"Error saving settings: {str(e)}")


def regenerate_department_colors(departments: List[str]) -> None:
    """
    Regenerate colors for departments.

    Args:
        departments: List of department names
    """
    settings = load_settings()

    # Get existing department colors
    department_colors = settings.get("department_colors", {})

    # Get color palette
    colorscale = px.colors.qualitative.Plotly + px.colors.qualitative.D3

    # Generate colors for missing departments
    for i, dept in enumerate(departments):
        if dept not in department_colors:
            department_colors[dept] = colorscale[i % len(colorscale)].lower()

    # Remove colors for departments that no longer exist
    for dept in list(department_colors.keys()):
        if dept not in departments:
            del department_colors[dept]

    # Save updated colors
    settings["department_colors"] = department_colors
    save_settings(settings)


def add_department_color(department: str) -> None:
    """
    Add a color for a single department.

    Args:
        department: Department name
    """
    settings = load_settings()
    department_colors = settings.get("department_colors", {})

    # Only add if it doesn't already exist
    if department not in department_colors:
        # Get color palette
        colorscale = px.colors.qualitative.Plotly + px.colors.qualitative.D3

        # Calculate index based on length of existing colors
        idx = len(department_colors) % len(colorscale)
        department_colors[department] = colorscale[idx].lower()

        # Save updated colors
        settings["department_colors"] = department_colors
        save_settings(settings)


def delete_department_color(department: str) -> None:
    """
    Delete a department's color.

    Args:
        department: Department name to delete
    """
    settings = load_settings()
    department_colors = settings.get("department_colors", {})

    if department in department_colors:
        del department_colors[department]
        settings["department_colors"] = department_colors
        save_settings(settings)


def load_utilization_colorscale() -> List[List[Any]]:
    """
    Load utilization heatmap colorscale.

    Returns:
        List of [position, color] pairs for the colorscale
    """
    settings = load_settings()
    return settings.get(
        "heatmap_colorscale",
        [
            [0.0, "#f0f2f6"],  # No allocation
            [0.5, "#ffd700"],  # Moderate allocation
            [1.0, "#4b0082"],  # Full/over allocation
        ],
    )


def save_utilization_colorscale(colorscale: List[List[Any]]) -> None:
    """
    Save utilization heatmap colorscale.

    Args:
        colorscale: List of [position, color] pairs
    """
    settings = load_settings()
    settings["heatmap_colorscale"] = colorscale
    save_settings(settings)


def manage_visualization_colors(departments: List[str]) -> Dict[str, str]:
    """
    Manage department colors and return the color mapping.

    Args:
        departments: List of department names

    Returns:
        Dictionary mapping department names to colors
    """
    # Regenerate colors for all departments
    regenerate_department_colors(departments)

    # Return the color mapping
    return load_department_colors()


def load_currency_settings() -> Tuple[str, Dict[str, Any]]:
    """
    Load currency settings from settings file.

    Returns:
        Tuple of (currency_symbol, currency_format)
    """
    settings = load_settings()
    currency = settings.get("currency", "EUR")
    currency_format = settings.get(
        "currency_format", {"symbol_position": "prefix", "decimal_places": 2}
    )
    return currency, currency_format


def save_currency_settings(currency: str, currency_format: Dict[str, Any]) -> None:
    """
    Save currency settings to settings file.

    Args:
        currency: Currency symbol
        currency_format: Currency format settings
    """
    settings = load_settings()
    settings["currency"] = currency
    settings["currency_format"] = currency_format
    save_settings(settings)


def load_daily_cost_settings() -> float:
    """
    Load maximum daily cost setting.

    Returns:
        Maximum daily cost value
    """
    settings = load_settings()
    return settings.get("max_daily_cost", 2000.0)


def save_daily_cost_settings(max_daily_cost: float) -> None:
    """
    Save maximum daily cost setting.

    Args:
        max_daily_cost: Maximum daily cost value
    """
    settings = load_settings()
    settings["max_daily_cost"] = max_daily_cost
    save_settings(settings)


def display_color_settings():
    """Display color settings UI in Streamlit."""
    # This function has been moved to app/ui/settings.py
    st.warning("This function has been relocated to app/ui/settings.py")


def save_gantt_chart_colors(colors_dict: Dict[str, str]):
    """
    Save Gantt chart colors.

    Args:
        colors_dict: Dictionary mapping chart elements to colors
    """
    settings = load_settings()
    settings["gantt_chart_colors"] = colors_dict
    save_settings(settings)


def save_department_colors(colors_dict: Dict[str, str]):
    """
    Save department colors.

    Args:
        colors_dict: Dictionary mapping departments to colors
    """
    settings = load_settings()
    settings["department_colors"] = colors_dict
    save_settings(settings)


def load_heatmap_colorscale():
    """
    Load heatmap colorscale.

    Returns:
        Colorscale for heatmap
    """
    return load_utilization_colorscale()


def save_heatmap_colorscale(colorscale: List[List[Any]]):
    """
    Save heatmap colorscale.

    Args:
        colorscale: Colorscale for heatmap
    """
    save_utilization_colorscale(colorscale)


def load_gantt_chart_colors():
    """
    Load Gantt chart colors.

    Returns:
        Dictionary mapping chart elements to colors
    """
    settings = load_settings()
    return settings.get("gantt_chart_colors", {})


def load_department_colors():
    """
    Load department colors.

    Returns:
        Dictionary mapping departments to colors
    """
    settings = load_settings()
    return settings.get("department_colors", {})


def load_work_schedule_settings():
    """
    Load default work schedule settings.

    Returns:
        Dictionary with work_days and work_hours
    """
    settings = load_settings()
    return settings.get(
        "work_schedule",
        {
            "work_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
            "work_hours": 8.0,
        },
    )


def save_work_schedule_settings(work_schedule: Dict[str, Any]):
    """
    Save default work schedule settings.

    Args:
        work_schedule: Dictionary with work_days and work_hours
    """
    settings = load_settings()
    settings["work_schedule"] = work_schedule
    save_settings(settings)


def load_utilization_thresholds():
    """
    Load utilization threshold settings.

    Returns:
        Dictionary with under and over threshold values
    """
    settings = load_settings()
    return settings.get("utilization_thresholds", {"under": 50, "over": 100})


def save_utilization_thresholds(thresholds: Dict[str, int]):
    """
    Save utilization threshold settings.

    Args:
        thresholds: Dictionary with under and over threshold values
    """
    settings = load_settings()
    settings["utilization_thresholds"] = thresholds
    save_settings(settings)


def load_display_preferences():
    """
    Load display preferences settings.

    Returns:
        Dictionary with display preferences
    """
    settings = load_settings()
    return settings.get(
        "display_preferences",
        {"page_size": 10, "default_view": "Cards", "chart_height": 600},
    )


def save_display_preferences(preferences: Dict[str, Any]):
    """
    Save display preferences settings.

    Args:
        preferences: Dictionary with display preferences
    """
    settings = load_settings()
    settings["display_preferences"] = preferences
    save_settings(settings)
