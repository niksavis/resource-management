"""
UI component utilities for the resource management application.
"""

import streamlit as st


def display_action_bar():
    """Display breadcrumbs with improved design."""
    active_tab = st.session_state.get("active_tab", "Dashboard")
    resource_view = st.session_state.get("resource_view", "All Resources")
    breadcrumb = f"Dashboard > {active_tab}"
    if active_tab == "Resource Management" and resource_view != "All Resources":
        breadcrumb += f" > {resource_view}"
    st.markdown(f"**{breadcrumb}**")


def paginate_dataframe(df, key_prefix, items_per_page=10):
    """
    Paginate a dataframe and display pagination controls.

    Args:
        df: The dataframe to paginate
        key_prefix: A prefix for the session state keys to avoid conflicts
        items_per_page: Number of items to display per page

    Returns:
        Paginated dataframe slice
    """
    # Initialize page number in session state if not present
    if f"{key_prefix}_page" not in st.session_state:
        st.session_state[f"{key_prefix}_page"] = 0

    # Get total number of pages
    total_rows = len(df)
    total_pages = max(1, (total_rows + items_per_page - 1) // items_per_page)

    # Ensure page index is valid after filtering might have reduced total pages
    if st.session_state[f"{key_prefix}_page"] >= total_pages:
        st.session_state[f"{key_prefix}_page"] = max(0, total_pages - 1)

    # Calculate start and end indices
    start_idx = st.session_state[f"{key_prefix}_page"] * items_per_page
    end_idx = min(start_idx + items_per_page, total_rows)

    # Reset the index to start from 1 instead of 0
    df_display = df.copy()
    df_display.index = range(1, len(df) + 1)

    # Get the paginated slice
    paginated_df = df_display.iloc[start_idx:end_idx]

    # Display pagination controls with improved layout
    col1, col2 = st.columns([7, 3])

    with col1:
        # Display page info with left alignment
        current_page_display = st.session_state[f"{key_prefix}_page"] + 1
        st.markdown(
            f"**Page {current_page_display} of {total_pages}** ({total_rows} items)"
        )

    with col2:
        # Group navigation buttons together on the right
        button_cols = st.columns([1, 1])
        with button_cols[0]:
            if st.button(
                "⬅️ Previous",
                key=f"{key_prefix}_prev",
                disabled=st.session_state[f"{key_prefix}_page"] == 0,
                use_container_width=True,
            ):
                st.session_state[f"{key_prefix}_page"] -= 1
                st.rerun()

        with button_cols[1]:
            if st.button(
                "Next ➡️",
                key=f"{key_prefix}_next",
                disabled=st.session_state[f"{key_prefix}_page"] >= total_pages - 1,
                use_container_width=True,
            ):
                st.session_state[f"{key_prefix}_page"] += 1
                st.rerun()

    return paginated_df


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
