import math

import numpy as np
import pandas as pd
import streamlit as st
from typing import List
from configuration import load_currency_settings


def display_filtered_resource(
    data_key: str,
    label: str,
    distinct_filters: bool = False,
    filter_by: str = "department",
) -> None:
    """
    Converts session data to a DataFrame, applies filtering, and displays the results.
    Refactored to improve readability and maintainability.
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

    with st.expander(f"Search and Filter {label.title()}", expanded=False):
        search_term = st.text_input(f"Search {label.title()}", key=f"search_{label}")

        col1, col2 = st.columns(2)
        team_filter = []
        dept_filter = []
        member_filter = []

        with col1:
            dept_filter, team_filter, member_filter = _display_filters(
                data_key, label, distinct_filters, filter_by
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

    currency, _ = load_currency_settings()

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


def _display_filters(
    data_key: str, label: str, distinct_filters: bool, filter_by: str
) -> tuple[List[str], List[str], List[str]]:
    """
    Displays filters for resources, combining primary and secondary filters.
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


def _apply_sorting(df: pd.DataFrame, label: str) -> pd.DataFrame:
    if not df.empty:
        sort_options = ["None"] + list(df.columns)
        sort_col = st.selectbox("Sort by", options=sort_options, key=f"sort_{label}")
        if sort_col != "None":
            ascending = st.checkbox("Ascending", True, key=f"asc_{label}")
            df = df.sort_values(by=sort_col, ascending=ascending, na_position="first")
    return df


def paginate_dataframe(df: pd.DataFrame, key_prefix: str) -> pd.DataFrame:
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


def confirm_action(action_name: str, key_suffix: str) -> bool:
    """Displays a confirmation dialog for an action."""
    confirm = st.checkbox(f"Confirm {action_name}", key=f"confirm_{key_suffix}")
    proceed = st.button(f"Proceed with {action_name}", key=f"proceed_{key_suffix}")
    if proceed and confirm:
        return True
    elif proceed:
        st.warning(f"Please confirm {action_name} by checking the box")
    return False


def check_circular_dependencies() -> tuple[List[str], dict, dict, dict]:
    """
    Check for circular dependencies between teams and report individuals in multiple teams,
    multiple departments, and teams in multiple departments.
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


def validate_team_integrity(team_name):
    """Validates that a team has at least 2 members."""
    team = next(
        (t for t in st.session_state.data["teams"] if t["name"] == team_name), None
    )
    if team and len(team["members"]) < 2:
        return False
    return True


def delete_resource(resource_list, resource_name, resource_type=None):
    """
    Deletes a resource from the given resource list by name.
    Optionally, handles additional cleanup based on the resource type.
    """
    # Filter out the resource to delete
    updated_list = [r for r in resource_list if r["name"] != resource_name]

    # Update the session state
    if resource_type == "team":
        # Remove the team from all people
        for person in st.session_state.data["people"]:
            if person["team"] == resource_name:
                person["team"] = None
    elif resource_type == "department":
        # Remove the department from all people and teams
        for person in st.session_state.data["people"]:
            if person["department"] == resource_name:
                person["department"] = None
        for team in st.session_state.data["teams"]:
            if team["department"] == resource_name:
                team["department"] = None

    return updated_list


def format_circular_dependency_message(
    cycle_paths: List[str],
    multi_team_members: dict,
    multi_department_members: dict,
    multi_department_teams: dict,
) -> str:
    """
    Formats a unified message for circular dependencies, members in multiple teams,
    members in multiple departments, and teams in multiple departments.
    """
    message = "\n**⚡ Impact:** Circular dependencies can cause issues with resource allocation and cost calculations.\n"
    message += "\n**💡 Solution:** Review the team memberships to eliminate overlapping assignments.\n"

    if cycle_paths:
        message += "\n**The following circular dependencies were detected:**\n"
        for path in cycle_paths:
            message += f"- {path}\n"

    if multi_team_members:
        message += "\n**Members in Multiple Teams:**\n"
        for member, teams in multi_team_members.items():
            message += f"- {member}: {', '.join(teams)}\n"

    if multi_department_members:
        message += "\n**Members in Multiple Departments:**\n"
        for member, departments in multi_department_members.items():
            message += f"- {member}: {', '.join(departments)}\n"

    if multi_department_teams:
        message += "\n**Teams in Multiple Departments:**\n"
        for team, departments in multi_department_teams.items():
            message += f"- {team}: {', '.join(departments)}\n"

    return message
