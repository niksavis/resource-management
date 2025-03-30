"""
Team CRUD operations module.

This module provides functions for creating, reading, updating, and deleting teams.
"""

import streamlit as st
from typing import Dict, List, Any
from validation import validate_name_field, validate_team_integrity
from utils import confirm_action


def team_crud_form():
    """Create, update, and delete teams."""
    st.subheader("Manage Teams")

    # Add Team Form
    with st.expander("Add New Team", expanded=False):
        with st.form("add_team_form"):
            name = st.text_input("Team Name", key="add_team_name")

            # Department selection
            departments = [d["name"] for d in st.session_state.data["departments"]]
            department = st.selectbox(
                "Department", options=departments, key="add_team_department"
            )

            # Team leader selection
            people_in_department = [
                p["name"]
                for p in st.session_state.data["people"]
                if p["department"] == department and not p["team"]
            ]

            leader = st.selectbox(
                "Team Leader",
                options=["None"] + people_in_department,
                key="add_team_leader",
            )

            # Team members selection (must have at least 2 members)
            available_members = [
                p["name"]
                for p in st.session_state.data["people"]
                if p["department"] == department and not p["team"]
            ]

            if leader != "None" and leader in available_members:
                # Add leader to top of the list for clarity
                available_members.remove(leader)
                available_members = [leader] + available_members

            selected_members = st.multiselect(
                "Team Members (min. 2)",
                options=available_members,
                key="add_team_members",
            )

            # Description
            description = st.text_area(
                "Team Description (optional)", key="add_team_description"
            )

            submitted = st.form_submit_button("Add Team")

            if submitted:
                if not validate_name_field(name, "team"):
                    st.error("Invalid team name. Please try again.")
                    return

                # Validate team doesn't already exist
                if any(t["name"] == name for t in st.session_state.data["teams"]):
                    st.error(f"Team '{name}' already exists.")
                    return

                # Validate team has at least 2 members
                if len(selected_members) < 2:
                    st.error("Teams must have at least 2 members.")
                    return

                # Create team
                team_data = {
                    "name": name,
                    "department": department,
                    "members": selected_members,
                    "description": description,
                }

                # Add team to session state
                st.session_state.data["teams"].append(team_data)

                # Update department's teams list
                for dept in st.session_state.data["departments"]:
                    if dept["name"] == department:
                        if "teams" not in dept:
                            dept["teams"] = []
                        dept["teams"].append(name)
                        break

                # Update members' team association
                for person in st.session_state.data["people"]:
                    if person["name"] in selected_members:
                        person["team"] = name

                st.success(f"Team '{name}' added successfully.")
                st.rerun()

    # Edit Team Form
    with st.expander("Edit Team", expanded=False):
        if not st.session_state.data["teams"]:
            st.info("No teams available to edit.")
        else:
            team_names = [t["name"] for t in st.session_state.data["teams"]]
            selected_team = st.selectbox(
                "Select Team to Edit", options=team_names, key="edit_team_select"
            )

            team = next(
                (
                    t
                    for t in st.session_state.data["teams"]
                    if t["name"] == selected_team
                ),
                None,
            )

            if team:
                with st.form("edit_team_form"):
                    name = st.text_input("Team Name", value=team["name"])

                    # Department selection
                    departments = [
                        d["name"] for d in st.session_state.data["departments"]
                    ]
                    department = st.selectbox(
                        "Department",
                        options=departments,
                        index=departments.index(team["department"])
                        if team["department"] in departments
                        else 0,
                        key="edit_team_department",
                    )

                    # Get current team members
                    current_members = team.get("members", [])

                    # Available members are people in the department not in other teams
                    # plus current team members (who can remain)
                    available_members = [
                        p["name"]
                        for p in st.session_state.data["people"]
                        if (
                            p["department"] == department
                            and (not p["team"] or p["team"] == team["name"])
                        )
                    ]

                    selected_members = st.multiselect(
                        "Team Members (min. 2)",
                        options=available_members,
                        default=current_members,
                        key="edit_team_members",
                    )

                    # Description
                    description = st.text_area(
                        "Team Description (optional)",
                        value=team.get("description", ""),
                        key="edit_team_description",
                    )

                    update_submitted = st.form_submit_button("Update Team")

                    if update_submitted:
                        if not validate_name_field(name, "team"):
                            st.error("Invalid team name. Please try again.")
                            return

                        # Check for name conflicts
                        if name != team["name"] and any(
                            t["name"] == name for t in st.session_state.data["teams"]
                        ):
                            st.error(f"Team '{name}' already exists.")
                            return

                        # Validate team has at least 2 members
                        if len(selected_members) < 2:
                            st.error("Teams must have at least 2 members.")
                            return

                        # Get the old team name and department for reference
                        old_name = team["name"]
                        old_department = team["department"]

                        # Update team in session state
                        team["name"] = name
                        team["department"] = department
                        team["members"] = selected_members
                        team["description"] = description

                        # Update department's teams list if department changed
                        if old_department != department:
                            # Remove from old department
                            for dept in st.session_state.data["departments"]:
                                if dept["name"] == old_department and "teams" in dept:
                                    if old_name in dept["teams"]:
                                        dept["teams"].remove(old_name)

                            # Add to new department
                            for dept in st.session_state.data["departments"]:
                                if dept["name"] == department:
                                    if "teams" not in dept:
                                        dept["teams"] = []
                                    if name not in dept["teams"]:
                                        dept["teams"].append(name)

                        # If team name changed, update department's teams list
                        elif old_name != name:
                            for dept in st.session_state.data["departments"]:
                                if dept["name"] == department and "teams" in dept:
                                    if old_name in dept["teams"]:
                                        dept["teams"].remove(old_name)
                                        dept["teams"].append(name)

                        # Update people's team associations
                        # 1. Remove team association from people no longer in the team
                        for person in st.session_state.data["people"]:
                            if (
                                person["team"] == old_name
                                and person["name"] not in selected_members
                            ):
                                person["team"] = None

                        # 2. Add team association to new members
                        for person in st.session_state.data["people"]:
                            if person["name"] in selected_members:
                                person["team"] = name

                        st.success(f"Team '{name}' updated successfully.")
                        st.rerun()

    # Delete Team Form
    with st.expander("Delete Team", expanded=False):
        if not st.session_state.data["teams"]:
            st.info("No teams available to delete.")
        else:
            team_names = [t["name"] for t in st.session_state.data["teams"]]
            selected_team = st.selectbox(
                "Select Team to Delete",
                options=[""] + team_names,
                key="delete_team_select",
            )

            if selected_team:
                # Get the team to display affected members
                team = next(
                    (
                        t
                        for t in st.session_state.data["teams"]
                        if t["name"] == selected_team
                    ),
                    None,
                )

                if team:
                    # Display affected members warning
                    members = team.get("members", [])
                    if members:
                        st.warning(
                            f"⚠️ This will remove {len(members)} people from the team!"
                        )
                        st.info(f"Affected members: {', '.join(members)}")

                if confirm_action(f"deleting team {selected_team}", "delete_team"):
                    # Find the team to get its department and members
                    team_to_delete = next(
                        (
                            t
                            for t in st.session_state.data["teams"]
                            if t["name"] == selected_team
                        ),
                        None,
                    )

                    if team_to_delete:
                        # Remove team from department's teams list
                        department = team_to_delete.get("department")
                        if department:
                            for dept in st.session_state.data["departments"]:
                                if dept["name"] == department and "teams" in dept:
                                    if selected_team in dept["teams"]:
                                        dept["teams"].remove(selected_team)

                        # Remove team association from members
                        for person in st.session_state.data["people"]:
                            if person["team"] == selected_team:
                                person["team"] = None

                    # Delete the team
                    st.session_state.data["teams"] = [
                        t
                        for t in st.session_state.data["teams"]
                        if t["name"] != selected_team
                    ]

                    st.success(f"Team '{selected_team}' deleted successfully.")
                    st.rerun()
