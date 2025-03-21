"""
Color Management Module

This module contains functions for dynamically managing and customizing
colors for visualizations in the resource management application.
"""

import json
import os
import streamlit as st
import plotly.express as px

SETTINGS_FILE = "settings.json"


def ensure_settings_directory():
    """Ensure the directory for settings.json exists."""
    directory = os.path.dirname(SETTINGS_FILE)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)


def load_settings():
    """Load settings from a JSON file or create default settings if missing."""
    if not os.path.exists(SETTINGS_FILE):
        departments = [d["name"] for d in st.session_state.data["departments"]]
        default_settings = {
            "department_colors": {
                dept: px.colors.qualitative.Plotly[
                    i % len(px.colors.qualitative.Plotly)
                ]
                for i, dept in enumerate(departments)
            },
            "utilization_colorscale": [
                [0, "#00FF00"],
                [0.5, "#FFFF00"],
                [1, "#FF0000"],
            ],
        }
        save_settings(default_settings)
        return default_settings

    try:
        with open(SETTINGS_FILE, "r") as file:
            return json.load(file)
    except (json.JSONDecodeError, FileNotFoundError):
        st.error("Error loading settings. Using default settings.")
        return {
            "department_colors": {},
            "utilization_colorscale": [
                [0, "#00FF00"],
                [0.5, "#FFFF00"],
                [1, "#FF0000"],
            ],
        }


def save_settings(settings):
    """Save settings to a JSON file."""
    ensure_settings_directory()
    with open(SETTINGS_FILE, "w") as file:
        json.dump(settings, file, indent=4)


def load_department_colors():
    """Load department colors from settings."""
    settings = load_settings()
    return settings.get("department_colors", {})


def save_department_colors(colors):
    """Save department colors to settings."""
    settings = load_settings()
    settings["department_colors"] = colors
    save_settings(settings)


def load_utilization_colorscale():
    """Load utilization colorscale from settings."""
    settings = load_settings()
    return settings.get("utilization_colorscale", [])


def save_utilization_colorscale(colorscale):
    """Save utilization colorscale to settings."""
    settings = load_settings()
    settings["utilization_colorscale"] = colorscale
    save_settings(settings)


def manage_visualization_colors(departments):
    """Dynamically assign and manage colors for visualizations."""
    # Load existing colors
    department_colors = load_department_colors()

    # Generate new colors for departments not in the file
    colorscale = px.colors.qualitative.Plotly + px.colors.qualitative.D3
    for dept in departments:
        if dept not in department_colors:
            department_colors[dept] = colorscale[
                len(department_colors) % len(colorscale)
            ].lower()

    # Remove departments that no longer exist
    departments_to_remove = [
        dept for dept in department_colors if dept not in departments
    ]
    for dept in departments_to_remove:
        del department_colors[dept]

    # Save updated colors
    save_department_colors(department_colors)

    return department_colors


def display_color_settings():
    """Allow users to customize visualization colors."""
    st.subheader("Visualization Colors")

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


def add_department_color(department_name):
    """Add a color for a new department."""
    settings = load_settings()
    department_colors = settings.get("department_colors", {})
    if department_name not in department_colors:
        # Choose a color from a predefined palette
        colorscale = px.colors.qualitative.Plotly + px.colors.qualitative.D3
        available_colors = [
            color.lower()
            for color in colorscale
            if color.lower() not in department_colors.values()
        ]
        if available_colors:
            department_colors[department_name] = available_colors[0]
        else:
            department_colors[department_name] = "#808080"  # Default gray
        settings["department_colors"] = department_colors
        save_settings(settings)


def delete_department_color(department_name):
    """Remove a department's color when it is deleted."""
    settings = load_settings()
    department_colors = settings.get("department_colors", {})
    if department_name in department_colors:
        del department_colors[department_name]
        settings["department_colors"] = department_colors
        save_settings(settings)


def regenerate_department_colors(departments):
    """Regenerate department colors based on the current departments."""
    settings = load_settings()
    department_colors = {}
    colorscale = px.colors.qualitative.Plotly + px.colors.qualitative.D3
    for i, department in enumerate(departments):
        department_colors[department] = colorscale[i % len(colorscale)].lower()
    settings["department_colors"] = department_colors
    save_settings(settings)


def load_currency_settings():
    """Load currency settings from the settings file."""
    settings = load_settings()
    return settings.get("currency", "USD"), settings.get(
        "currency_format",
        {"symbol_position": "prefix", "decimal_places": 2},
    )


def save_currency_settings(currency, currency_format):
    """Save currency settings to the settings file."""
    settings = load_settings()
    settings["currency"] = currency
    settings["currency_format"] = currency_format
    save_settings(settings)
