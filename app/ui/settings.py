"""
Settings UI module.

This module provides the UI components for application settings and configuration.
"""

import streamlit as st
from typing import Dict, Any, List

from app.utils.ui_components import display_action_bar
from app.services.config_service import (
    load_currency_settings,
    save_currency_settings,
    load_display_preferences,
    save_display_preferences,
    load_work_schedule_settings,
    save_work_schedule_settings,
    load_utilization_thresholds,
    save_utilization_thresholds,
    load_daily_cost_settings,
    save_daily_cost_settings,
    load_date_range_settings,
    save_date_range_settings,
    load_department_colors,
    save_department_colors,
    load_heatmap_colorscale,
    save_heatmap_colorscale,
)


def display_settings_tab():
    """Display settings and configuration UI."""
    display_action_bar()
    st.subheader("Application Settings")

    # Added description to provide context to users
    st.info(
        "Configure application settings to customize your experience. Changes will be applied immediately."
    )

    settings_tabs = st.tabs(
        ["General Settings", "Display Preferences", "Cost Settings", "Color Settings"]
    )

    with settings_tabs[0]:
        display_general_settings()

    with settings_tabs[1]:
        display_display_preferences()

    with settings_tabs[2]:
        display_cost_settings()

    with settings_tabs[3]:
        display_color_settings()


def display_general_settings():
    """Display general settings (currency, date ranges, etc.)."""
    st.markdown("### General Settings")

    # Currency settings
    with st.expander("Currency Settings", expanded=True):
        currency, currency_format = load_currency_settings()

        col1, col2, col3 = st.columns(3)
        with col1:
            new_currency = st.text_input("Currency Symbol", value=currency)

        with col2:
            symbol_position = st.selectbox(
                "Symbol Position",
                options=["prefix", "suffix"],
                index=0 if currency_format["symbol_position"] == "prefix" else 1,
            )

        with col3:
            decimal_places = st.number_input(
                "Decimal Places",
                min_value=0,
                max_value=4,
                value=currency_format["decimal_places"],
            )

        # Add option for space between currency symbol and value
        add_space = st.checkbox(
            "Add space between currency symbol and value",
            value=currency_format.get("add_space", False),
            help="When checked, adds a space between the currency symbol and the amount (e.g., '$ 1,000' instead of '$1,000')",
        )

        # Added more space before the button for better separation
        st.write("")
        if st.button("Save Currency Settings", use_container_width=True):
            new_currency_format = {
                "symbol_position": symbol_position,
                "decimal_places": decimal_places,
                "add_space": add_space,  # Save the space setting
            }
            save_currency_settings(new_currency, new_currency_format)
            st.success("Currency settings saved!")
            st.rerun()

    # Date range settings - now collapsed by default
    with st.expander("Date Range Settings", expanded=False):
        date_ranges = load_date_range_settings()

        col1, col2, col3 = st.columns(3)
        with col1:
            short_range = st.number_input(
                "Short Range (days)",
                min_value=1,
                max_value=90,
                value=date_ranges.get("short", 30),
            )

        with col2:
            medium_range = st.number_input(
                "Medium Range (days)",
                min_value=30,
                max_value=180,
                value=date_ranges.get("medium", 90),
            )

        with col3:
            long_range = st.number_input(
                "Long Range (days)",
                min_value=90,
                max_value=365,
                value=date_ranges.get("long", 180),
            )

        if st.button("Save Date Range Settings"):
            new_date_ranges = {
                "short": short_range,
                "medium": medium_range,
                "long": long_range,
            }
            save_date_range_settings(new_date_ranges)
            st.success("Date range settings saved!")
            st.rerun()

    # Work schedule settings
    with st.expander("Default Work Schedule", expanded=False):
        work_schedule = load_work_schedule_settings()

        work_days = work_schedule.get(
            "work_days", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        )
        daily_hours = work_schedule.get("work_hours", 8.0)

        new_work_days = st.multiselect(
            "Default Work Days",
            options=[
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
                "Sunday",
            ],
            default=work_days,
        )

        new_daily_hours = st.number_input(
            "Default Daily Work Hours",
            min_value=0.5,
            max_value=24.0,
            value=float(daily_hours),
            step=0.5,
        )

        if st.button("Save Work Schedule"):
            new_work_schedule = {
                "work_days": new_work_days,
                "work_hours": new_daily_hours,
            }
            save_work_schedule_settings(new_work_schedule)
            st.success("Work schedule settings saved!")
            st.rerun()

    # Utilization thresholds
    with st.expander("Utilization Thresholds", expanded=False):
        thresholds = load_utilization_thresholds()

        col1, col2 = st.columns(2)
        with col1:
            under_threshold = st.slider(
                "Underutilization Threshold (%)",
                min_value=0,
                max_value=100,
                value=thresholds.get("under", 50),
                help="Resources below this threshold are considered underutilized",
            )

        with col2:
            over_threshold = st.slider(
                "Overutilization Threshold (%)",
                min_value=under_threshold,
                max_value=150,
                value=thresholds.get("over", 100),
                help="Resources above this threshold are considered overutilized",
            )

        if st.button("Save Utilization Thresholds"):
            new_thresholds = {"under": under_threshold, "over": over_threshold}
            save_utilization_thresholds(new_thresholds)
            st.success("Utilization thresholds saved!")
            st.rerun()


def display_display_preferences():
    """Display UI settings and preferences."""
    st.markdown("### Display Preferences")

    # Load current preferences
    prefs = load_display_preferences()

    # Converted form to expanders for consistency
    # Pagination settings
    with st.expander("Pagination Settings", expanded=True):
        page_size = st.number_input(
            "Items Per Page",
            min_value=5,
            max_value=100,
            value=prefs.get("page_size", 10),
            step=5,
            help="Number of items to display per page in tables and lists",
        )

        st.write("")
        if st.button("Save Pagination Settings", use_container_width=True):
            new_prefs = prefs.copy()
            new_prefs["page_size"] = page_size
            save_display_preferences(new_prefs)
            st.success("Pagination settings saved!")
            st.rerun()

    # Chart settings
    with st.expander("Chart Settings", expanded=False):
        chart_height = st.number_input(
            "Default Chart Height (px)",
            min_value=300,
            max_value=1200,
            value=prefs.get("chart_height", 600),
            step=50,
            help="Default height for charts and visualizations",
        )

        st.write("")
        if st.button("Save Chart Settings", use_container_width=True):
            new_prefs = prefs.copy()
            new_prefs["chart_height"] = chart_height
            save_display_preferences(new_prefs)
            st.success("Chart settings saved!")
            st.rerun()

    # Default view for resources
    with st.expander("Resource View", expanded=False):
        default_view = st.radio(
            "Default Resource View",
            options=["Cards", "Visual Map"],
            index=0 if prefs.get("default_view", "Cards") == "Cards" else 1,
            horizontal=True,
            help="Default view for displaying resources",
        )

        st.write("")
        if st.button("Save Resource View Settings", use_container_width=True):
            new_prefs = prefs.copy()
            new_prefs["default_view"] = default_view
            save_display_preferences(new_prefs)
            st.success("Resource view preferences saved!")
            st.rerun()


def display_cost_settings():
    """Display cost-related settings."""
    st.markdown("### Cost Settings")

    # Max daily cost setting
    with st.expander("Daily Cost Limit", expanded=True):
        max_daily_cost = load_daily_cost_settings()

        new_max_cost = st.number_input(
            "Maximum Daily Cost Limit",
            min_value=100.0,
            max_value=10000.0,
            value=float(max_daily_cost),
            step=100.0,
            help="Maximum daily cost allowed for a resource",
        )

        # Added description for clarity
        st.caption(
            "This setting affects resource cost calculations throughout the application"
        )

        st.write("")
        if st.button("Save Cost Limit", use_container_width=True):
            save_daily_cost_settings(new_max_cost)
            st.success("Daily cost limit saved!")
            st.rerun()


def display_color_settings():
    """Display and configure color settings for visualizations."""
    st.markdown("### Color Settings")

    # Department colors
    with st.expander("Department Colors", expanded=True):
        departments = [d["name"] for d in st.session_state.data["departments"]]
        dept_colors = load_department_colors()

        if not departments:
            st.info(
                "No departments available. Add departments to customize their colors."
            )
        else:
            st.markdown("**Department Color Configuration**")
            st.caption(
                "Choose distinctive colors to easily identify departments in charts and reports"
            )
            new_colors = {}

            # Create a multi-column layout for better space utilization
            cols = st.columns(3)
            for i, dept in enumerate(departments):
                default_color = dept_colors.get(dept, "#4B0082")
                with cols[i % 3]:
                    new_colors[dept] = st.color_picker(
                        f"{dept}", value=default_color, key=f"color_{dept}"
                    )

            st.write("")
            if st.button("Save Department Colors", use_container_width=True):
                save_department_colors(new_colors)
                st.success("Department colors updated!")
                st.rerun()

    # Heatmap colors for resource allocations
    with st.expander("Resource Allocation Colors", expanded=False):
        heatmap_colorscale = load_heatmap_colorscale()

        st.markdown("**Resource Allocation Color Scale**")
        st.info("Define colors for different allocation levels (0% to 100%+)")
        st.caption(
            "These colors will be used in allocation heatmaps and visualizations"
        )

        # Convert colorscale format if needed
        if isinstance(heatmap_colorscale[0], list):
            colorscale_dict = {
                int(level * 100): color for level, color in heatmap_colorscale
            }
        else:
            colorscale_dict = heatmap_colorscale

        col1, col2, col3 = st.columns(3)

        with col1:
            low_color = st.color_picker(
                "No Allocation (0%)",
                value=colorscale_dict.get(0, "#f0f2f6"),
                key="heatmap_low",
            )

        with col2:
            mid_color = st.color_picker(
                "Moderate Allocation (50%)",
                value=colorscale_dict.get(50, "#ffd700"),
                key="heatmap_mid",
            )

        with col3:
            high_color = st.color_picker(
                "Full/Over Allocation (100%+)",
                value=colorscale_dict.get(100, "#4b0082"),
                key="heatmap_high",
            )

        # Preview of color scale
        st.write("Preview:")
        preview_cols = st.columns(5)
        with preview_cols[0]:
            st.markdown(
                f'<div style="background-color:{low_color};height:20px;border-radius:3px;"></div>',
                unsafe_allow_html=True,
            )
            st.caption("0%")
        with preview_cols[1]:
            blend1 = f"linear-gradient(90deg, {low_color} 0%, {mid_color} 100%)"
            st.markdown(
                f'<div style="background:{blend1};height:20px;border-radius:3px;"></div>',
                unsafe_allow_html=True,
            )
            st.caption("25%")
        with preview_cols[2]:
            st.markdown(
                f'<div style="background-color:{mid_color};height:20px;border-radius:3px;"></div>',
                unsafe_allow_html=True,
            )
            st.caption("50%")
        with preview_cols[3]:
            blend2 = f"linear-gradient(90deg, {mid_color} 0%, {high_color} 100%)"
            st.markdown(
                f'<div style="background:{blend2};height:20px;border-radius:3px;"></div>',
                unsafe_allow_html=True,
            )
            st.caption("75%")
        with preview_cols[4]:
            st.markdown(
                f'<div style="background-color:{high_color};height:20px;border-radius:3px;"></div>',
                unsafe_allow_html=True,
            )
            st.caption("100%")

        st.write("")
        if st.button("Save Allocation Colors", use_container_width=True):
            new_colorscale = [[0.0, low_color], [0.5, mid_color], [1.0, high_color]]
            save_heatmap_colorscale(new_colorscale)
            st.success("Allocation colors updated!")
            st.rerun()
