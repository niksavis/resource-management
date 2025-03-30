"""
Resource Management UI module.

This module provides the UI components for managing resources (people, teams, departments).
"""

import streamlit as st
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional

from app.utils.ui_components import display_action_bar, paginate_dataframe
from app.services.config_service import load_currency_settings, load_display_preferences
from app.utils.resource_utils import calculate_team_cost, calculate_department_cost
from person_crud_form import person_crud_form
from team_crud_form import team_crud_form
from department_crud_form import department_crud_form
from app.utils.validation import validate_team_integrity


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
        if not st.session_state.data["people"]:
            st.info("No people found. Please add people to manage them.")
        else:
            st.subheader("Manage People")
            from utils import display_filtered_resource

            display_filtered_resource("people", "people")
            person_crud_form()

    with resource_tabs[2]:
        if not st.session_state.data["teams"]:
            st.info("No teams found. Please add teams to manage them.")
        else:
            st.subheader("Manage Teams")
            from utils import display_filtered_resource

            display_filtered_resource("teams", "teams", distinct_filters=True)
            team_crud_form()

    with resource_tabs[3]:
        if not st.session_state.data["departments"]:
            st.info("No departments found. Please add departments to manage them.")
        else:
            st.subheader("Manage Departments")
            from utils import display_filtered_resource

            display_filtered_resource(
                "departments", "departments", distinct_filters=True, filter_by="teams"
            )
            department_crud_form()

    _check_and_display_dependency_warnings()


def _check_and_display_dependency_warnings():
    """Check for circular dependencies and display warnings if found."""
    from utils import check_circular_dependencies, format_circular_dependency_message

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

    with st.expander("Search, Sort, and Filter Resources", expanded=False):
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
            key=lambda x: calculate_team_cost(x["name"]),
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
        team_costs = [calculate_team_cost(team["name"]) for team in teams]
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
        dept_costs = [calculate_department_cost(dept["name"]) for dept in departments]
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
                team_cost = calculate_team_cost(team["name"])
                st.markdown(
                    f"""
                    <div class="card team-card">
                        <h3>👥 {team["name"]}</h3>
                        <p><strong>Department:</strong> {team["department"] or "None"}</p>
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
    for idx, dept in enumerate(departments):
        with cols[idx % 3]:
            dept_cost = calculate_department_cost(dept["name"])
            st.markdown(
                f"""
                <div class="card department-card">
                    <h3>🏢 {dept["name"]}</h3>
                    <p><strong>Teams:</strong> {len(dept.get("teams", []))}</p>
                    <p><strong>Members:</strong> {len([p for p in people if p["department"] == dept["name"]])}</p>
                    <p><strong>Daily Cost:</strong> {currency} {dept_cost:,.2f}</p>
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
    from visualizations import display_sunburst_organization

    # Prepare filtered data for the visualization
    filtered_data = {
        "people": [p for p in people if "Person" in type_filter],
        "teams": [t for t in teams if "Team" in type_filter],
        "departments": [d for d in departments if "Department" in type_filter],
    }

    display_sunburst_organization(filtered_data)
