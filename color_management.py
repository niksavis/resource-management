"""
Color Management Module

This module contains functions for dynamically managing and customizing
colors for visualizations in the resource management application.
"""

import streamlit as st
import plotly.express as px


def manage_visualization_colors(departments):
    """Dynamically assign and manage colors for visualizations."""

    # Initialize department colors if not in session state
    if "department_colors" not in st.session_state:
        # Generate initial colors using Plotly's qualitative colorscales
        colorscale = px.colors.qualitative.Plotly

        # Map departments to colors
        st.session_state.department_colors = {
            dept: colorscale[i % len(colorscale)] for i, dept in enumerate(departments)
        }

    # Check for new departments not in the color mapping
    for dept in departments:
        if dept not in st.session_state.department_colors:
            # Assign a new color from Plotly's extended colorscales
            extended_colors = px.colors.qualitative.Plotly + px.colors.qualitative.D3
            st.session_state.department_colors[dept] = extended_colors[
                len(st.session_state.department_colors) % len(extended_colors)
            ]

    return st.session_state.department_colors


def display_color_settings():
    """Allow users to customize visualization colors."""
    st.subheader("Visualization Colors")

    with st.expander("Customize Department Colors", expanded=False):
        # Get current color mapping
        colors = st.session_state.department_colors

        # Create a form for color editing
        with st.form("color_settings"):
            modified = False
            for dept, color in colors.items():
                new_color = st.color_picker(f"{dept}", color)
                if new_color != color:
                    st.session_state.department_colors[dept] = new_color
                    modified = True

            submit = st.form_submit_button("Save Colors")
            if submit and modified:
                st.success("Color settings updated")
