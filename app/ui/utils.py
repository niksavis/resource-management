"""
Utility functions for UI components.

This module provides helper functions for UI modules.
"""

import streamlit as st
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple
from app.utils.ui_components import paginate_dataframe
from app.services.config_service import load_currency_settings


def check_circular_dependencies() -> Tuple[
    List[str], Dict[str, List[str]], Dict[str, List[str]], Dict[str, List[str]]
]:
    """
    Check for circular dependencies between teams and report individuals in multiple teams,
    multiple departments, and teams in multiple departments.

    Returns:
        Tuple containing:
        - List of circular dependency paths
        - Dict of people in multiple teams
        - Dict of people in multiple departments
        - Dict of teams in multiple departments
    """
    dependency_graph = {}
    multi_team_members = {}
    multi_department_members = {}
    multi_department_teams = {}

    # Build dependency graph and check for multi-team or multi-department members
    team_membership = {}
    department_membership = {}
    team_departments = {}

    # Check for people in multiple teams
    for team in st.session_state.data["teams"]:
        dependency_graph[team["name"]] = set()
        team_departments[team["name"]] = team.get("department", "Unknown")

        # Check for people being in multiple teams
        for member in team.get("members", []):
            if member not in team_membership:
                team_membership[member] = []
            team_membership[member].append(team["name"])

            if len(team_membership[member]) > 1:
                multi_team_members[member] = team_membership[member]

        # Build dependency graph for teams containing other teams
        for other_team in st.session_state.data["teams"]:
            if team["name"] != other_team["name"] and other_team["name"] in team.get(
                "members", []
            ):
                dependency_graph[team["name"]].add(other_team["name"])

    # Check for people in multiple departments
    for department in st.session_state.data["departments"]:
        # Check for people being in multiple departments
        for member in department.get("members", []):
            if member not in department_membership:
                department_membership[member] = []
            department_membership[member].append(department["name"])

            if len(department_membership[member]) > 1:
                multi_department_members[member] = department_membership[member]

        # Check for teams being in multiple departments
        for team in department.get("teams", []):
            if (
                team in team_departments
                and team_departments[team] != department["name"]
            ):
                if team not in multi_department_teams:
                    multi_department_teams[team] = []
                multi_department_teams[team].append(department["name"])
                if team_departments[team] not in multi_department_teams[team]:
                    multi_department_teams[team].append(team_departments[team])

    # Check for cycles in the dependency graph
    visited = set()
    path = set()
    cycle_paths = []

    def dfs(node, current_path=None):
        if current_path is None:
            current_path = []

        # Check if we found a cycle
        if node in path:
            # We have a cycle - create a string representation
            cycle_start_idx = current_path.index(node)
            cycle = current_path[cycle_start_idx:]
            cycle.append(node)  # Complete the cycle
            cycle_str = " → ".join(cycle)
            if cycle_str not in cycle_paths:
                cycle_paths.append(cycle_str)
            return True

        # Skip if already fully processed
        if node in visited:
            return False

        # Add to current path and mark as being processed
        visited.add(node)
        path.add(node)
        current_path.append(node)

        # Process neighbors
        for neighbor in dependency_graph.get(node, []):
            if dfs(neighbor, current_path):
                return True

        # Remove from current path after processing
        path.remove(node)
        current_path.pop()
        return False

    # Run DFS on each node to find cycles
    for node in dependency_graph:
        if node not in visited:
            dfs(node)

    return (
        cycle_paths,
        multi_team_members,
        multi_department_members,
        multi_department_teams,
    )


def format_circular_dependency_message(
    cycles: List[str],
    multi_team_members: Dict[str, List[str]],
    multi_department_members: Dict[str, List[str]],
    multi_department_teams: Dict[str, List[str]],
) -> str:
    """
    Format a warning message about circular dependencies.

    Args:
        cycles: List of circular dependency paths
        multi_team_members: Dict of people in multiple teams
        multi_department_members: Dict of people in multiple departments
        multi_department_teams: Dict of teams in multiple departments

    Returns:
        Formatted warning message
    """
    message_parts = []

    if cycles:
        message_parts.append("⚠️ **Circular Dependencies Detected**\n")
        message_parts.append("The following circular dependencies were found:\n")
        for cycle in cycles:
            message_parts.append(f"- {cycle}\n")

    if multi_team_members:
        message_parts.append("\n⚠️ **People in Multiple Teams**\n")
        for person, teams in multi_team_members.items():
            message_parts.append(f"- {person}: {', '.join(teams)}\n")

    if multi_department_members:
        message_parts.append("\n⚠️ **People in Multiple Departments**\n")
        for person, departments in multi_department_members.items():
            message_parts.append(f"- {person}: {', '.join(departments)}\n")

    if multi_department_teams:
        message_parts.append("\n⚠️ **Teams in Multiple Departments**\n")
        for team, departments in multi_department_teams.items():
            message_parts.append(f"- {team}: {', '.join(departments)}\n")

    if not message_parts:
        message_parts.append("No circular dependencies or conflicts detected.")

    return "".join(message_parts)


def display_filtered_resource(
    data_key: str,
    label: str,
    distinct_filters: bool = False,
    filter_by: str = "department",
) -> None:
    """
    Displays filtered resources in a dataframe with search and filtering options.

    Args:
        data_key: Key in session state data
        label: Label for display purposes
        distinct_filters: Whether to use resource-specific filters
        filter_by: Field to filter on (e.g., "department")
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

    # Create friendly column names for display
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
        }
    elif label == "teams":
        friendly_names = {
            "name": "Name",
            "department": "Department",
            "members": "Members",
        }
    elif label == "departments":
        friendly_names = {
            "name": "Name",
            "teams": "Teams",
            "members": "Members",
        }

    # Rename columns for display
    display_df = df.copy()
    for col, friendly in friendly_names.items():
        if col in display_df.columns:
            display_df = display_df.rename(columns={col: friendly})

    # Create search and filter expander
    with st.expander(f"🔍 Search and Filter {label.title()}", expanded=False):
        # Search box
        search_term = st.text_input(f"Search {label.title()}", key=f"search_{label}")

        # Additional filters
        col1, col2, col3 = st.columns(3)

        with col1:
            # Department filter
            if "Department" in display_df.columns:
                dept_options = ["All"] + sorted(df["department"].unique().tolist())
                dept_filter = st.selectbox(
                    "Filter by Department",
                    options=dept_options,
                    index=0,
                    key=f"dept_filter_{label}",
                )
            else:
                dept_filter = "All"

        with col2:
            # Team filter (for people)
            if label == "people" and "Team" in display_df.columns:
                team_options = (
                    ["All"]
                    + ["None"]
                    + sorted([t["name"] for t in st.session_state.data["teams"]])
                )
                team_filter = st.selectbox(
                    "Filter by Team",
                    options=team_options,
                    index=0,
                    key=f"team_filter_{label}",
                )
            else:
                team_filter = "All"

        with col3:
            # Sort options
            if friendly_names:
                sort_options = list(friendly_names.values())
                sort_col = st.selectbox(
                    "Sort by", options=[""] + sort_options, index=0, key=f"sort_{label}"
                )

                if sort_col:
                    sort_dir = st.radio(
                        "Sort Direction",
                        options=["Ascending", "Descending"],
                        index=0,
                        horizontal=True,
                        key=f"sort_dir_{label}",
                    )
            else:
                sort_col = ""
                sort_dir = "Ascending"

    # Apply search filter
    if search_term:
        # Create a mask for text search across all columns
        mask = np.column_stack(
            [
                display_df[col]
                .astype(str)
                .str.contains(search_term, case=False, na=False)
                for col in display_df.columns
            ]
        )
        display_df = display_df[mask.any(axis=1)]

    # Apply department filter
    if dept_filter != "All" and "Department" in display_df.columns:
        display_df = display_df[display_df["Department"] == dept_filter]

    # Apply team filter
    if team_filter != "All" and label == "people" and "Team" in display_df.columns:
        if team_filter == "None":
            display_df = display_df[display_df["Team"].isna()]
        else:
            display_df = display_df[display_df["Team"] == team_filter]

    # Apply sorting
    if sort_col:
        # Get original column name from friendly name
        orig_col = None
        for k, v in friendly_names.items():
            if v == sort_col:
                orig_col = k
                break

        if orig_col in df.columns:
            display_df = display_df.sort_values(
                by=sort_col, ascending=(sort_dir == "Ascending")
            )

    # Format display for list columns
    for col in display_df.columns:
        if display_df[col].apply(lambda x: isinstance(x, list)).any():
            display_df[col] = display_df[col].apply(
                lambda x: ", ".join(x) if isinstance(x, list) else str(x)
            )

    # Apply pagination
    display_df = paginate_dataframe(display_df, label)

    # Get currency for formatting
    currency, _ = load_currency_settings()

    # Display the filtered, sorted dataframe
    st.dataframe(
        display_df,
        column_config={
            "Daily Cost": st.column_config.NumberColumn(
                f"Daily Cost ({currency})", format="%.2f"
            ),
            "Daily Work Hours": st.column_config.NumberColumn(
                "Daily Work Hours", format="%.1f hours"
            ),
        },
        use_container_width=True,
    )
