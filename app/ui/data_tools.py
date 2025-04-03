"""
Data Tools UI module.

This module provides the UI components for importing and exporting data.
"""

import streamlit as st
import pandas as pd
import io
from datetime import datetime
from typing import Dict, Any, List
from app.utils.ui_components import display_action_bar
from app.services.data_service import load_json, save_json
from app.services.config_service import regenerate_department_colors


def display_import_export_data_tab():
    """Display the data import/export tab."""
    display_action_bar()
    st.subheader("Data Tools")

    # Info message explaining the purpose of this page
    st.info(
        "Import data from external sources or export your data for backup and sharing purposes."
    )

    tabs = st.tabs(["Import Data", "Export Data"])

    with tabs[0]:
        display_import_section()

    with tabs[1]:
        display_export_section()


def display_import_section():
    """Display the enhanced data import section."""
    st.markdown("### Import Data")

    # Initialize import state variables in session state if they don't exist
    if "import_initiated" not in st.session_state:
        st.session_state.import_initiated = False
    if "import_confirmed" not in st.session_state:
        st.session_state.import_confirmed = False
    if "import_success" not in st.session_state:
        st.session_state.import_success = False
    if "import_data" not in st.session_state:
        st.session_state.import_data = None
    if "import_mode" not in st.session_state:
        st.session_state.import_mode = None
    if "import_resource_type" not in st.session_state:
        st.session_state.import_resource_type = None
    if "import_format" not in st.session_state:
        st.session_state.import_format = None
    if "show_import_message" not in st.session_state:
        st.session_state.show_import_message = False
    if "import_message" not in st.session_state:
        st.session_state.import_message = ""
    if "import_message_type" not in st.session_state:
        st.session_state.import_message_type = "info"

    # Function to handle starting the import process
    def start_import():
        st.session_state.import_initiated = True
        st.session_state.import_confirmed = False

    # Function to handle confirming the import
    def confirm_import():
        st.session_state.import_confirmed = True
        perform_import()

    # Function to cancel the import
    def cancel_import():
        st.session_state.import_initiated = False
        st.session_state.import_confirmed = False
        st.session_state.import_data = None
        st.session_state.import_mode = None
        st.session_state.import_resource_type = None
        st.session_state.import_format = None

    # Function to actually perform the import
    def perform_import():
        try:
            if st.session_state.import_mode == "Replace all existing data":
                if st.session_state.import_format == "JSON (.json)":
                    st.session_state.data = st.session_state.import_data
                else:
                    # Handle mapped data for Excel/CSV
                    if (
                        st.session_state.import_resource_type.lower()
                        in st.session_state.data
                    ):
                        st.session_state.data[
                            st.session_state.import_resource_type.lower()
                        ] = st.session_state.import_data
                st.session_state.import_message = "✅ Data replaced successfully! Your application is now using the imported data."
                st.session_state.import_message_type = "success"
            else:
                # Merge data
                if st.session_state.import_format == "JSON (.json)":
                    _merge_imported_data(st.session_state.import_data)
                else:
                    # Handle mapped data for Excel/CSV
                    existing = st.session_state.data.get(
                        st.session_state.import_resource_type.lower(), []
                    )
                    # Simple merge strategy - could be enhanced
                    st.session_state.data[
                        st.session_state.import_resource_type.lower()
                    ] = existing + st.session_state.import_data
                st.session_state.import_message = "✅ Data merged successfully! New entries have been added to your existing data."
                st.session_state.import_message_type = "success"

            # Set success flag and show message
            st.session_state.import_success = True
            st.session_state.show_import_message = True

            # Reset the import process
            st.session_state.import_initiated = False
            st.session_state.import_confirmed = False

        except Exception as e:
            st.session_state.import_message = f"❌ Error during import: {str(e)}"
            st.session_state.import_message_type = "error"
            st.session_state.show_import_message = True
            st.session_state.import_success = False

    # Display persistent messages if they exist
    if st.session_state.show_import_message:
        if st.session_state.import_message_type == "success":
            st.success(st.session_state.import_message)
        elif st.session_state.import_message_type == "error":
            st.error(st.session_state.import_message)
        else:
            st.info(st.session_state.import_message)

        # Add a button to clear the message
        if st.button("Clear Message", key="clear_import_message"):
            st.session_state.show_import_message = False
            st.session_state.import_message = ""
            st.rerun()

    # File format selection
    file_format = st.radio(
        "Select file format",
        options=["JSON (.json)", "Excel (.xlsx)", "CSV (.csv)"],
        horizontal=True,
    )

    # File uploader with dynamic file types
    allowed_types = {
        "JSON (.json)": ["json"],
        "Excel (.xlsx)": ["xlsx"],
        "CSV (.csv)": ["csv"],
    }
    uploaded_file = st.file_uploader(
        "Upload your data file",
        type=allowed_types[file_format],
        help="Select a file containing resource management data",
    )

    if uploaded_file is not None:
        try:
            # Process based on file format
            if file_format == "JSON (.json)":
                imported_data = load_json(uploaded_file)
            elif file_format == "Excel (.xlsx)":
                # Show sheet selection for Excel files
                xls = pd.ExcelFile(uploaded_file)
                sheet_name = st.selectbox("Select sheet", options=xls.sheet_names)
                df = pd.read_excel(uploaded_file, sheet_name=sheet_name)
                imported_data = df.to_dict(orient="records")
                st.dataframe(df.head(), use_container_width=True)
            else:  # CSV
                df = pd.read_csv(uploaded_file)
                imported_data = df.to_dict(orient="records")
                st.dataframe(df.head(), use_container_width=True)

            # For non-JSON formats, we need to map to our data structure
            resource_type = None
            if file_format != "JSON (.json)":
                with st.expander(
                    "Data Mapping (Required for Excel/CSV)", expanded=True
                ):
                    st.info("Map your columns to the required data fields.")
                    resource_type = st.selectbox(
                        "What type of data is this?",
                        options=["People", "Projects", "Teams", "Departments"],
                    )

                    # Show mapping UI based on selected resource type
                    if resource_type == "People":
                        imported_data = {"people": imported_data}

            # Validate data structure
            valid_data = False
            if file_format == "JSON (.json)":
                valid_data = _validate_imported_data(imported_data)
                if valid_data:
                    # Preview summary
                    with st.expander("Data Preview", expanded=True):
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("People", len(imported_data.get("people", [])))
                        with col2:
                            st.metric("Teams", len(imported_data.get("teams", [])))
                        with col3:
                            st.metric(
                                "Departments", len(imported_data.get("departments", []))
                            )
                        with col4:
                            st.metric(
                                "Projects", len(imported_data.get("projects", []))
                            )
                else:
                    st.error(
                        "The JSON file doesn't have the required structure (people, teams, departments, projects)."
                    )
            else:
                # For Excel/CSV we assume valid after mapping
                valid_data = True

            # Import options
            if valid_data and not st.session_state.import_initiated:
                st.markdown("#### Import Options")
                import_mode = st.radio(
                    "How should the data be imported?",
                    options=["Replace all existing data", "Merge with existing data"],
                    captions=[
                        "Overwrites all current data",
                        "Adds new entries while preserving existing ones",
                    ],
                    index=1,
                )

                # Store the necessary data in session state for later use
                st.session_state.import_data = imported_data
                st.session_state.import_mode = import_mode
                st.session_state.import_resource_type = resource_type
                st.session_state.import_format = file_format

                # Import button
                if st.button(
                    "Import Data",
                    type="primary",
                    use_container_width=True,
                    key="start_import",
                ):
                    start_import()
                    st.rerun()

            # Show confirmation dialog if import initiated
            if (
                st.session_state.import_initiated
                and not st.session_state.import_confirmed
            ):
                st.markdown("---")
                st.warning("⚠️ Confirmation Required")

                st.markdown(
                    f"You are about to **{st.session_state.import_mode.lower()}**. This action cannot be undone."
                )

                if st.session_state.import_mode == "Replace all existing data":
                    st.info(
                        "All existing data will be replaced with the imported data."
                    )
                else:
                    st.info("New entries will be added to your existing data.")

                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button(
                        "✅ Yes, proceed with import",
                        type="primary",
                        use_container_width=True,
                    ):
                        confirm_import()
                        st.rerun()
                with col2:
                    if st.button("❌ Cancel", use_container_width=True):
                        cancel_import()
                        st.rerun()

        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
            st.info("Please make sure your file has the correct format and try again.")


def display_export_section():
    """Display the enhanced data export section."""
    st.markdown("### Export Data")

    # Current data overview
    with st.expander("Current Data Summary", expanded=True):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("People", len(st.session_state.data.get("people", [])))
        with col2:
            st.metric("Teams", len(st.session_state.data.get("teams", [])))
        with col3:
            st.metric("Departments", len(st.session_state.data.get("departments", [])))
        with col4:
            st.metric("Projects", len(st.session_state.data.get("projects", [])))

    # File format selection
    file_format = st.radio(
        "Select export format",
        options=["JSON (.json)", "Excel (.xlsx)", "CSV (.csv)"],
        horizontal=True,
    )

    # Export data selection
    st.markdown("#### What data would you like to export?")
    export_options = [
        "All Data",
        "People Only",
        "Projects Only",
        "Teams Only",
        "Departments Only",
    ]
    export_type = st.selectbox("Data Selection", options=export_options)

    # File naming
    col1, col2 = st.columns([3, 1])
    with col1:
        # Determine default extension based on format
        extension = (
            ".json"
            if file_format == "JSON (.json)"
            else ".xlsx"
            if file_format == "Excel (.xlsx)"
            else ".csv"
        )
        filename_base = f"resource_data_{export_type.lower().replace(' ', '_').replace('_only', '')}"
        filename = st.text_input("Filename", value=f"{filename_base}{extension}")

    with col2:
        st.write("Options")
        include_date = st.checkbox(
            "Add date", value=True, help="Include current date in filename"
        )
        if include_date:
            filename = filename.replace(
                extension, f"_{datetime.now().strftime('%Y%m%d')}{extension}"
            )

    # Export button
    if st.button("Export Data", type="primary", use_container_width=True):
        with st.spinner("Preparing export..."):
            try:
                # Prepare data for export based on selection
                if export_type == "All Data":
                    export_data = st.session_state.data
                elif export_type == "People Only":
                    export_data = {"people": st.session_state.data.get("people", [])}
                elif export_type == "Projects Only":
                    export_data = {
                        "projects": st.session_state.data.get("projects", [])
                    }
                elif export_type == "Teams Only":
                    export_data = {"teams": st.session_state.data.get("teams", [])}
                elif export_type == "Departments Only":
                    export_data = {
                        "departments": st.session_state.data.get("departments", [])
                    }

                # Handle different file formats
                if file_format == "JSON (.json)":
                    # Generate download link for JSON
                    download_link = save_json(export_data, filename)
                    st.success("✅ Export ready for download!")
                    st.markdown(download_link, unsafe_allow_html=True)
                else:
                    # Convert to DataFrame for Excel/CSV
                    if export_type == "All Data":
                        # Create a separate dataframe for each data type
                        dfs = {}
                        for key, data in export_data.items():
                            if data:  # Only create dataframe if data exists
                                dfs[key] = pd.DataFrame(data)

                        if file_format == "Excel (.xlsx)":
                            # Create Excel with multiple sheets
                            buffer = io.BytesIO()
                            with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                                for sheet_name, df in dfs.items():
                                    df.to_excel(
                                        writer,
                                        sheet_name=sheet_name.capitalize(),
                                        index=False,
                                    )
                            buffer.seek(0)

                            st.success("✅ Export ready for download!")
                            st.download_button(
                                label="Download Excel File",
                                data=buffer,
                                file_name=filename,
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            )
                        else:  # CSV - we'll create a zip file with multiple CSVs
                            import zipfile

                            buffer = io.BytesIO()
                            with zipfile.ZipFile(buffer, "w") as zf:
                                for name, df in dfs.items():
                                    csv_buffer = io.StringIO()
                                    df.to_csv(csv_buffer, index=False)
                                    zf.writestr(f"{name}.csv", csv_buffer.getvalue())
                            buffer.seek(0)

                            zip_filename = filename.replace(".csv", ".zip")
                            st.success("✅ Export ready for download!")
                            st.download_button(
                                label="Download ZIP File",
                                data=buffer,
                                file_name=zip_filename,
                                mime="application/zip",
                            )
                    else:
                        # Single dataframe for the selected data type
                        data_key = export_type.lower().replace(" only", "")
                        df = pd.DataFrame(export_data.get(data_key, []))

                        if file_format == "Excel (.xlsx)":
                            buffer = io.BytesIO()
                            with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                                df.to_excel(writer, index=False)
                            buffer.seek(0)

                            st.success("✅ Export ready for download!")
                            st.download_button(
                                label="Download Excel File",
                                data=buffer,
                                file_name=filename,
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            )
                        else:  # CSV
                            csv = df.to_csv(index=False)

                            st.success("✅ Export ready for download!")
                            st.download_button(
                                label="Download CSV File",
                                data=csv,
                                file_name=filename,
                                mime="text/csv",
                            )
            except Exception as e:
                st.error(f"Error during export: {str(e)}")


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

    department_names = [d["name"] for d in st.session_state.data["departments"]]
    regenerate_department_colors(department_names)
