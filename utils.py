"""
Utility functions for the resource management application.

This module provides common utility functions used across the application.
"""

import uuid
import numpy as np
import pandas as pd
import streamlit as st
from typing import List, Dict, Any, Optional, Tuple, Union
from configuration import load_currency_settings, load_display_preferences


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
            "capacity_hours_per_week": "Capacity (Hours/Week)",
            "capacity_hours_per_month": "Capacity (Hours/Month)",
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
                f"Daily Cost ({currency})", format="%.2f"
            ),
            "work_days": "Work Days",
            "daily_work_hours": st.column_config.NumberColumn(
                "Daily Work Hours", format="%.1f hours"
            ),
            "capacity_hours_per_week": "Capacity (Hours/Week)",
            "capacity_hours_per_month": "Capacity (Hours/Month)",
        },
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


def paginate_dataframe(
    df: pd.DataFrame, key_prefix: str, items_per_page: Optional[int] = None
) -> pd.DataFrame:
    """
    Paginate a DataFrame and provide navigation.

    Args:
        df: DataFrame to paginate
        key_prefix: Prefix for session state keys
        items_per_page: Number of items per page. If None, uses settings.

    Returns:
        Paginated DataFrame
    """
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

    for team in st.session_state.data["teams"]:
        dependency_graph[team["name"]] = set()
        team_departments[team["name"]] = team["department"]

        for member in team["members"]:
            if member in team_membership:
                if member not in multi_team_members:
                    multi_team_members[member] = [team_membership[member]]
                multi_team_members[member].append(team["name"])
            team_membership[member] = team["name"]

        for other_team in st.session_state.data["teams"]:
            if team != other_team and any(
                member in other_team["members"] for member in team["members"]
            ):
                dependency_graph[team["name"]].add(other_team["name"])

    for department in st.session_state.data["departments"]:
        for member in department["members"]:
            if member in department_membership:
                if member not in multi_department_members:
                    multi_department_members[member] = [department_membership[member]]
                multi_department_members[member].append(department["name"])
            department_membership[member] = department["name"]

        for team in department["teams"]:
            if team in team_departments:
                if team_departments[team] != department["name"]:
                    if team not in multi_department_teams:
                        multi_department_teams[team] = [team_departments[team]]
                    multi_department_teams[team].append(department["name"])

    # Check for cycles
    visited = set()
    path = set()
    cycle_paths = []

    def dfs(node, current_path=None):
        if current_path is None:
            current_path = []

        if node in path:
            # Cycle detected - capture the full path
            cycle_path = current_path + [node]
            cycle_paths.append(" → ".join(cycle_path))
            return True

        if node in visited:
            return False

        visited.add(node)
        path.add(node)
        current_path.append(node)

        for neighbor in dependency_graph.get(node, []):
            if dfs(neighbor, current_path):
                return True

        path.remove(node)
        current_path.pop()
        return False

    for node in dependency_graph:
        dfs(node, [])

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


def format_currency(
    value: Union[float, int],
    currency: str = "$",
    decimal_places: int = 2,
    symbol_position: str = "prefix",
) -> str:
    """
    Format a numeric value as currency.

    Args:
        value: The numeric value to format
        currency: Currency symbol to use
        decimal_places: Number of decimal places to display
        symbol_position: Whether to show symbol before or after value ('prefix' or 'suffix')

    Returns:
        Formatted currency string
    """
    formatted_value = f"{value:,.{decimal_places}f}"
    if symbol_position == "prefix":
        return f"{currency} {formatted_value}"
    else:
        return f"{formatted_value} {currency}"


def get_resource_type(resource_name: str) -> str:
    """
    Determine the type of a resource by name.

    Args:
        resource_name: Name of the resource

    Returns:
        Resource type ('person', 'team', 'department', or 'unknown')
    """
    # Check if it's a person
    if any(p["name"] == resource_name for p in st.session_state.data["people"]):
        return "person"

    # Check if it's a team
    if any(t["name"] == resource_name for t in st.session_state.data["teams"]):
        return "team"

    # Check if it's a department
    if any(d["name"] == resource_name for d in st.session_state.data["departments"]):
        return "department"

    return "unknown"


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


def _apply_all_filters(
    df: pd.DataFrame,
    search_term: str,
    team_filter: List[str],
    dept_filter: List[str],
    member_filter: List[str],
    distinct_filters: bool,
    data_key: str,
) -> pd.DataFrame:
    """
    Apply all filters to a DataFrame.

    Args:
        df: DataFrame to filter
        search_term: Search term to filter by
        team_filter: List of teams to filter by
        dept_filter: List of departments to filter by
        member_filter: List of members to filter by
        distinct_filters: Whether to use distinct filters
        data_key: Key in session state data

    Returns:
        Filtered DataFrame
    """
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
