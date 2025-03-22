"""
Utilities Module

This module contains utility functions for the resource management
application, including data pagination, confirmation dialogs, and
circular dependency checks.
"""

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

    with st.expander(f"Search and Filter {label}", expanded=False):
        search_term = st.text_input(f"Search {label}", key=f"search_{label}")

        col1, col2 = st.columns(2)
        team_filter = []
        dept_filter = []
        member_filter = []

        with col1:
            dept_filter, team_filter = _display_primary_filters(
                data_key, label, distinct_filters, filter_by
            )

        with col2:
            member_filter, team_filter = _display_secondary_filters(
                data_key, label, distinct_filters
            )

        df = _apply_all_filters(
            df,
            search_term,
            team_filter,
            dept_filter,
            member_filter,
            distinct_filters,
            data_key,
        )

        df = _apply_sorting(df, label)
        df = paginate_dataframe(df, label)

    st.dataframe(
        df,
        column_config={
            "name": "Name",
            "role": "Role",
            "department": "Department",
            "team": "Team",
            "teams": "Teams",
            "members": "Members",
            "daily_cost": st.column_config.NumberColumn(
                "Daily Cost (€)", format="€%.2f"
            ),
            "work_days": "Work Days",
            "daily_work_hours": st.column_config.NumberColumn(
                "Daily Work Hours", format="%.1f hours"
            ),
        },
        use_container_width=True,
    )


def _display_primary_filters(data_key, label, distinct_filters, filter_by):
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

    if team_filter:
        if distinct_filters and data_key == "departments":
            df = df[df["teams"].apply(lambda x: any(team in x for team in team_filter))]
        else:
            df = df[df["team"].isin(team_filter)]

    if distinct_filters and data_key in ["departments", "teams"] and member_filter:
        df = df[
            df["members"].apply(lambda x: any(member in x for member in member_filter))
        ]

    if dept_filter:
        df = df[df["department"].isin(dept_filter)]

    return df


def _apply_sorting(df, label):
    if not df.empty:
        sort_options = ["None"] + list(df.columns)
        sort_col = st.selectbox("Sort by", options=sort_options, key=f"sort_{label}")
        if sort_col != "None":
            ascending = st.checkbox("Ascending", True, key=f"asc_{label}")
            df = df.sort_values(by=sort_col, ascending=ascending, na_position="first")
    return df


def paginate_dataframe(df, key_prefix):
    """Paginate a dataframe for display."""
    if len(df) > 20:
        page_size = st.slider(
            "Rows per page", 10, 100, 20, 10, key=f"page_size_{key_prefix}"
        )
        total_pages = math.ceil(len(df) / page_size)
        page_num = st.number_input(
            "Page", 1, total_pages, 1, 1, key=f"page_num_{key_prefix}"
        )
        start_idx = (page_num - 1) * page_size
        end_idx = min(start_idx + page_size, len(df))
        st.write(f"Showing {start_idx + 1} to {end_idx} of {len(df)} entries")
        return df.iloc[start_idx:end_idx]
    return df


def confirm_action(action_name, key_suffix):
    confirm = st.checkbox(f"Confirm {action_name}", key=f"confirm_{key_suffix}")
    proceed = st.button(f"Proceed with {action_name}", key=f"proceed_{key_suffix}")
    if proceed:
        if confirm:
            return True
        else:
            st.warning(f"Please confirm {action_name} by checking the box")
    return False


def check_circular_dependencies():
    dependency_graph = {}

    for team in st.session_state.data["teams"]:
        dependency_graph[team["name"]] = set()
        for other_team in st.session_state.data["teams"]:
            if team != other_team and any(
                member in other_team["members"] for member in team["members"]
            ):
                dependency_graph[team["name"]].add(other_team["name"])

    visited = set()
    path = set()

    def dfs(node):
        if node in path:
            return True
        if node in visited:
            return False

        visited.add(node)
        path.add(node)

        for neighbor in dependency_graph.get(node, []):
            if dfs(neighbor):
                return True

        path.remove(node)
        return False

    cycles = []
    for node in dependency_graph:
        if dfs(node):
            cycles.append(node)

    return cycles
