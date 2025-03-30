"""
UI components for the resource management application.

This module provides reusable UI components and display functions.
"""

import streamlit as st
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple, Union
from app.services.data_service import paginate_dataframe, _apply_all_filters
from app.utils.formatting import format_currency
from app.services.config_service import load_currency_settings, load_display_preferences


def display_filtered_resource(
    data_key: str,
    label: str,
    distinct_filters: bool = False,
    filter_by: str = "department",
) -> None:
    """
    Converts session data to a DataFrame, applies filtering, and displays the results.

    Args:
        data_key: Key in session state data to access the resource list
        label: Label for the resource type (for display purposes)
        distinct_filters: Whether to use type-specific filtering
        filter_by: Field to filter by (default: "department")
    """
    # If no data, show a helpful empty state message
    if not st.session_state.data.get(data_key, []):
        st.info(f"No {label} found. Add your first {label[:-1]} using the form below.")
        return

    data = st.session_state.data[data_key]
    if not data:
        st.warning(f"No {label} found. Please add some first.")
        return

    df = pd.DataFrame(data)

    # Define column name mappings based on resource type
    friendly_names = {}
    if label == "people":
        friendly_names = {
            "name": "Name",
            "role": "Role",
            "department": "Department",
            "team": "Team",
            "daily_cost": "Daily Cost",
            "work_days": "Work Days",
            "daily_work_hours": "Daily Work Hours",
            "skills": "Skills",
            "capacity_hours_per_week": "Capacity (Hours/Week)",
            "capacity_hours_per_month": "Capacity (Hours/Month)",
        }
    elif label == "teams":
        friendly_names = {
            "name": "Name",
            "description": "Description",
            "department": "Department",
            "members": "Members",
        }
    elif label == "departments":
        friendly_names = {
            "name": "Name",
            "teams": "Teams",
            "members": "Members",
        }

    # Create friendly sort options
    sort_options = []
    sort_mapping = {}  # Maps friendly names back to original column names

    for col in df.columns:
        if col in friendly_names:
            friendly_name = friendly_names[col]
            sort_options.append(friendly_name)
            sort_mapping[friendly_name] = col

    with st.expander(f"Search, Sort, and Filter {label.title()}", expanded=False):
        # First row: Search (full width)
        search_term = st.text_input(f"Search {label.title()}", key=f"search_{label}")

        # Second row: Three columns for filters and sorting
        col1, col2, col3 = st.columns(3)

        # Customize filters by resource type
        if label == "people":
            with col1:
                dept_filter = st.multiselect(
                    "Filter by Department",
                    options=[d["name"] for d in st.session_state.data["departments"]],
                    default=[],
                    key=f"filter_dept_{label}",
                )
            with col2:
                team_filter = st.multiselect(
                    "Filter by Team",
                    options=[t["name"] for t in st.session_state.data["teams"]],
                    default=[],
                    key=f"filter_team_{label}",
                )
            member_filter = []

        elif label == "teams":
            with col1:
                dept_filter = st.multiselect(
                    "Filter by Department",
                    options=[d["name"] for d in st.session_state.data["departments"]],
                    default=[],
                    key=f"filter_dept_{label}",
                )
            with col2:
                member_filter = st.multiselect(
                    "Filter by Member",
                    options=[p["name"] for p in st.session_state.data["people"]],
                    default=[],
                    key=f"filter_member_{label}",
                )
            team_filter = []

        elif label == "departments":
            with col1:
                team_filter = st.multiselect(
                    "Filter by Team",
                    options=[t["name"] for t in st.session_state.data["teams"]],
                    default=[],
                    key=f"filter_team_{label}",
                )
            with col2:
                member_filter = st.multiselect(
                    "Filter by Member",
                    options=[p["name"] for p in st.session_state.data["people"]],
                    default=[],
                    key=f"filter_member_{label}",
                )
            dept_filter = []

        # Sort options in third column for all resource types
        with col3:
            sort_col_friendly = st.selectbox(
                "Sort by", options=sort_options, key=f"sort_{label}"
            )

            # Convert friendly name back to original column name for sorting
            sort_col = sort_mapping.get(sort_col_friendly)

            ascending = st.checkbox("Ascending", True, key=f"asc_{label}")

        # Apply filters and sorting
        df = _apply_all_filters(
            df,
            search_term,
            team_filter,
            dept_filter,
            member_filter,
            distinct_filters,
            data_key,
        )

        # Apply sorting using the original column name
        if sort_col:
            df = df.sort_values(by=sort_col, ascending=ascending, na_position="first")

    df = paginate_dataframe(df, label)

    currency, _ = load_currency_settings()

    # Use the same friendly_names for display
    column_config = {col: friendly_names.get(col, col) for col in df.columns}

    # Add special formatting for certain columns
    if "daily_cost" in df.columns:
        column_config["daily_cost"] = st.column_config.NumberColumn(
            f"Daily Cost ({currency})", format="%.2f"
        )

    if "daily_work_hours" in df.columns:
        column_config["daily_work_hours"] = st.column_config.NumberColumn(
            "Daily Work Hours", format="%.1f hours"
        )

    if "capacity_hours_per_week" in df.columns:
        column_config["capacity_hours_per_week"] = st.column_config.NumberColumn(
            "Capacity (Hours/Week)", format="%.1f hours"
        )

    if "capacity_hours_per_month" in df.columns:
        column_config["capacity_hours_per_month"] = st.column_config.NumberColumn(
            "Capacity (Hours/Month)", format="%.1f hours"
        )

    if "skills" in df.columns:
        column_config["skills"] = st.column_config.ListColumn("Skills")

    st.dataframe(
        df,
        column_config=column_config,
        use_container_width=True,
    )


def filter_dataframe(
    df: pd.DataFrame, key: str, columns: Optional[List[str]] = None
) -> pd.DataFrame:
    """
    Enhances a DataFrame with search, sort, and pagination capabilities.

    Args:
        df: DataFrame to filter
        key: Unique key for session state
        columns: Columns to include in filtering

    Returns:
        Filtered DataFrame
    """
    import uuid

    if columns is None:
        columns = df.columns

    # Generate a unique prefix for this instance
    unique_prefix = f"{key}_{uuid.uuid4().hex[:8]}"

    for col in df.columns:
        if df[col].apply(lambda v: isinstance(v, list)).any():
            df[col] = df[col].apply(
                lambda v: ", ".join(map(str, v)) if isinstance(v, list) else str(v)
            )

    with st.expander(
        f"Search and Filter {key.replace('_', ' ').title()}", expanded=False
    ):
        search_term = st.text_input(
            f"Search {key.replace('_', ' ').title()}", key=f"search_{unique_prefix}"
        )

        col_filters = st.columns(min(4, len(columns)))
        active_filters = {}

        for i, col in enumerate(columns):
            with col_filters[i % 4]:
                if df[col].dtype == "object" or df[col].dtype == "string":
                    unique_col_key = f"filter_{unique_prefix}_{col}"  # Unique key for each column filter
                    unique_values = sorted(df[col].dropna().unique())
                    if len(unique_values) < 15:
                        selected = st.multiselect(
                            f"Filter {col}",
                            options=unique_values,
                            default=[],
                            key=unique_col_key,
                        )
                        if selected:
                            active_filters[col] = selected

        if search_term:
            mask = np.column_stack(
                [
                    df[col]
                    .fillna("")
                    .astype(str)
                    .str.contains(search_term, case=False, na=False)
                    for col in df.columns
                ]
            )
            df = df[mask.any(axis=1)]

        for col, values in active_filters.items():
            df = df[df[col].isin(values)]

        if not df.empty:
            # Create sort options with "Name" as default if it exists in columns
            default_sort = (
                "Name"
                if "Name" in df.columns or "name" in df.columns
                else df.columns[0]
            )
            sort_col = st.selectbox(
                "Sort by",
                options=list(df.columns),
                index=list(df.columns).index(default_sort)
                if default_sort in df.columns
                else 0,
                key=f"sort_{unique_prefix}",
            )

            # Always show ascending checkbox
            ascending = st.checkbox("Ascending", True, key=f"asc_{unique_prefix}")

            # Always apply sorting
            df = df.sort_values(by=sort_col, ascending=ascending, na_position="first")

        df = paginate_dataframe(df, unique_prefix)  # Use unique prefix for pagination

    return df


def confirm_action(action_name: str, key_suffix: str) -> bool:
    """
    Displays a confirmation dialog for an action.

    Args:
        action_name: Name of the action to confirm
        key_suffix: Suffix for the session state keys

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


def _display_filters(
    data_key: str, label: str, distinct_filters: bool, filter_by: str
) -> Tuple[List[str], List[str], List[str]]:
    """
    Display filter controls for resources based on type.

    Args:
        data_key: Key to access data in session state
        label: Label for the resource
        distinct_filters: Whether to show distinct filters
        filter_by: Field to filter by

    Returns:
        Tuple of selected filter values (dept_filter, team_filter, member_filter)
    """
    dept_filter = []
    team_filter = []
    member_filter = []

    if distinct_filters and data_key in ["departments", "teams"]:
        if filter_by == "teams":
            team_filter = st.multiselect(
                "Filter by Team",
                options=[t["name"] for t in st.session_state.data["teams"]],
                default=[],
                key=f"filter_team_{label}",
            )
        else:
            dept_filter = st.multiselect(
                "Filter by Department",
                options=[d["name"] for d in st.session_state.data["departments"]],
                default=[],
                key=f"filter_dept_{label}",
            )
        member_filter = st.multiselect(
            "Filter by Member",
            options=[p["name"] for p in st.session_state.data["people"]],
            default=[],
            key=f"filter_member_{label}",
        )
    else:
        dept_filter = st.multiselect(
            "Filter by Department",
            options=[d["name"] for d in st.session_state.data["departments"]],
            default=[],
            key=f"filter_dept_{label}",
        )
        team_filter = st.multiselect(
            "Filter by Team",
            options=[t["name"] for t in st.session_state.data["teams"]],
            default=[],
            key=f"filter_team_{label}",
        )

    return dept_filter, team_filter, member_filter
