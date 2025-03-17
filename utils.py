import streamlit as st
import pandas as pd
import numpy as np
import math


def display_filtered_resource(
    data_key: str,
    label: str,
    distinct_filters: bool = False,
    filter_by: str = "department",
):
    """
    Converts session data to a DataFrame, applies filtering, and displays the results.
    Refactored to improve readability and maintainability.
    """
    data = st.session_state.data[data_key]
    if not data:
        st.warning(f"No {label} found. Please add some first.")
        return

    df = pd.DataFrame(data)

    # Add team and department filters
    with st.expander(f"Search and Filter {label}", expanded=False):
        search_term = st.text_input(f"Search {label}", key=f"search_{label}")

        # Create filter columns and initialize filters
        col1, col2 = st.columns(2)
        team_filter = []
        dept_filter = []
        member_filter = []

        # Display filters in columns
        with col1:
            dept_filter, team_filter = _display_primary_filters(
                data_key, label, distinct_filters, filter_by
            )

        with col2:
            member_filter, team_filter = _display_secondary_filters(
                data_key, label, distinct_filters
            )

        # Apply all filters to the dataframe
        df = _apply_all_filters(
            df,
            search_term,
            team_filter,
            dept_filter,
            member_filter,
            distinct_filters,
            data_key,
        )

        # Apply sorting and pagination
        df = _apply_sorting(df, label)
        df = _apply_pagination(df, label)

    # Display the filtered dataframe
    st.dataframe(df, use_container_width=True)


def _display_primary_filters(data_key, label, distinct_filters, filter_by):
    """Helper function to display the first column of filters."""
    dept_filter = []
    team_filter = []

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
    else:
        dept_filter = st.multiselect(
            "Filter by Department",
            options=[d["name"] for d in st.session_state.data["departments"]],
            default=[],
            key=f"filter_dept_{label}",
        )

    return dept_filter, team_filter


def _display_secondary_filters(data_key, label, distinct_filters):
    """Helper function to display the second column of filters."""
    member_filter = []
    team_filter = []

    if distinct_filters and data_key in ["departments", "teams"]:
        member_filter = st.multiselect(
            "Filter by Member",
            options=[p["name"] for p in st.session_state.data["people"]],
            default=[],
            key=f"filter_member_{label}",
        )
    else:
        team_filter = st.multiselect(
            "Filter by Team",
            options=[t["name"] for t in st.session_state.data["teams"]],
            default=[],
            key=f"filter_team_{label}",
        )

    return member_filter, team_filter


def _apply_all_filters(
    df, search_term, team_filter, dept_filter, member_filter, distinct_filters, data_key
):
    """Helper function to apply all filters to the dataframe."""
    # Apply search term across all columns
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

    # Apply team filter
    if team_filter:
        if distinct_filters and data_key == "departments":
            df = df[df["teams"].apply(lambda x: any(team in x for team in team_filter))]
        else:
            df = df[df["team"].isin(team_filter)]

    # Apply member filter
    if distinct_filters and data_key in ["departments", "teams"] and member_filter:
        df = df[
            df["members"].apply(lambda x: any(member in x for member in member_filter))
        ]

    # Apply department filter
    if dept_filter:
        df = df[df["department"].isin(dept_filter)]

    return df


def _apply_sorting(df, label):
    """Helper function to apply sorting to the dataframe."""
    if not df.empty:
        sort_options = ["None"] + list(df.columns)
        sort_col = st.selectbox("Sort by", options=sort_options, key=f"sort_{label}")
        if sort_col != "None":
            ascending = st.checkbox("Ascending", True, key=f"asc_{label}")
            df = df.sort_values(by=sort_col, ascending=ascending, na_position="first")
    return df


def _apply_pagination(df, label):
    """Helper function to apply pagination to the dataframe."""
    if len(df) > 20:
        page_size = st.slider(
            "Rows per page",
            min_value=10,
            max_value=100,
            value=20,
            step=10,
            key=f"page_size_{label}",
        )
        total_pages = math.ceil(len(df) / page_size)
        page_num = st.number_input(
            "Page",
            min_value=1,
            max_value=total_pages,
            value=1,
            step=1,
            key=f"page_num_{label}",
        )
        start_idx = (page_num - 1) * page_size
        end_idx = min(start_idx + page_size, len(df))
        st.write(f"Showing {start_idx + 1} to {end_idx} of {len(df)} entries")
        df = df.iloc[start_idx:end_idx]
    return df
