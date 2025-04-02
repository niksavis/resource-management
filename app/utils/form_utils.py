"""
Form utility functions for the resource management application.

This module provides common utilities for form rendering and feedback
to ensure consistent UI/UX across all forms in the application.
"""

import streamlit as st
from typing import Optional, List, Callable


def display_form_header(title: str, form_type: str) -> None:
    """
    Display a consistent form header with appropriate icon.

    Args:
        title: The title of the form
        form_type: Type of form ('add', 'edit', or 'delete')
    """
    icons = {
        "add": "➕",
        "edit": "✏️",
        "delete": "🗑️",
        "view": "👁️",
    }
    icon = icons.get(form_type, "")
    st.markdown(f"### {icon} {title}")


def display_form_feedback(
    success: bool,
    message: str,
    details: Optional[List[str]] = None,
    show_duration: int = 3,
) -> None:
    """
    Display consistent feedback for form actions.

    Args:
        success: Whether the action was successful
        message: Main message to display
        details: Optional list of detailed messages (for errors)
        show_duration: How long to show the message (seconds)
    """
    if success:
        st.success(message, icon="✅")
    else:
        st.error(message, icon="❌")
        if details:
            for detail in details:
                st.warning(detail)


def display_confirm_checkbox(label: str, key: str) -> bool:
    """
    Display a consistent confirmation checkbox.

    Args:
        label: Label for the checkbox
        key: Unique key for the checkbox

    Returns:
        True if checked, False otherwise
    """
    return st.checkbox(f"✓ {label}", key=key)


def display_form_actions(
    primary_label: str,
    primary_key: str,
    is_delete: bool = False,
    is_disabled: bool = False,
    secondary_label: Optional[str] = None,
    secondary_key: Optional[str] = None,
    secondary_action: Optional[Callable] = None,
) -> bool:
    """
    Display consistent form action buttons.

    Args:
        primary_label: Label for the primary button
        primary_key: Key for the primary button
        is_delete: Whether this is a delete action
        is_disabled: Whether the primary button should be disabled
        secondary_label: Label for secondary button (optional)
        secondary_key: Key for secondary button
        secondary_action: Callback for secondary button

    Returns:
        True if primary button clicked, False otherwise
    """
    col1, col2 = st.columns([3, 1]) if secondary_label else [st.container(), None]

    with col1:
        button_type = "primary" if not is_delete else "danger"
        icon = "✓" if not is_delete else "🗑️"
        clicked = st.button(
            f"{icon} {primary_label}",
            key=primary_key,
            type=button_type,
            disabled=is_disabled,
            use_container_width=True,
        )

    if secondary_label and secondary_key and col2:
        with col2:
            if (
                st.button(
                    secondary_label,
                    key=secondary_key,
                    use_container_width=True,
                )
                and secondary_action
            ):
                secondary_action()

    return clicked


def display_form_separator() -> None:
    """Display a consistent separator between form sections."""
    st.divider()


def display_form_section(title: str) -> None:
    """
    Display a consistent form section header.

    Args:
        title: Title of the section
    """
    st.subheader(title)


def display_resource_icon(resource_type: str) -> str:
    """
    Get the appropriate icon for a resource type.

    Args:
        resource_type: Type of resource ('person', 'team', 'department', or 'project')

    Returns:
        Icon string
    """
    icons = {
        "person": "👤",
        "team": "👥",
        "department": "🏢",
        "project": "📋",
    }
    return icons.get(resource_type.lower(), "📄")
