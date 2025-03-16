import streamlit as st
from typing import List, Dict


def delete_resource(resource_list: List[Dict], resource_name: str) -> bool:
    """
    Removes a resource from the provided list based on the resource_name.
    """
    for idx, r in enumerate(resource_list):
        if r["name"] == resource_name:
            del resource_list[idx]
            return True
    return False


def ensure_department_exists(department_name: str) -> None:
    """
    Adds a new department if it doesn't already exist.
    """
    if not any(
        d["name"] == department_name for d in st.session_state.data["departments"]
    ):
        st.session_state.data["departments"].append(
            {"name": department_name, "teams": [], "members": []}
        )


def person_crud_form() -> None:
    """
    Handles add/edit/delete operations for People.
    """
    with st.form("add_person"):
        st.write("Add new person")
        name = st.text_input("Name")
        role = st.selectbox(
            "Role",
            [
                "Developer",
                "UX/UI Designer",
                "Domain Lead",
                "Product Owner",
                "Project Manager",
                "Key Stakeholder",
                "Head of Department",
                "Other",
            ],
        )
        if role == "Other":
            role = st.text_input("Specify role")

        # Select or create department
        if st.session_state.data["departments"]:
            dept_options = [d["name"] for d in st.session_state.data["departments"]]
            department = st.selectbox("Department", dept_options)
        else:
            department = st.text_input("Department")

        # Select team (optional)
        team_options = ["None"]
        if st.session_state.data["teams"] and department:
            for team in st.session_state.data["teams"]:
                if team["department"] == department:
                    team_options.append(team["name"])

        team = st.selectbox("Team (optional)", team_options)
        if team == "None":
            team = None

        submit = st.form_submit_button("Add Person")

        if submit and name and role and department:
            if not name.strip():
                st.error("Name cannot be empty.")
                st.stop()
            ensure_department_exists(department)

            # Add person
            st.session_state.data["people"].append(
                {
                    "name": name,
                    "role": role,
                    "department": department,
                    "team": team,
                }
            )

            # Update department members
            for dept in st.session_state.data["departments"]:
                if dept["name"] == department:
                    if name not in dept["members"]:
                        dept["members"].append(name)

            st.success(f"Added {name} as {role} to {department}")
            st.rerun()

    if st.session_state.data["people"]:
        st.subheader("Edit or Delete a Person")
        selected_name = st.selectbox(
            "Select person",
            [p["name"] for p in st.session_state.data["people"]],
        )
        if selected_name:
            if st.button(f"Delete {selected_name}"):
                success = delete_resource(
                    st.session_state.data["people"], selected_name
                )
                if success:
                    st.success(f"Deleted person: {selected_name}")
                    st.rerun()
                else:
                    st.error("Could not delete person.")
            # Edit Person functionality
            selected_person = next(
                (
                    p
                    for p in st.session_state.data["people"]
                    if p["name"] == selected_name
                ),
                None,
            )

            if selected_person:
                with st.form("edit_person_form"):
                    new_name = st.text_input("Name", value=selected_person["name"])

                    roles = [
                        "Developer",
                        "UX/UI Designer",
                        "Domain Lead",
                        "Product Owner",
                        "Project Manager",
                        "Key Stakeholder",
                        "Head of Department",
                        "Other",
                    ]
                    role_index = (
                        roles.index(selected_person["role"])
                        if selected_person["role"] in roles
                        else roles.index("Other")
                    )
                    new_role = st.selectbox("Role", roles, index=role_index)

                    if new_role == "Other":
                        new_role = st.text_input(
                            "Specify role", value=selected_person["role"]
                        )

                    # Select department
                    dept_options = [
                        d["name"] for d in st.session_state.data["departments"]
                    ]
                    dept_index = (
                        dept_options.index(selected_person["department"])
                        if selected_person["department"] in dept_options
                        else 0
                    )
                    new_department = st.selectbox(
                        "Department", dept_options, index=dept_index
                    )

                    # Select team (optional)
                    team_options = ["None"]
                    for team in st.session_state.data["teams"]:
                        if team["department"] == new_department:
                            team_options.append(team["name"])

                    current_team_index = 0
                    if (
                        selected_person["team"] is not None
                        and selected_person["team"] in team_options
                    ):
                        current_team_index = team_options.index(selected_person["team"])

                    new_team = st.selectbox(
                        "Team (optional)", team_options, index=current_team_index
                    )
                    if new_team == "None":
                        new_team = None

                    update_button = st.form_submit_button("Update Person")

                    if update_button:
                        # Update person info and related references
                        for i, person in enumerate(st.session_state.data["people"]):
                            if person["name"] == selected_name:
                                # Update department references
                                if person["department"] != new_department:
                                    # Remove from old department
                                    for dept in st.session_state.data["departments"]:
                                        if (
                                            dept["name"] == person["department"]
                                            and person["name"] in dept["members"]
                                        ):
                                            dept["members"].remove(person["name"])

                                    # Add to new department
                                    for dept in st.session_state.data["departments"]:
                                        if (
                                            dept["name"] == new_department
                                            and new_name not in dept["members"]
                                        ):
                                            dept["members"].append(new_name)

                                # Update team references
                                if person["team"] != new_team:
                                    # Remove from old team
                                    if person["team"] is not None:
                                        for team in st.session_state.data["teams"]:
                                            if (
                                                team["name"] == person["team"]
                                                and person["name"] in team["members"]
                                            ):
                                                team["members"].remove(person["name"])

                                    # Add to new team
                                    if new_team is not None:
                                        for team in st.session_state.data["teams"]:
                                            if (
                                                team["name"] == new_team
                                                and new_name not in team["members"]
                                            ):
                                                team["members"].append(new_name)

                                # Update person record
                                st.session_state.data["people"][i] = {
                                    "name": new_name,
                                    "role": new_role,
                                    "department": new_department,
                                    "team": new_team,
                                }

                                st.success(f"Updated {selected_name} to {new_name}")
                                st.rerun()


def team_crud_form() -> None:
    """
    Handles add/edit/delete operations for Teams.
    """
    with st.form("add_team"):
        st.write("Add new team")
        name = st.text_input("Team Name")

        # Select or create department
        if st.session_state.data["departments"] and name:
            dept_options = [d["name"] for d in st.session_state.data["departments"]]
            department = st.selectbox("Department", dept_options)
        else:
            department = st.text_input("Department")

        # Select team members
        member_options = []
        for person in st.session_state.data["people"]:
            if person["department"] == department:
                member_options.append(person["name"])

        members = st.multiselect("Team Members", member_options)

        submit = st.form_submit_button("Add Team")

        if submit and name and department:
            if not name.strip():
                st.error("Team name cannot be empty.")
                st.stop()
            if len(members) < 2:
                st.error("A team must have at least 2 members.")
            else:
                ensure_department_exists(department)

                # Add team
                st.session_state.data["teams"].append(
                    {"name": name, "department": department, "members": members}
                )

                # Update department teams
                for dept in st.session_state.data["departments"]:
                    if dept["name"] == department:
                        if name not in dept["teams"]:
                            dept["teams"].append(name)

                st.success(f"Added team {name} to {department}")
                st.rerun()

    if st.session_state.data["teams"]:
        st.subheader("Edit or Delete a Team")
        selected_team = st.selectbox(
            "Select team",
            [t["name"] for t in st.session_state.data["teams"]],
        )
        if selected_team:
            if st.button(f"Delete {selected_team}"):
                success = delete_resource(st.session_state.data["teams"], selected_team)
                if success:
                    st.success(f"Deleted team: {selected_team}")
                    st.rerun()
                else:
                    st.error("Could not delete team.")
            # Edit Team functionality
            selected_team_data = next(
                (
                    t
                    for t in st.session_state.data["teams"]
                    if t["name"] == selected_team
                ),
                None,
            )

            if selected_team_data:
                with st.form("edit_team_form"):
                    new_name = st.text_input(
                        "Team Name", value=selected_team_data["name"]
                    )

                    # Select department
                    dept_options = [
                        d["name"] for d in st.session_state.data["departments"]
                    ]
                    dept_index = (
                        dept_options.index(selected_team_data["department"])
                        if selected_team_data["department"] in dept_options
                        else 0
                    )
                    new_department = st.selectbox(
                        "Department", dept_options, index=dept_index
                    )

                    # Select team members
                    member_options = []
                    for person in st.session_state.data["people"]:
                        if person["department"] == new_department:
                            member_options.append(person["name"])

                    current_members = [
                        m for m in selected_team_data["members"] if m in member_options
                    ]
                    new_members = st.multiselect(
                        "Team Members", member_options, default=current_members
                    )

                    update_button = st.form_submit_button("Update Team")

                    if update_button:
                        if len(new_members) < 2:
                            st.error("A team must have at least 2 members.")
                        else:
                            # Update team info and related references
                            for i, team in enumerate(st.session_state.data["teams"]):
                                if team["name"] == selected_team:
                                    # Handle department change
                                    if team["department"] != new_department:
                                        # Remove from old department
                                        for dept in st.session_state.data[
                                            "departments"
                                        ]:
                                            if (
                                                dept["name"] == team["department"]
                                                and team["name"] in dept["teams"]
                                            ):
                                                dept["teams"].remove(team["name"])

                                        # Add to new department
                                        for dept in st.session_state.data[
                                            "departments"
                                        ]:
                                            if (
                                                dept["name"] == new_department
                                                and new_name not in dept["teams"]
                                            ):
                                                dept["teams"].append(new_name)

                                    # Update member references
                                    # Remove team assignment from members no longer in the team
                                    for person in st.session_state.data["people"]:
                                        if (
                                            person["team"] == team["name"]
                                            and person["name"] not in new_members
                                        ):
                                            person["team"] = None

                                    # Add team assignment to new members
                                    for person in st.session_state.data["people"]:
                                        if (
                                            person["name"] in new_members
                                            and person["team"] != team["name"]
                                        ):
                                            person["team"] = new_name

                                    # Update team record
                                    st.session_state.data["teams"][i] = {
                                        "name": new_name,
                                        "department": new_department,
                                        "members": new_members,
                                    }

                                    st.success(f"Updated {selected_team} to {new_name}")
                                    st.rerun()


def department_crud_form() -> None:
    """
    Handles add/edit/delete operations for Departments.
    """
    with st.form("add_department"):
        st.write("Add new department")
        name = st.text_input("Department Name")
        submit = st.form_submit_button("Add Department")

        if submit and name:
            if not name.strip():
                st.error("Department name cannot be empty.")
                st.stop()
            # Check if department already exists
            if any(d["name"] == name for d in st.session_state.data["departments"]):
                st.error(f"Department {name} already exists.")
            else:
                # Add department
                st.session_state.data["departments"].append(
                    {"name": name, "teams": [], "members": []}
                )
                st.success(f"Added department {name}")
                st.rerun()

    if st.session_state.data["departments"]:
        st.subheader("Edit or Delete a Department")
        selected_dept = st.selectbox(
            "Select department",
            [d["name"] for d in st.session_state.data["departments"]],
        )
        if selected_dept:
            if st.button(f"Delete {selected_dept}"):
                success = delete_resource(
                    st.session_state.data["departments"], selected_dept
                )
                if success:
                    st.success(f"Deleted department: {selected_dept}")
                    st.rerun()
                else:
                    st.error("Could not delete department.")
            # Edit Department functionality
            selected_dept_data = next(
                (
                    d
                    for d in st.session_state.data["departments"]
                    if d["name"] == selected_dept
                ),
                None,
            )

            if selected_dept_data:
                with st.form("edit_department_form"):
                    new_name = st.text_input(
                        "Department Name", value=selected_dept_data["name"]
                    )

                    update_button = st.form_submit_button("Update Department")

                    if update_button:
                        # Update department info and related references
                        for i, dept in enumerate(st.session_state.data["departments"]):
                            if dept["name"] == selected_dept:
                                # Update teams that belong to this department
                                for team in st.session_state.data["teams"]:
                                    if team["department"] == selected_dept:
                                        team["department"] = new_name

                                # Update people that belong to this department
                                for person in st.session_state.data["people"]:
                                    if person["department"] == selected_dept:
                                        person["department"] = new_name

                                # Update department record
                                st.session_state.data["departments"][i]["name"] = (
                                    new_name
                                )

                                st.success(f"Updated {selected_dept} to {new_name}")
                                st.rerun()
