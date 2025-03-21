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


def load_settings():
    """Load settings from a JSON file."""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as file:
                return json.load(file)
        except json.JSONDecodeError as e:
            st.error(
                f"Error decoding settings file: {e}. Reverting to default settings."
            )
        except Exception as e:
            st.error(
                f"Unexpected error loading settings file: {e}. Reverting to default settings."
            )
        # Provide fallback settings in case of error
        return {"department_colors": {}, "utilization_colorscale": []}
    return {"department_colors": {}, "utilization_colorscale": []}


def save_settings(settings):
    """Save settings to a JSON file."""
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
            ].lower()  # Ensure lowercase

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
            for i, (value, color) in enumerate(utilization_colorscale):
                new_color = st.color_picker(
                    f"Value {value * 100:.0f}%", color
                ).lower()  # Ensure lowercase
                if not new_color.startswith("#") or len(new_color) not in [4, 7]:
                    st.error(
                        f"Invalid hex color: {new_color}. Please use a valid hex code."
                    )
                    return
                if new_color != color:
                    utilization_colorscale[i][1] = new_color
                    modified = True

            submit = st.form_submit_button("Save Utilization Colors")
            if submit and modified:
                save_utilization_colorscale(utilization_colorscale)
                st.success("Utilization colors updated")
