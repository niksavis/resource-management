"""
Main entry point for the Resource Management Application.
Orchestrates the application flow and handles session state.
"""

import streamlit as st
from app.ui.dashboard import display_home_tab
from app.ui.resource_management import display_manage_resources_tab
from app.ui.project_management import display_manage_projects_tab
from app.ui.analytics import (
    display_visualize_data_tab,
    display_resource_utilization_tab,
    display_capacity_planning_tab,
    display_resource_calendar_tab,
)
from app.ui.settings import display_settings_tab
from app.ui.data_tools import display_import_export_data_tab
from app.services.session_service import (
    initialize_session_state,
    initialize_filter_state,
)
from app.utils.styling import apply_custom_css
from app.services.data_service import check_data_integrity
from app.services.data_service import check_circular_dependencies
from app.ui.components import display_filtered_resource
from app.ui.forms.department_form import display_department_form as department_crud_form


def main():
    """Orchestrates the Streamlit application flow with improved navigation."""
    apply_custom_css()
    initialize_session_state()
    initialize_filter_state()

    with st.sidebar:
        _display_sidebar()

    st.title("Resource Management App")
    _route_to_active_tab()


def _display_sidebar():
    """Display the application sidebar with navigation and search."""
    st.title("Resource Management")

    # Search functionality
    st.markdown("### Quick Search")
    _display_search_box()

    st.markdown("---")
    st.markdown("### Navigation")

    # Dashboard section
    st.markdown("#### Dashboard")
    if st.button("🏠 Dashboard", use_container_width=True):
        st.session_state.active_tab = "Dashboard"
        st.rerun()

    # Resource Management section
    st.markdown("#### Resource Management")
    if st.button("👥 Resource Management", use_container_width=True):
        st.session_state.active_tab = "Resource Management"
        st.rerun()

    if st.button("📋 Project Management", use_container_width=True):
        st.session_state.active_tab = "Project Management"
        st.rerun()

    # Analytics section
    st.markdown("#### Resource Analytics")
    if st.button("📈 Workload Distribution", use_container_width=True):
        st.session_state.active_tab = "Workload Distribution"
        st.rerun()

    if st.button("📉 Performance Metrics", use_container_width=True):
        st.session_state.active_tab = "Performance Metrics"
        st.rerun()

    if st.button("📊 Availability Forecast", use_container_width=True):
        st.session_state.active_tab = "Availability Forecast"
        st.rerun()

    if st.button("🗓️ Resource Calendar", use_container_width=True):
        st.session_state.active_tab = "Resource Calendar"
        st.rerun()

    # Tools section
    st.markdown("#### Tools")
    if st.button("💾 Data Tools", use_container_width=True):
        st.session_state.active_tab = "Data Tools"
        st.rerun()

    if st.button("⚙️ Configuration", use_container_width=True):
        st.session_state.active_tab = "Configuration"
        st.rerun()


def _display_search_box():
    """Display search box with results."""
    from app.services.search_service import global_search

    search_query = st.text_input("Search resources and projects")
    if search_query:
        results = global_search(search_query)
        if results:
            st.markdown("**Search Results:**")
            for resource_type, resource_name in results:
                if st.button(
                    f"{resource_type}: {resource_name}",
                    key=f"search_{resource_type}_{resource_name}",
                ):
                    # Set navigation based on resource type
                    if (
                        resource_type == "Person"
                        or resource_type == "Team"
                        or resource_type == "Department"
                    ):
                        st.session_state.active_tab = "Resource Management"
                        st.session_state.selected_resource = resource_name
                        st.session_state.resource_view = resource_type + "s"
                    elif resource_type == "Project":
                        st.session_state.active_tab = "Project Management"
                        st.session_state.selected_project = resource_name
                    st.rerun()
        else:
            st.info("No matching resources found.")


def _route_to_active_tab():
    """Route to the active tab based on session state."""
    tab_mapping = {
        "Dashboard": display_home_tab,
        "Resource Management": display_manage_resources_tab,
        "Project Management": display_manage_projects_tab,
        "Workload Distribution": display_visualize_data_tab,
        "Performance Metrics": display_resource_utilization_tab,
        "Availability Forecast": display_capacity_planning_tab,
        "Resource Calendar": display_resource_calendar_tab,
        "Data Tools": display_import_export_data_tab,
        "Configuration": display_settings_tab,
    }

    active_tab = st.session_state.get("active_tab", "Dashboard")
    if active_tab in tab_mapping:
        tab_mapping[active_tab]()
    else:
        display_home_tab()


if __name__ == "__main__":
    main()
