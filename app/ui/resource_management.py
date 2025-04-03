"""
Resource Management UI module.

This module provides the UI components for managing resources (people, teams, departments).
"""

import streamlit as st
import pandas as pd
import numpy as np
from typing import List, Dict, Any
from app.utils.ui_components import display_action_bar, paginate_dataframe
from app.services.config_service import (
    load_currency_settings,
    load_display_preferences,
    load_daily_cost_settings,
    remove_department_color,
)
from app.utils.resource_utils import (
    calculate_team_cost,
    calculate_department_cost,
    update_resource_references,
    delete_resource,
    add_resource,
    update_resource,
)
from app.ui.forms.person_form import display_person_form as person_crud_form
from app.ui.forms.team_form import display_team_form as team_crud_form
from app.ui.forms.department_form import display_department_form as department_crud_form
from app.utils.formatting import format_circular_dependency_message
from app.services.data_service import check_circular_dependencies, parse_resources
from app.ui.visualizations import display_sunburst_organization


def display_manage_resources_tab():
    """Display the resource management tab with all resource types."""
    display_action_bar()
    st.subheader("Resource Management")

    resource_tabs = st.tabs(["All Resources", "People", "Teams", "Departments"])

    with resource_tabs[0]:
        if (
            not st.session_state.data["people"]
            and not st.session_state.data["teams"]
            and not st.session_state.data["departments"]
        ):
            st.info("No resources found. Please add people, teams, or departments.")
        else:
            display_consolidated_resources()

    with resource_tabs[1]:
        display_people_tab()

    with resource_tabs[2]:
        display_teams_tab()

    with resource_tabs[3]:
        display_departments_tab()

    _check_and_display_dependency_warnings()


def display_people_tab():
    """Display the people tab with people list and CRUD forms."""
    st.subheader("Manage People")
    if st.session_state.data["people"]:
        people_df = _create_people_dataframe()
        people_df = _filter_people_dataframe(people_df)

        display_prefs = load_display_preferences()
        page_size = display_prefs.get("page_size", 10)
        people_df = paginate_dataframe(people_df, "people", items_per_page=page_size)

        # Enable horizontal scrolling for the dataframe
        st.markdown(
            """
            <style>
            .stDataFrame {
                width: 100%;
                overflow-x: auto;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        st.dataframe(people_df, use_container_width=True)
    else:
        st.warning("No people found. Please add a person first.")

    # People CRUD forms
    with st.expander("➕ Add Person"):
        person_crud_form(on_submit=lambda person: _add_person(person), form_type="add")

    if st.session_state.data["people"]:
        with st.expander("✏️ Edit Person"):
            person_to_edit = st.selectbox(
                "Select Person to Edit",
                options=[p["name"] for p in st.session_state.data["people"]],
                key="select_person_to_edit",
            )
            selected_person = next(
                (
                    p
                    for p in st.session_state.data["people"]
                    if p["name"] == person_to_edit
                ),
                None,
            )
            if selected_person:
                person_crud_form(
                    person_data=selected_person,
                    on_submit=lambda person: _update_person(person, person_to_edit),
                    form_type="edit",
                )

        with st.expander("🗑️ Delete Person"):
            person_to_delete = st.selectbox(
                "Select Person to Delete",
                options=[p["name"] for p in st.session_state.data["people"]],
                key="select_person_to_delete",
            )
            selected_person = next(
                (
                    p
                    for p in st.session_state.data["people"]
                    if p["name"] == person_to_delete
                ),
                None,
            )
            if selected_person:
                st.write(f"You are about to delete: **{person_to_delete}**")
                if st.button(
                    "Delete Person",
                    key="delete_person_button",
                    type="primary",
                    use_container_width=True,
                ):
                    _delete_person(person_to_delete)
                    st.rerun()


def display_teams_tab():
    """Display the teams tab with teams list and CRUD forms."""
    st.subheader("Manage Teams")
    if st.session_state.data["teams"]:
        teams_df = _create_teams_dataframe()
        teams_df = _filter_teams_dataframe(teams_df)

        display_prefs = load_display_preferences()
        page_size = display_prefs.get("page_size", 10)
        teams_df = paginate_dataframe(teams_df, "teams", items_per_page=page_size)

        # Enable horizontal scrolling for the dataframe
        st.markdown(
            """
            <style>
            .stDataFrame {
                width: 100%;
                overflow-x: auto;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        st.dataframe(teams_df, use_container_width=True)
    else:
        st.warning("No teams found. Please add a team first.")

    # Team CRUD forms
    with st.expander("➕ Add Team"):
        team_crud_form(on_submit=lambda team: _add_team(team), form_type="add")

    if st.session_state.data["teams"]:
        with st.expander("✏️ Edit Team"):
            team_to_edit = st.selectbox(
                "Select Team to Edit",
                options=[t["name"] for t in st.session_state.data["teams"]],
                key="select_team_to_edit",
            )
            selected_team = next(
                (
                    t
                    for t in st.session_state.data["teams"]
                    if t["name"] == team_to_edit
                ),
                None,
            )
            if selected_team:
                team_crud_form(
                    team_data=selected_team,
                    on_submit=lambda team: _update_team(team, team_to_edit),
                    form_type="edit",
                )

        with st.expander("🗑️ Delete Team"):
            team_to_delete = st.selectbox(
                "Select Team to Delete",
                options=[t["name"] for t in st.session_state.data["teams"]],
                key="select_team_to_delete",
            )
            selected_team = next(
                (
                    t
                    for t in st.session_state.data["teams"]
                    if t["name"] == team_to_delete
                ),
                None,
            )
            if selected_team:
                st.write(f"You are about to delete: **{team_to_delete}**")
                st.write(
                    f"This team has **{len(selected_team.get('members', []))} members** who will be affected."
                )
                if st.button(
                    "Delete Team",
                    key="delete_team_button",
                    type="primary",
                    use_container_width=True,
                ):
                    _delete_team(team_to_delete)
                    st.rerun()


def display_departments_tab():
    """Display the departments tab with departments list and CRUD forms."""
    st.subheader("Manage Departments")
    if st.session_state.data["departments"]:
        departments_df = _create_departments_dataframe()
        departments_df = _filter_departments_dataframe(departments_df)

        display_prefs = load_display_preferences()
        page_size = display_prefs.get("page_size", 10)
        departments_df = paginate_dataframe(
            departments_df, "departments", items_per_page=page_size
        )

        # Enable horizontal scrolling for the dataframe
        st.markdown(
            """
            <style>
            .stDataFrame {
                width: 100%;
                overflow-x: auto;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        st.dataframe(departments_df, use_container_width=True)
    else:
        st.warning("No departments found. Please add a department first.")

    # Department CRUD forms with expanders
    with st.expander("➕ Add Department"):
        department_crud_form(
            on_submit=lambda dept: _add_department(dept), form_type="add"
        )

    if st.session_state.data["departments"]:
        with st.expander("✏️ Edit Department"):
            dept_to_edit = st.selectbox(
                "Select Department to Edit",
                options=[d["name"] for d in st.session_state.data["departments"]],
                key="select_department_to_edit",
            )
            selected_department = next(
                (
                    d
                    for d in st.session_state.data["departments"]
                    if d["name"] == dept_to_edit
                ),
                None,
            )
            if selected_department:
                department_crud_form(
                    department_data=selected_department,
                    on_submit=lambda dept: _update_department(dept, dept_to_edit),
                    form_type="edit",
                )

        with st.expander("🗑️ Delete Department"):
            dept_to_delete = st.selectbox(
                "Select Department to Delete",
                options=[d["name"] for d in st.session_state.data["departments"]],
                key="select_department_to_delete",
            )
            selected_department = next(
                (
                    d
                    for d in st.session_state.data["departments"]
                    if d["name"] == dept_to_delete
                ),
                None,
            )
            if selected_department:
                st.write(f"You are about to delete: **{dept_to_delete}**")
                st.write(
                    f"This department has **{len(selected_department.get('teams', []))} teams** "
                    + f"and **{len(selected_department.get('members', []))} direct members** who will be affected."
                )
                if st.button(
                    "Delete Department",
                    key="delete_department_button",
                    type="primary",
                    use_container_width=True,
                ):
                    _delete_department(dept_to_delete)
                    st.rerun()


def _check_and_display_dependency_warnings():
    """Check for circular dependencies and display warnings if found."""
    cycles, multi_team_members, multi_department_members, multi_department_teams = (
        check_circular_dependencies()
    )

    if (
        cycles
        or multi_team_members
        or multi_department_members
        or multi_department_teams
    ):
        circular_dependency_message = format_circular_dependency_message(
            cycles, multi_team_members, multi_department_members, multi_department_teams
        )
        with st.expander("⚠️ Circular Dependencies Detected", expanded=True):
            st.warning(circular_dependency_message)


def display_consolidated_resources():
    """Display a consolidated view of all resources using cards or visual map."""
    people = st.session_state.data["people"]
    teams = st.session_state.data["teams"]
    departments = st.session_state.data["departments"]

    st.write("### Resources Overview")

    with st.expander("🔍 Search, Sort, and Filter Resources", expanded=False):
        search_term = st.text_input("Search Resources", key="search_all_resources")

        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            type_filter = st.multiselect(
                "Filter by Type",
                options=["Person", "Team", "Department"],
                default=[],
                key="filter_type_all",
            )
        with col2:
            dept_filter = st.multiselect(
                "Filter by Department",
                options=[d["name"] for d in st.session_state.data["departments"]],
                default=[],
                key="filter_dept_all",
            )
        with col3:
            sort_option = st.selectbox(
                "Sort by",
                options=["Name", "Role", "Department", "Daily Cost"],
                key="sort_option_all",
            )
            ascending = st.checkbox("Ascending", value=True, key="sort_ascending_all")

    # Apply search filter
    if search_term:
        people = [p for p in people if search_term.lower() in str(p).lower()]
        teams = [t for t in teams if search_term.lower() in str(t).lower()]
        departments = [d for d in departments if search_term.lower() in str(d).lower()]

    # Apply department filter
    if dept_filter:
        people = [p for p in people if p["department"] in dept_filter]
        teams = [t for t in teams if t["department"] in dept_filter]
        departments = [d for d in departments if d["name"] in dept_filter]

    # Apply type filter only if it has values, otherwise keep all types
    filtered_people = people if not type_filter or "Person" in type_filter else []
    filtered_teams = teams if not type_filter or "Team" in type_filter else []
    filtered_departments = (
        departments if not type_filter or "Department" in type_filter else []
    )

    # Apply sorting
    if sort_option == "Name":
        filtered_people.sort(key=lambda x: x["name"], reverse=not ascending)
        filtered_teams.sort(key=lambda x: x["name"], reverse=not ascending)
        filtered_departments.sort(key=lambda x: x["name"], reverse=not ascending)
    elif sort_option == "Role":
        filtered_people.sort(key=lambda x: x.get("role", ""), reverse=not ascending)
    elif sort_option == "Department":
        filtered_people.sort(key=lambda x: x["department"], reverse=not ascending)
        filtered_teams.sort(key=lambda x: x["department"], reverse=not ascending)
        filtered_departments.sort(key=lambda x: x["name"], reverse=not ascending)
    elif sort_option == "Daily Cost":
        filtered_people.sort(
            key=lambda x: x.get("daily_cost", 0), reverse=not ascending
        )
        filtered_teams.sort(
            key=lambda x: calculate_team_cost(x, filtered_people),
            reverse=not ascending,
        )

    # Get default view from display preferences
    display_prefs = load_display_preferences()
    default_view = display_prefs.get("default_view", "Cards")

    view_option = st.radio(
        "View As:",
        ["Cards", "Visual Map"],
        index=0 if default_view == "Cards" else 1,
        horizontal=True,
    )

    if view_option == "Cards":
        _display_resource_cards(
            filtered_people,
            filtered_teams,
            filtered_departments,
            ["Person", "Team", "Department"],
        )
    else:
        _display_resource_visual_map(
            filtered_people,
            filtered_teams,
            filtered_departments,
            ["Person", "Team", "Department"],
        )


def _display_resource_cards(
    people: List[Dict[str, Any]],
    teams: List[Dict[str, Any]],
    departments: List[Dict[str, Any]],
    type_filter: List[str],
):
    """Display resources as visual cards organized by type with summaries."""
    currency, _ = load_currency_settings()

    if "Person" in type_filter and people:
        st.markdown("### People")
        _display_people_summary(people, currency)
        _display_person_cards(people, currency)

    if "Team" in type_filter and teams:
        st.markdown("### Teams")
        _display_teams_summary(teams, people, currency)
        _display_team_cards(teams, people, currency)

    if "Department" in type_filter and departments:
        st.markdown("### Departments")
        _display_departments_summary(departments, people, currency)
        _display_department_cards(departments, people, currency)


def _display_people_summary(people: List[Dict[str, Any]], currency: str):
    """Display a summary for people."""
    total_people = len(people)
    if total_people > 0:
        avg_daily_cost = sum(p.get("daily_cost", 0) for p in people) / total_people
        st.write(f"**Total People:** {total_people}")
        st.write(f"**Average Daily Cost:** {currency} {avg_daily_cost:,.2f}")
    else:
        st.write("**No people to display.**")


def _display_teams_summary(
    teams: List[Dict[str, Any]], people: List[Dict[str, Any]], currency: str
):
    """Display a summary for teams."""
    total_teams = len(teams)
    if total_teams > 0:
        team_costs = [calculate_team_cost(team, people) for team in teams]
        avg_team_cost = sum(team_costs) / total_teams
        st.write(f"**Total Teams:** {total_teams}")
        st.write(f"**Average Team Daily Cost:** {currency} {avg_team_cost:,.2f}")
    else:
        st.write("**No teams to display.**")


def _display_departments_summary(
    departments: List[Dict[str, Any]], people: List[Dict[str, Any]], currency: str
):
    """Display a summary for departments."""
    total_departments = len(departments)
    if total_departments > 0:
        teams = st.session_state.data["teams"]
        dept_costs = [
            calculate_department_cost(dept, teams, people) for dept in departments
        ]
        avg_department_cost = sum(dept_costs) / total_departments
        st.write(f"**Total Departments:** {total_departments}")
        st.write(
            f"**Average Department Daily Cost:** {currency} {avg_department_cost:,.2f}"
        )
    else:
        st.write("**No departments to display.**")


def _display_person_cards(people: List[Dict[str, Any]], currency: str):
    """Display person cards in a consistent grid."""
    cols = st.columns(3)
    for idx, person in enumerate(people):
        with cols[idx % 3]:
            with st.container():
                st.markdown(
                    f"""
                    <div class="card person-card">
                        <h3>👤 {person["name"]}</h3>
                        <div style="background-color: {"rgba(255,215,0,0.2)" if person["team"] else "rgba(100,100,100,0.1)"}; padding: 5px; border-radius: 4px; margin-bottom: 10px;">
                            <span style="font-weight: bold;">{"👥 " + person["team"] if person["team"] else "Individual Contributor"}</span>
                        </div>
                        <p><strong>Role:</strong> {person["role"]}</p>
                        <p><strong>Department:</strong> {person["department"]}</p>
                        <p><strong>Daily Cost:</strong> {currency} {person["daily_cost"]:,.2f}</p>
                        <p><strong>Work Days:</strong> {", ".join(person["work_days"])}</p>
                        <p><strong>Hours:</strong> {person["daily_work_hours"]} per day</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


def _display_team_cards(
    teams: List[Dict[str, Any]], people: List[Dict[str, Any]], currency: str
):
    """Display team cards in a consistent grid."""
    cols = st.columns(3)
    for idx, team in enumerate(teams):
        with cols[idx % 3]:
            with st.container():
                team_cost = calculate_team_cost(team, people)
                st.markdown(
                    f"""
                    <div class="card team-card">
                        <h3>👥 {team["name"]}</h3>
                        <div style="background-color: rgba(100,100,100,0.1); padding: 5px; border-radius: 4px; margin-bottom: 10px;">
                            <span style="font-weight: bold;">Department: {team["department"] or "None"}</span>
                        </div>
                        <p><strong>Members:</strong> {len(team["members"])}</p>
                        <p><strong>Daily Cost:</strong> {currency} {team_cost:,.2f}</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


def _display_department_cards(
    departments: List[Dict[str, Any]], people: List[Dict[str, Any]], currency: str
):
    """Display department cards in a consistent grid."""
    cols = st.columns(3)
    teams = st.session_state.data["teams"]
    for idx, dept in enumerate(departments):
        with cols[idx % 3]:
            # Calculate department cost
            cost = calculate_department_cost(dept, teams, people)

            # Count individual contributors (people in dept but not in teams)
            individual_contributors = len(
                [
                    p
                    for p in people
                    if p.get("department") == dept["name"] and not p.get("team")
                ]
            )

            # Count total people in department
            total_people = len(
                [p for p in people if p.get("department") == dept["name"]]
            )

            # Restore the card styling to match person and team cards
            st.markdown(
                f"""
                <div class="card department-card">
                    <h3>🏢 {dept["name"]}</h3>
                    <div style="background-color: rgba(100,100,100,0.1); padding: 5px; border-radius: 4px; margin-bottom: 10px;">
                        <span style="font-weight: bold;">Organization Unit</span>
                    </div>
                    <p><strong>Teams:</strong> {len(dept.get("teams", []))}</p>
                    <p><strong>Individual Contributors:</strong> {individual_contributors}</p>
                    <p><strong>Total People:</strong> {total_people}</p>
                    <p><strong>Daily Cost:</strong> {currency} {cost:,.2f}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )


def _display_resource_visual_map(
    people: List[Dict[str, Any]],
    teams: List[Dict[str, Any]],
    departments: List[Dict[str, Any]],
    type_filter: List[str],
):
    """Display resources as a network using sunburst visualization."""

    # Prepare filtered data for the visualization
    filtered_data = {
        "people": [p for p in people if "Person" in type_filter],
        "teams": [t for t in teams if "Team" in type_filter],
        "departments": [d for d in departments if "Department" in type_filter],
    }

    display_sunburst_organization(filtered_data)


def _update_person(person, old_name=None):
    # Check against maximum daily cost limit
    max_daily_cost = load_daily_cost_settings()
    if person.get("daily_cost", 0) > max_daily_cost:
        currency, _ = load_currency_settings()
        st.error(
            f"Daily cost exceeds maximum limit of {currency} {max_daily_cost:,.2f}! Please adjust the cost."
        )
        return False

    if old_name is None:
        old_name = person["name"]

    if old_name and old_name != person["name"]:
        update_resource_references(old_name, person["name"], "person")
    update_resource(st.session_state.data["people"], old_name, person)

    # Clear the people dataframe cache
    if "people_df_cache" in st.session_state:
        del st.session_state["people_df_cache"]
    # Also clear team and department caches as they might include person data
    if "teams_df_cache" in st.session_state:
        del st.session_state["teams_df_cache"]
    if "departments_df_cache" in st.session_state:
        del st.session_state["departments_df_cache"]

    # Clear form state to reset the form
    for key in list(st.session_state.keys()):
        if key.startswith("person_form_") or key.startswith("edit_person_"):
            del st.session_state[key]

    st.success(f"Person {person['name']} updated successfully!")

    # Force an immediate rerun to refresh the UI
    st.rerun()

    return True


def _add_person(person):
    # Check against maximum daily cost limit
    max_daily_cost = load_daily_cost_settings()
    if person.get("daily_cost", 0) > max_daily_cost:
        currency, _ = load_currency_settings()
        st.error(
            f"Daily cost exceeds maximum limit of {currency} {max_daily_cost:,.2f}! Please adjust the cost."
        )
        return False

    if add_resource(st.session_state.data["people"], person):
        # Clear all caches that might include person data
        if "people_df_cache" in st.session_state:
            del st.session_state["people_df_cache"]
        if "teams_df_cache" in st.session_state:
            del st.session_state["teams_df_cache"]
        if "departments_df_cache" in st.session_state:
            del st.session_state["departments_df_cache"]

        # Clear form state to reset the form
        for key in list(st.session_state.keys()):
            if key.startswith("person_form_") or key.startswith("add_person_"):
                del st.session_state[key]

        st.success(f"Person {person['name']} added successfully!")

        # Force an immediate rerun to refresh the UI
        st.rerun()

        return True
    else:
        st.error(f"Person {person['name']} already exists!")
        return False


def _delete_person(name):
    delete_resource(st.session_state.data["people"], name, "person")

    # Clear all caches that might include person data
    if "people_df_cache" in st.session_state:
        del st.session_state["people_df_cache"]
    if "teams_df_cache" in st.session_state:
        del st.session_state["teams_df_cache"]
    if "departments_df_cache" in st.session_state:
        del st.session_state["departments_df_cache"]

    # Clear form state
    for key in list(st.session_state.keys()):
        if key.startswith("person_") or key.startswith("delete_person_"):
            del st.session_state[key]

    # The rerun is already called by the button click handler


def _add_team(team):
    if add_resource(st.session_state.data["teams"], team):
        # Clear all caches that might include team data
        if "teams_df_cache" in st.session_state:
            del st.session_state["teams_df_cache"]
        if "departments_df_cache" in st.session_state:
            del st.session_state["departments_df_cache"]
        if "people_df_cache" in st.session_state:
            del st.session_state["people_df_cache"]

        st.success(f"Team {team['name']} added successfully!")
    else:
        st.error(f"Team {team['name']} already exists!")


def _update_team(team, old_name=None):
    # Find the team to update
    team_name = old_name if old_name else team["name"]
    team_index = next(
        (
            i
            for i, t in enumerate(st.session_state.data["teams"])
            if t["name"] == team_name
        ),
        None,
    )

    if team_index is None:
        st.error(f"Team '{team_name}' not found")
        return

    # Get the existing team to track changes
    existing_team = st.session_state.data["teams"][team_index]

    # Create a deep copy of the team to avoid reference issues
    team = {
        "name": team["name"],
        "department": team["department"],
        "members": team.get("members", []).copy(),
    }

    # Handle name changes and references
    if old_name and old_name != team["name"]:
        update_resource_references(old_name, team["name"], "team")

    # Handle department changes
    if team.get("department") != existing_team.get("department"):
        # Update people's department if needed
        for person in st.session_state.data["people"]:
            if person.get("team") == team_name:
                person["department"] = team["department"]

    # Update team in the data
    st.session_state.data["teams"][team_index] = team

    # Handle member changes - update people's team and department associations

    # 1. For added members, update their team and department
    added_members = [
        m for m in team.get("members", []) if m not in existing_team.get("members", [])
    ]
    for member_name in added_members:
        person = next(
            (p for p in st.session_state.data["people"] if p["name"] == member_name),
            None,
        )
        if person:
            person["team"] = team["name"]
            if team.get("department"):
                person["department"] = team["department"]

    # 2. For removed members, clear their team association
    removed_members = [
        m for m in existing_team.get("members", []) if m not in team.get("members", [])
    ]
    for member_name in removed_members:
        person = next(
            (p for p in st.session_state.data["people"] if p["name"] == member_name),
            None,
        )
        if person and person.get("team") == team_name:
            person["team"] = None

    # After updating the team, clear all relevant caches
    if "teams_df_cache" in st.session_state:
        del st.session_state["teams_df_cache"]
    if "departments_df_cache" in st.session_state:
        del st.session_state["departments_df_cache"]
    if "people_df_cache" in st.session_state:
        del st.session_state["people_df_cache"]

    st.success(f"Team '{team['name']}' updated successfully!")

    # Force a rerun to refresh the UI immediately
    st.rerun()


def _delete_team(name):
    delete_resource(st.session_state.data["teams"], name, "team")

    # Clear all caches that might include team data
    if "teams_df_cache" in st.session_state:
        del st.session_state["teams_df_cache"]
    if "departments_df_cache" in st.session_state:
        del st.session_state["departments_df_cache"]
    if "people_df_cache" in st.session_state:
        del st.session_state["people_df_cache"]


def _add_department(department):
    if add_resource(st.session_state.data["departments"], department):
        # Clear all caches that might include department data
        if "departments_df_cache" in st.session_state:
            del st.session_state["departments_df_cache"]
        if "teams_df_cache" in st.session_state:
            del st.session_state["teams_df_cache"]
        if "people_df_cache" in st.session_state:
            del st.session_state["people_df_cache"]

        st.success(f"Department {department['name']} added successfully!")
    else:
        st.error(f"Department {department['name']} already exists!")


def _update_department(department, old_name=None):
    # Find the department to update
    dept_name = old_name if old_name else department["name"]
    dept_index = next(
        (
            i
            for i, d in enumerate(st.session_state.data["departments"])
            if d["name"] == dept_name
        ),
        None,
    )

    if dept_index is None:
        st.error(f"Department '{dept_name}' not found")
        return

    # Get the existing department to track changes
    existing_dept = st.session_state.data["departments"][dept_index]

    # Create a deep copy of the department to avoid reference issues
    department = {
        "name": department["name"],
        "teams": department.get("teams", []).copy(),
        "members": department.get("members", []).copy(),
    }

    # Handle name changes and references
    if old_name and old_name != department["name"]:
        update_resource_references(old_name, department["name"], "department")

    # Update department in the data
    st.session_state.data["departments"][dept_index] = department

    # Update team associations when department changes
    for team_name in department.get("teams", []):
        team = next(
            (t for t in st.session_state.data["teams"] if t["name"] == team_name), None
        )
        if team:
            team["department"] = department["name"]

    # For removed teams, clear their department association if it still points to this department
    if existing_dept:
        removed_teams = [
            t
            for t in existing_dept.get("teams", [])
            if t not in department.get("teams", [])
        ]
        for team_name in removed_teams:
            team = next(
                (t for t in st.session_state.data["teams"] if t["name"] == team_name),
                None,
            )
            if team and team.get("department") == dept_name:
                team["department"] = None

    # After updating the department, clear all relevant caches
    if "departments_df_cache" in st.session_state:
        del st.session_state["departments_df_cache"]
    if "teams_df_cache" in st.session_state:
        del st.session_state["teams_df_cache"]
    if "people_df_cache" in st.session_state:
        del st.session_state["people_df_cache"]

    st.success(f"Department '{department['name']}' updated successfully!")

    # Force a rerun to refresh the UI immediately
    st.rerun()


def _delete_department(name):
    # Remove color from settings first, then delete the resource
    remove_department_color(name)
    delete_resource(st.session_state.data["departments"], name, "department")

    # Clear all caches that might include department data
    if "departments_df_cache" in st.session_state:
        del st.session_state["departments_df_cache"]
    if "teams_df_cache" in st.session_state:
        del st.session_state["teams_df_cache"]
    if "people_df_cache" in st.session_state:
        del st.session_state["people_df_cache"]


def _filter_people_dataframe(people_df: pd.DataFrame) -> pd.DataFrame:
    """Filter people DataFrame based on user-selected filters."""
    # Clear the cached dataframe when filters are changed
    filter_key = "people_filter_changed"

    with st.expander("🔍 Search, Sort, and Filter People", expanded=False):
        # Add filtering UI here
        search_term = st.text_input("Search People", key="search_people")

        # Apply filters (any filter change should update the UI)
        if _any_people_filter_changed():
            if "people_df_cache" in st.session_state:
                del st.session_state["people_df_cache"]
            if filter_key not in st.session_state:
                st.session_state[filter_key] = True
                st.rerun()

        # Apply search filter
        if search_term:
            mask = np.column_stack(
                [
                    people_df[col]
                    .fillna("")
                    .astype(str)
                    .str.contains(search_term, case=False, na=False)
                    for col in people_df.columns
                ]
            )
            people_df = people_df[mask.any(axis=1)]

    return people_df


def _filter_teams_dataframe(teams_df: pd.DataFrame) -> pd.DataFrame:
    """Filter teams DataFrame based on user-selected filters."""
    # Clear the cached dataframe when filters are changed
    filter_key = "teams_filter_changed"

    with st.expander("🔍 Search, Sort, and Filter Teams", expanded=False):
        # Add filtering UI here
        search_term = st.text_input("Search Teams", key="search_teams")

        # Apply filters (any filter change should update the UI)
        if _any_teams_filter_changed():
            if "teams_df_cache" in st.session_state:
                del st.session_state["teams_df_cache"]
            if filter_key not in st.session_state:
                st.session_state[filter_key] = True
                st.rerun()

        # Apply search filter
        if search_term:
            mask = np.column_stack(
                [
                    teams_df[col]
                    .fillna("")
                    .astype(str)
                    .str.contains(search_term, case=False, na=False)
                    for col in teams_df.columns
                ]
            )
            teams_df = teams_df[mask.any(axis=1)]

    return teams_df


def _filter_departments_dataframe(departments_df: pd.DataFrame) -> pd.DataFrame:
    """Filter departments DataFrame based on user-selected filters."""
    # Clear the cached dataframe when filters are changed
    filter_key = "departments_filter_changed"

    with st.expander("🔍 Search, Sort, and Filter Departments", expanded=False):
        # Add filtering UI here
        search_term = st.text_input("Search Departments", key="search_departments")

        # Apply filters (any filter change should update the UI)
        if _any_departments_filter_changed():
            if "departments_df_cache" in st.session_state:
                del st.session_state["departments_df_cache"]
            if filter_key not in st.session_state:
                st.session_state[filter_key] = True
                st.rerun()

        # Apply search filter
        if search_term:
            mask = np.column_stack(
                [
                    departments_df[col]
                    .fillna("")
                    .astype(str)
                    .str.contains(search_term, case=False, na=False)
                    for col in departments_df.columns
                ]
            )
            departments_df = departments_df[mask.any(axis=1)]

    return departments_df


# Helper functions to detect filter changes
def _any_people_filter_changed() -> bool:
    """Check if any people filter has changed since last render."""
    filter_keys = ["search_people"]

    current_values = {
        key: st.session_state.get(key) for key in filter_keys if key in st.session_state
    }

    if "prev_people_filter_values" not in st.session_state:
        st.session_state["prev_people_filter_values"] = current_values
        return False

    changed = current_values != st.session_state["prev_people_filter_values"]
    st.session_state["prev_people_filter_values"] = current_values

    return changed


def _any_teams_filter_changed() -> bool:
    """Check if any teams filter has changed since last render."""
    filter_keys = ["search_teams"]

    current_values = {
        key: st.session_state.get(key) for key in filter_keys if key in st.session_state
    }

    if "prev_teams_filter_values" not in st.session_state:
        st.session_state["prev_teams_filter_values"] = current_values
        return False

    changed = current_values != st.session_state["prev_teams_filter_values"]
    st.session_state["prev_teams_filter_values"] = current_values

    return changed


def _any_departments_filter_changed() -> bool:
    """Check if any departments filter has changed since last render."""
    filter_keys = ["search_departments"]

    current_values = {
        key: st.session_state.get(key) for key in filter_keys if key in st.session_state
    }

    if "prev_departments_filter_values" not in st.session_state:
        st.session_state["prev_departments_filter_values"] = current_values
        return False

    changed = current_values != st.session_state["prev_departments_filter_values"]
    st.session_state["prev_departments_filter_values"] = current_values

    return changed


def _create_people_dataframe() -> pd.DataFrame:
    """
    Create a DataFrame from people data.

    Returns:
        DataFrame with people information
    """
    # Use a cache key to store the dataframe
    if "people_df_cache" not in st.session_state:
        currency, _ = load_currency_settings()
        st.session_state["people_df_cache"] = pd.DataFrame(
            [
                {
                    "Name": p["name"],
                    "Role": p.get("role", ""),
                    "Team": p.get("team", ""),
                    "Department": p.get("department", ""),
                    "Daily Cost": f"{currency} {p.get('daily_cost', 0):,.2f}",
                    "Work Days": ", ".join(p.get("work_days", [])),
                    "Daily Hours": p.get("daily_work_hours", 8),
                    "Skills": ", ".join(p.get("skills", [])),
                }
                for p in st.session_state.data["people"]
            ]
        )

    return st.session_state["people_df_cache"]


def _create_teams_dataframe() -> pd.DataFrame:
    """
    Create a DataFrame from teams data.

    Returns:
        DataFrame with teams information
    """
    # Use a cache key to store the dataframe
    if "teams_df_cache" not in st.session_state:
        people = st.session_state.data["people"]
        currency, _ = load_currency_settings()
        st.session_state["teams_df_cache"] = pd.DataFrame(
            [
                {
                    "Name": t["name"],
                    "Department": t.get("department", ""),
                    "Members": len(t.get("members", [])),
                    "Member Names": parse_resources(t.get("members", []))[0],
                    "Daily Cost": f"{currency} {calculate_team_cost(t, people):,.2f}",
                }
                for t in st.session_state.data["teams"]
            ]
        )

    return st.session_state["teams_df_cache"]


def _create_departments_dataframe() -> pd.DataFrame:
    """
    Create a DataFrame from departments data.

    Returns:
        DataFrame with departments information
    """
    # Use a cache key to store the dataframe
    if "departments_df_cache" not in st.session_state:
        people = st.session_state.data["people"]
        teams = st.session_state.data["teams"]
        currency, _ = load_currency_settings()
        st.session_state["departments_df_cache"] = pd.DataFrame(
            [
                {
                    "Name": d["name"],
                    "Teams": len(d.get("teams", [])),
                    "Team Names": parse_resources(d.get("teams", []))[1],
                    "Direct Members": len(
                        [
                            p
                            for p in people
                            if p.get("department") == d["name"] and not p.get("team")
                        ]
                    ),
                    "Total Members": len(
                        [p for p in people if p.get("department") == d["name"]]
                    ),
                    "Daily Cost": f"{currency} {calculate_department_cost(d, teams, people):,.2f}",
                }
                for d in st.session_state.data["departments"]
            ]
        )

    return st.session_state["departments_df_cache"]
