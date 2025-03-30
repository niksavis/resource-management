"""
UI component utilities for the resource management application.
"""

import streamlit as st
from typing import Optional, List, Dict, Any


def display_action_bar():
    """Display breadcrumbs with improved design."""
    active_tab = st.session_state.get("active_tab", "Dashboard")
    resource_view = st.session_state.get("resource_view", "All Resources")
    breadcrumb = f"Dashboard > {active_tab}"
    if active_tab == "Resource Management" and resource_view != "All Resources":
        breadcrumb += f" > {resource_view}"
    st.markdown(f"**{breadcrumb}**")


def paginate_dataframe(df, key_prefix, items_per_page=None):
    """
    Paginate a DataFrame and provide navigation.

    Args:
        df: DataFrame to paginate
        key_prefix: Prefix for session state keys
        items_per_page: Number of items per page. If None, uses settings.

    Returns:
        Paginated DataFrame
    """
    from app.services.config_service import load_display_preferences

    if items_per_page is None:
        # Get page size from settings
        display_prefs = load_display_preferences()
        items_per_page = display_prefs.get("page_size", 10)

    # Initialize page number in session state if not exists
    if f"{key_prefix}_page" not in st.session_state:
        st.session_state[f"{key_prefix}_page"] = 0

    # Calculate total pages
    n_pages = max(1, len(df) // items_per_page)

    # Only show pagination if needed
    if len(df) > items_per_page:
        # Create pagination controls
        col1, col2, col3 = st.columns([1, 3, 1])
        with col1:
            if st.button("◀️ Previous", key=f"{key_prefix}_prev"):
                st.session_state[f"{key_prefix}_page"] = max(
                    0, st.session_state[f"{key_prefix}_page"] - 1
                )

        with col2:
            st.write(f"Page {st.session_state[f'{key_prefix}_page'] + 1} of {n_pages}")

        with col3:
            if st.button("Next ▶️", key=f"{key_prefix}_next"):
                st.session_state[f"{key_prefix}_page"] = min(
                    n_pages - 1, st.session_state[f"{key_prefix}_page"] + 1
                )

    # Get current page number
    current_page = st.session_state[f"{key_prefix}_page"]

    # Calculate start and end indices
    start_idx = current_page * items_per_page
    end_idx = min(start_idx + items_per_page, len(df))

    # Return the sliced DataFrame
    return df.iloc[start_idx:end_idx].reset_index(drop=True)


def confirm_action(action_name: str, key_suffix: str) -> bool:
    """
    Displays a confirmation dialog for an action.

    Args:
        action_name: Name of the action to confirm
        key_suffix: Suffix for the unique keys

    Returns:
        True if action is confirmed, False otherwise
    """
    confirm = st.checkbox(f"Confirm {action_name}", key=f"confirm_{key_suffix}")
    proceed = st.button(f"Proceed with {action_name}", key=f"proceed_{key_suffix}")
    if proceed and confirm:
        return True
    elif proceed:
        st.warning(f"Please confirm {action_name} by checking the box")
    return False
