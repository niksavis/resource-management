"""
Data Tools UI module.

This module provides the UI components for importing and exporting data.
"""

import streamlit as st
import pandas as pd
import json
import io
from typing import Dict, Any, List

from app.utils.ui_components import display_action_bar, confirm_action
from app.services.data_service import load_json, save_json, save_data


def display_import_export_data_tab():
    """Display the data import/export tab."""
    display_action_bar()
    st.subheader("Data Tools")

    col1, col2 = st.columns(2)

    with col1:
        _display_import_section()

    with col2:
        _display_export_section()

    # Backup/Restore section
    st.markdown("---")
    st.subheader("Data Backup & Restore")
    _display_backup_restore_section()


def _display_import_section():
    """Display the data import section."""
    st.markdown("### Import Data")

    # Upload JSON file
    uploaded_file = st.file_uploader("Upload JSON Data", type=["json"])

    if uploaded_file is not None:
        try:
            # Load and validate the uploaded data
            imported_data = load_json(uploaded_file)

            # Check if the data has the expected structure
            if _validate_imported_data(imported_data):
                # Preview the imported data
                st.success("Data validated successfully!")

                with st.expander("Preview Imported Data", expanded=False):
                    st.write(f"People: {len(imported_data.get('people', []))}")
                    st.write(f"Teams: {len(imported_data.get('teams', []))}")
                    st.write(
                        f"Departments: {len(imported_data.get('departments', []))}"
                    )
                    st.write(f"Projects: {len(imported_data.get('projects', []))}")

                # Import options
                import_mode = st.radio(
                    "Import Mode",
                    options=["Replace All Data", "Merge with Existing Data"],
                    index=0,
                )

                # Process import
                if st.button("Import Data"):
                    if import_mode == "Replace All Data":
                        st.session_state.data = imported_data
                        st.success("All data replaced successfully!")
                    else:
                        # Merge data
                        _merge_imported_data(imported_data)
                        st.success("Data merged successfully!")

                    st.rerun()
            else:
                st.error(
                    "Invalid data format. The uploaded JSON must contain people, teams, departments, and projects."
                )
        except Exception as e:
            st.error(f"Error processing the uploaded file: {str(e)}")


def _validate_imported_data(data: Dict[str, Any]) -> bool:
    """
    Validate that imported data has the required structure.

    Args:
        data: The imported data to validate

    Returns:
        True if the data is valid, False otherwise
    """
    # Check if the required keys exist
    required_keys = ["people", "teams", "departments", "projects"]
    if not all(key in data for key in required_keys):
        return False

    # Check if the values are lists
    if not all(isinstance(data[key], list) for key in required_keys):
        return False

    # Additional validation could be added here

    return True


def _merge_imported_data(imported_data: Dict[str, List[Dict[str, Any]]]):
    """
    Merge imported data with existing data.

    Args:
        imported_data: The imported data to merge
    """
    # For each resource type, merge based on unique names
    for resource_type in ["people", "teams", "departments", "projects"]:
        existing_items = st.session_state.data.get(resource_type, [])
        existing_names = {item["name"] for item in existing_items}

        # Add new items from imported data
        for item in imported_data.get(resource_type, []):
            if item["name"] not in existing_names:
                existing_items.append(item)
                existing_names.add(item["name"])

    # Update department colors
    from app.services.config_service import regenerate_department_colors

    department_names = [d["name"] for d in st.session_state.data["departments"]]
    regenerate_department_colors(department_names)


def _display_export_section():
    """Display the data export section."""
    st.markdown("### Export Data")

    # Display current data stats
    st.markdown("**Current Data:**")
    st.write(f"People: {len(st.session_state.data.get('people', []))}")
    st.write(f"Teams: {len(st.session_state.data.get('teams', []))}")
    st.write(f"Departments: {len(st.session_state.data.get('departments', []))}")
    st.write(f"Projects: {len(st.session_state.data.get('projects', []))}")

    # Export options
    export_options = [
        "All Data",
        "People Only",
        "Projects Only",
        "Teams Only",
        "Departments Only",
    ]
    export_type = st.selectbox("Select Data to Export", options=export_options)

    filename = st.text_input("Filename", value="resource_data.json")

    if st.button("Export Data"):
        # Prepare data for export based on selection
        if export_type == "All Data":
            export_data = st.session_state.data
        elif export_type == "People Only":
            export_data = {"people": st.session_state.data.get("people", [])}
        elif export_type == "Projects Only":
            export_data = {"projects": st.session_state.data.get("projects", [])}
        elif export_type == "Teams Only":
            export_data = {"teams": st.session_state.data.get("teams", [])}
        elif export_type == "Departments Only":
            export_data = {"departments": st.session_state.data.get("departments", [])}

        # Generate download link
        download_link = save_json(export_data, filename)
        st.markdown(download_link, unsafe_allow_html=True)


def _display_backup_restore_section():
    """Display the data backup and restore section."""
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Backup Data")
        backup_filename = st.text_input(
            "Backup Filename", value="resource_data_backup.json"
        )

        if st.button("Create Backup"):
            # Save current data to backup file
            success = save_data(st.session_state.data, backup_filename)
            if success:
                st.success(f"Data backed up successfully to {backup_filename}")
            else:
                st.error("Failed to create backup. Check permissions and try again.")

    with col2:
        st.markdown("### Restore From Backup")
        restore_file = st.file_uploader(
            "Upload Backup File", type=["json"], key="restore_file"
        )

        if restore_file is not None:
            try:
                backup_data = load_json(restore_file)
                if _validate_imported_data(backup_data):
                    if st.button("Restore Data"):
                        st.session_state.data = backup_data
                        st.success("Data restored successfully!")
                        st.rerun()
                else:
                    st.error("Invalid backup file format.")
            except Exception as e:
                st.error(f"Error processing backup file: {str(e)}")
