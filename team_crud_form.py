"""
Team CRUD Form Module

This module contains the Streamlit form for managing teams.
"""

import streamlit as st


def team_crud_form():
    st.subheader("Team Management")

    # Load existing teams from session state
    teams = st.session_state.data["teams"]

    # Team selection
    team_names = [team["name"] for team in teams]
    selected_team = st.selectbox("Select a team to edit", team_names)

    # Find the selected team
    team = next((team for team in teams if team["name"] == selected_team), None)

    if team:
        st.write(f"Editing team: {team['name']}")

        # Team name
        new_name = st.text_input("Team Name", value=team["name"])

        # Team members
        people = st.session_state.data["people"]
        person_names = [person["name"] for person in people]
        new_members = st.multiselect(
            "Team Members", person_names, default=team["members"]
        )

        # Update team
        update_button = st.button("Update Team")

        if update_button:
            if len(new_members) < 2:
                st.error(
                    "A team must have at least 2 members. Please add more members or delete the team instead."
                )
                st.stop()

            team["name"] = new_name
            team["members"] = new_members
            st.success(f"Team '{new_name}' updated successfully.")
            st.rerun()

        # Delete team
        delete_button = st.button("Delete Team")

        if delete_button:
            st.session_state.data["teams"] = [
                t for t in teams if t["name"] != team["name"]
            ]
            st.success(f"Team '{team['name']}' deleted successfully.")
            st.rerun()
