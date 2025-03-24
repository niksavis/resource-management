"""
Team CRUD Form Module
This module contains the Streamlit form for managing teams.
"""

import streamlit as st
from validation import validate_name_field


def team_crud_form():
    st.subheader("Manage Teams")

    # Select a team to edit or delete
    teams = st.session_state.data["teams"]
    team_names = [team["name"] for team in teams]
    selected_team = st.selectbox(
        "Select a team to edit or delete", [""] + team_names, key="selected_team"
    )

    if selected_team:
        team = next((t for t in teams if t["name"] == selected_team), None)
        if team:
            with st.form("edit_team"):
                name = st.text_input("Team Name", value=team["name"])
                department = st.selectbox(
                    "Department",
                    options=[d["name"] for d in st.session_state.data["departments"]],
                    index=[
                        d["name"] for d in st.session_state.data["departments"]
                    ].index(team["department"]),
                )

                # Team members
                people = st.session_state.data["people"]
                person_names = [person["name"] for person in people]
                valid_members = [
                    member for member in team["members"] if member in person_names
                ]  # Filter valid members
                new_members = st.multiselect(
                    "Team Members", person_names, default=valid_members
                )

                update_button = st.form_submit_button("Update Team")
                if update_button:
                    if len(new_members) < 2:
                        st.error(
                            "A team must have at least 2 members. Please add more members or delete the team instead."
                        )
                        st.stop()
                    team["name"] = name
                    team["department"] = department
                    team["members"] = new_members
                    st.success(f"Team '{name}' updated successfully.")
                    st.rerun()

            # Delete team
            delete_button = st.button("Delete Team")
            if delete_button:
                st.session_state.data["teams"] = [
                    t for t in teams if t["name"] != team["name"]
                ]

                # Update people who belong to this team
                for person in st.session_state.data["people"]:
                    if person["team"] == team["name"]:
                        person["team"] = None

                st.success(f"Team '{team['name']}' deleted successfully.")
                st.rerun()

    # Add a new team
    st.subheader("Add Team")
    with st.form("add_team"):
        name = st.text_input("Team Name")
        department = st.selectbox(
            "Department",
            options=[d["name"] for d in st.session_state.data["departments"]],
        )

        # Team members
        people = st.session_state.data["people"]
        person_names = [person["name"] for person in people]
        members = st.multiselect("Team Members", person_names)

        submit = st.form_submit_button("Add Team")
        if submit:
            if not validate_name_field(name, "team"):
                st.error("Invalid team name. Please try again.")
                return

            if len(members) < 2:
                st.error("A team must have at least 2 members.")
                return

            st.session_state.data["teams"].append(
                {"name": name, "department": department, "members": members}
            )

            # Update department teams
            for dept in st.session_state.data["departments"]:
                if dept["name"] == department:
                    if name not in dept["teams"]:
                        dept["teams"].append(name)

            st.success(f"Team '{name}' added successfully.")
            st.rerun()
