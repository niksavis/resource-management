"""
Resource Forms Module

This module contains Streamlit form functions for managing people,
teams, departments, and projects. It provides CRUD operations for
each resource type and integrates validation and state management.
"""

# Third-party imports
import pandas as pd
import plotly.express as px
import streamlit as st
from typing import Dict, List

# Local module imports
from color_management import (
    add_department_color,
    delete_department_color,
    load_currency_settings,
)
from data_handlers import (
    calculate_department_cost,
    calculate_person_cost,
    calculate_project_cost,
    calculate_team_cost,
)
from utils import paginate_dataframe
from validation import (
    detect_budget_overrun,
    validate_budget,
    validate_daily_cost,
    validate_name_field,
    validate_project_dates,
    validate_project_input,  # Ensure this is imported only once
    validate_work_days,
    validate_work_hours,
)


def delete_resource(
    resource_list: List[Dict[str, any]], resource_name: str, resource_type: str = None
) -> bool:
    """
    Removes a resource from the provided list and updates related references.

    Args:
        resource_list: The list containing the resource to delete
        resource_name: The name of the resource to delete
        resource_type: The type of resource (person, team, department)

    Returns:
        bool: True if the resource was deleted, False otherwise
    """
    for idx, r in enumerate(resource_list):
        if r["name"] == resource_name:
            # Handle team deletion
            if resource_type == "team":
                team = resource_list[idx]
                # Update people who belong to this team
                for person in st.session_state.data["people"]:
                    if person["team"] == resource_name:
                        person["team"] = None

                # Remove team from department
                for dept in st.session_state.data["departments"]:
                    if resource_name in dept["teams"]:
                        dept["teams"].remove(resource_name)

            # Handle department deletion
            elif resource_type == "department":
                # Update people who belong to this department
                for person in st.session_state.data["people"]:
                    if person["department"] == resource_name:
                        person["department"] = None

                # Update teams that belong to this department
                for team in st.session_state.data["teams"]:
                    if team["department"] == resource_name:
                        team["department"] = None

            # Delete the resource
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
    """Form for managing people with improved layout."""
    # Load currency settings
    currency, currency_format = load_currency_settings()
    currency_symbol = currency

    # Create tabs for Add/Edit/Delete operations
    person_tabs = st.tabs(["Add Person", "Edit Person", "Delete Person"])

    # Add Person Tab
    with person_tabs[0]:
        with st.form("add_person"):
            st.subheader("Add New Person")

            # Use consistent two-column layout
            col1, col2 = st.columns([1, 1])

            # Personal Information Section
            with col1:
                st.markdown("#### Personal Information")
                name = st.text_input("Name")
                role = st.selectbox(
                    "Role",
                    options=[
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

            # Department and Team Section
            with col2:
                st.markdown("#### Department and Team")

                # Department selection with "None" and new department option
                dept_options = ["None"] + [
                    d["name"] for d in st.session_state.data["departments"]
                ]
                dept_selection = st.selectbox("Department", dept_options)

                if dept_selection == "None":
                    department = None
                    new_dept_name = st.text_input("Or create new department")
                    if new_dept_name.strip():
                        department = new_dept_name
                else:
                    department = dept_selection

                # Team selection with "None" and new team option
                team_options = ["None"]
                if department:
                    for team_obj in st.session_state.data["teams"]:
                        if team_obj["department"] == department:
                            team_options.append(team_obj["name"])

                team_selection = st.selectbox("Team (optional)", team_options)
                if team_selection == "None":
                    team = None
                    new_team_name = st.text_input("Or create new team")
                    if new_team_name.strip():
                        team = new_team_name
                else:
                    team = team_selection

            # Work Details Section
            st.markdown("#### Work Details")
            col3, col4 = st.columns([1, 1])

            with col3:
                daily_work_hours = st.number_input(
                    "Daily Work Hours",
                    min_value=1,
                    max_value=24,
                    value=8,
                    help="Number of hours this person works per day.",
                )

                daily_cost = st.number_input(
                    f"Daily Cost ({currency_symbol})",
                    min_value=0.0,
                    step=50.0,
                    value=0.0,
                    help="Cost per day for this person.",
                )

            with col4:
                st.write("Work Days")
                day_labels = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]
                work_days = {}

                # Organize days in two rows for better layout
                days_row1 = st.columns(5)
                days_row2 = st.columns(5)

                for idx, day in enumerate(day_labels[:5]):
                    work_days[day] = days_row1[idx].checkbox(
                        day, value=(day in ["MO", "TU", "WE", "TH", "FR"])
                    )

                for idx, day in enumerate(day_labels[5:]):
                    work_days[day] = days_row2[idx].checkbox(day, value=False)

                selected_work_days = [d for d, checked in work_days.items() if checked]

            submit = st.form_submit_button("Add Person", use_container_width=True)

            if submit:
                # Validation for new fields
                if not validate_daily_cost(daily_cost):
                    st.stop()
                if not validate_work_days(selected_work_days):
                    st.stop()
                if not validate_work_hours(daily_work_hours):
                    st.stop()
                if not validate_name_field(name, "Person"):
                    st.stop()

                # Create new department if needed
                if department and not any(
                    d["name"] == department
                    for d in st.session_state.data["departments"]
                ):
                    st.session_state.data["departments"].append(
                        {"name": department, "teams": [], "members": []}
                    )
                    add_department_color(department)

                # Create new team if needed
                if team and not any(
                    t["name"] == team for t in st.session_state.data["teams"]
                ):
                    st.session_state.data["teams"].append(
                        {"name": team, "department": department, "members": [name]}
                    )

                    # Add team to department
                    for dept in st.session_state.data["departments"]:
                        if dept["name"] == department:
                            if team not in dept["teams"]:
                                dept["teams"].append(team)

                # Add person
                st.session_state.data["people"].append(
                    {
                        "name": name,
                        "role": role,
                        "department": department,
                        "team": team,
                        "daily_cost": daily_cost,
                        "work_days": selected_work_days,
                        "daily_work_hours": daily_work_hours,
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
                # Make expander collapsed
                with st.expander("Edit Person", expanded=False):
                    with st.form("edit_person_form"):
                        col1, col2 = st.columns([1, 1])
                        with col1:
                            new_name = st.text_input(
                                "Name", value=selected_person["name"]
                            )

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

                        with col2:
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
                                current_team_index = team_options.index(
                                    selected_person["team"]
                                )

                            new_team = st.selectbox(
                                "Team (optional)",
                                team_options,
                                index=current_team_index,
                            )

                            if new_team == "None":
                                new_team = None

                        # Place Daily Work Hours to the left, Daily Cost to the right
                        row2_col1, row2_col2 = st.columns([1, 1])
                        with row2_col1:
                            new_daily_work_hours = st.number_input(
                                "Daily Work Hours",
                                min_value=1,
                                max_value=24,
                                value=selected_person["daily_work_hours"],
                            )

                        with row2_col2:
                            new_daily_cost = st.number_input(
                                f"Daily Cost ({currency_symbol})",
                                min_value=0.0,
                                step=50.0,  # Changed step to a float
                                value=float(
                                    selected_person["daily_cost"]
                                ),  # Ensure value is a float
                            )

                        st.write("Work Days")
                        col_days_edit = st.columns(7)
                        day_labels = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]
                        new_work_days = {}

                        for idx, day in enumerate(day_labels):
                            new_work_days[day] = col_days_edit[idx].checkbox(
                                day,
                                value=(day in selected_person["work_days"]),
                                key=f"edit_{day}",
                            )

                        selected_new_work_days = [
                            d for d, checked in new_work_days.items() if checked
                        ]

                        update_button = st.form_submit_button(
                            "Update Person", use_container_width=True
                        )

                        if update_button:
                            # Validation for updated fields
                            if new_daily_cost <= 0:
                                st.error("Daily cost must be greater than 0.")
                                st.stop()
                            if not selected_new_work_days:
                                st.error("At least one work day must be selected.")
                                st.stop()
                            if new_daily_work_hours < 1 or new_daily_work_hours > 24:
                                st.error("Daily work hours must be between 1 and 24.")
                                st.stop()
                            if not validate_daily_cost(new_daily_cost):
                                st.stop()

                            # Update person info and related references
                            for i, person in enumerate(st.session_state.data["people"]):
                                if person["name"] == selected_name:
                                    # Update department references
                                    if person["department"] != new_department:
                                        # Remove from old department
                                        for dept in st.session_state.data[
                                            "departments"
                                        ]:
                                            if (
                                                dept["name"] == person["department"]
                                                and person["name"] in dept["members"]
                                            ):
                                                dept["members"].remove(person["name"])

                                        # Add to new department
                                        for dept in st.session_state.data[
                                            "departments"
                                        ]:
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
                                                    and person["name"]
                                                    in team["members"]
                                                ):
                                                    team["members"].remove(
                                                        person["name"]
                                                    )

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
                                        "daily_cost": new_daily_cost,
                                        "work_days": selected_new_work_days,
                                        "daily_work_hours": new_daily_work_hours,
                                    }

                            st.success(f"Updated {selected_name} to {new_name}")
                            st.rerun()


def team_crud_form() -> None:
    """Form for managing teams with improved layout."""
    # Use tabs for the Team CRUD
    team_tabs = st.tabs(["Add Team", "Edit Team", "Delete Team"])

    # Add Team Tab
    with team_tabs[0]:
        with st.form("add_team"):
            st.subheader("Add New Team")

            # Consistent two-column layout
            col1, col2 = st.columns([1, 1])

            with col1:
                st.markdown("#### Team Information")
                name = st.text_input("Team Name")

                # Department selection with "None" and new department option
                dept_options = ["None"] + [
                    d["name"] for d in st.session_state.data["departments"]
                ]
                dept_selection = st.selectbox("Department", dept_options)

                if dept_selection == "None":
                    department = None
                    new_dept_name = st.text_input("Or create new department")
                    if new_dept_name.strip():
                        department = new_dept_name
                else:
                    department = dept_selection

            with col2:
                st.markdown("#### Team Members")
                member_options = [
                    person["name"]
                    for person in st.session_state.data["people"]
                    if person["department"] == department
                ]

                members = st.multiselect("Team Members", member_options)

                team_daily_cost = sum(
                    person["daily_cost"]
                    for person in st.session_state.data["people"]
                    if person["name"] in members
                )

                st.metric("Calculated Team Daily Cost", f"€{team_daily_cost:,.2f}")

            submit = st.form_submit_button("Add Team", use_container_width=True)

            if submit:
                if not validate_name_field(name, "Team"):
                    st.stop()

                if len(members) < 2:
                    st.error("A team must have at least 2 members.")
                else:
                    # Create new department if needed
                    if department and not any(
                        d["name"] == department
                        for d in st.session_state.data["departments"]
                    ):
                        st.session_state.data["departments"].append(
                            {"name": department, "teams": [], "members": []}
                        )
                        add_department_color(department)

                    # Add team
                    st.session_state.data["teams"].append(
                        {
                            "name": name,
                            "department": department,
                            "members": members,
                        }
                    )

                    # Update department teams
                    for dept in st.session_state.data["departments"]:
                        if dept["name"] == department:
                            if name not in dept["teams"]:
                                dept["teams"].append(name)

                    st.success(f"Added team {name} to {department}")
                    st.rerun()


def department_crud_form() -> None:
    """Form for managing departments."""
    with st.expander("Add new Department", expanded=False):
        with st.form("add_department"):
            st.write("Add new department")
            name = st.text_input("Department Name")
            submit = st.form_submit_button("Add Department", use_container_width=True)
            if submit and name:
                if not validate_name_field(name, "Department"):
                    st.stop()
                # Check if department already exists
                if any(d["name"] == name for d in st.session_state.data["departments"]):
                    st.error(f"Department {name} already exists.")
                else:
                    # Add department
                    st.session_state.data["departments"].append(
                        {"name": name, "teams": [], "members": []}
                    )
                    add_department_color(name)  # Add color for the new department
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
                    st.session_state.data["departments"], selected_dept, "department"
                )
                if success:
                    delete_department_color(
                        selected_dept
                    )  # Remove the department color
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
                with st.expander("Edit Department", expanded=False):
                    with st.form("edit_department_form"):
                        new_name = st.text_input(
                            "Department Name", value=selected_dept_data["name"]
                        )

                        update_button = st.form_submit_button(
                            "Update Department", use_container_width=True
                        )

                        if update_button:
                            # Update department info and related references
                            for i, dept in enumerate(
                                st.session_state.data["departments"]
                            ):
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

        # Display department cost information
        st.subheader("Department Cost Overview")
        people = st.session_state.data["people"]
        teams = st.session_state.data["teams"]
        # Calculate department cost
        department_cost = calculate_department_cost(selected_dept_data, people, teams)

        st.write(f"**Total Department Cost:** {department_cost:,.2f}")

        # Summary Section
        st.markdown("### Cost Summary")
        total_team_cost = sum(
            calculate_team_cost(team, people)
            for team in teams
            if team["department"] == selected_dept
        )

        total_individual_cost = sum(
            calculate_person_cost(person)
            for person in people
            if person["department"] == selected_dept
        )

        col1, col2 = st.columns(2)
        col1.metric("Total Team Cost", f"{total_team_cost:,.2f}")
        col2.metric("Total Individual Cost", f"{total_individual_cost:,.2f}")

        # Pie Chart for Cost Breakdown
        st.markdown("### Cost Breakdown")
        pie_data = {
            "Category": ["Teams", "Individuals"],
            "Cost": [total_team_cost, total_individual_cost],
        }

        pie_df = pd.DataFrame(pie_data)
        pie_chart = px.pie(
            pie_df,
            names="Category",
            values="Cost",
            title="Cost Breakdown by Category",
            color_discrete_sequence=px.colors.qualitative.Set2,
        )

        st.plotly_chart(pie_chart, use_container_width=True)

        # Bar Chart for Team Costs
        st.markdown("### Team Cost Breakdown")
        team_costs = [
            {"Team": team["name"], "Cost": calculate_team_cost(team, people)}
            for team in teams
            if team["department"] == selected_dept
        ]

        team_cost_df = pd.DataFrame(team_costs)
        if not team_cost_df.empty:
            bar_chart = px.bar(
                team_cost_df,
                x="Team",
                y="Cost",
                title="Cost Breakdown by Teams",
                color="Team",
                text="Cost",
                color_discrete_sequence=px.colors.qualitative.Set3,
            )

            st.plotly_chart(bar_chart, use_container_width=True)

        # Interactive Table for Individual Costs
        st.markdown("### Individual Cost Breakdown")
        individual_costs = [
            {"Name": person["name"], "Cost": calculate_person_cost(person)}
            for person in people
            if person["department"] == selected_dept
        ]

        individual_cost_df = pd.DataFrame(individual_costs)
        if not individual_cost_df.empty:
            individual_cost_df = individual_cost_df.sort_values(
                by="Cost", ascending=False
            )

            st.dataframe(individual_cost_df, use_container_width=True)

        # Pagination
        departments_df = pd.DataFrame(st.session_state.data["departments"])
        departments_df = paginate_dataframe(departments_df, "departments_crud")
        st.dataframe(
            departments_df,
            column_config={
                "name": "Department Name",
                "teams": "Teams",
                "members": "Members",
            },
            use_container_width=True,
        )


def add_project_form() -> None:
    """
    Form for adding a new project.
    """
    # Ensure session state variables exist
    if "new_project_people" not in st.session_state:
        st.session_state["new_project_people"] = []
    if "new_project_teams" not in st.session_state:
        st.session_state["new_project_teams"] = []

    with st.expander("Add new project", expanded=False):
        with st.form("add_project_form"):
            st.write("Add new project")
            name = st.text_input("Project Name")

            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Start Date")
            with col2:
                end_date = st.date_input("End Date")

            priority = st.number_input(
                "Priority (lower = higher priority)",
                min_value=1,
                value=1,
                step=1,  # Ensure consistent type (int)
                help="Lower numbers indicate higher priority. Priority 1 is the highest.",
            )

            allocated_budget = st.number_input(
                "Allocated Budget (€)",
                min_value=0.0,
                step=1000.0,  # Ensure consistent type (float)
                value=0.0,  # Ensure consistent type (float)
                help="Budget allocated for this project.",
            )

            # Resource assignment
            people_options = [
                p["name"] for p in st.session_state.data["people"] if p["team"] is None
            ]
            people_options = list(
                set(people_options + st.session_state["new_project_people"])
            )
            selected_people = st.multiselect(
                "Select People",
                people_options,
                default=st.session_state["new_project_people"],
            )
            st.session_state["new_project_people"] = selected_people

            team_options = [t["name"] for t in st.session_state.data["teams"]]
            team_options = list(
                set(team_options + st.session_state["new_project_teams"])
            )
            selected_teams = st.multiselect(
                "Select Teams",
                team_options,
                default=st.session_state["new_project_teams"],
            )
            st.session_state["new_project_teams"] = selected_teams

            submit = st.form_submit_button(
                "Add Project", use_container_width=True
            )  # Add missing submit button

            if submit:
                # Validation for budget
                if not validate_budget(allocated_budget):
                    st.stop()
                project_data = {
                    "name": name,
                    "start_date": start_date,
                    "end_date": end_date,
                    "priority": priority,
                    "allocated_budget": allocated_budget,
                    "assigned_resources": st.session_state["new_project_people"]
                    + st.session_state["new_project_teams"],
                }
                is_valid, errors = validate_project_input(project_data)
                if not is_valid:
                    for error in errors:
                        st.error(error)
                    st.stop()
                if not validate_project_dates(start_date, end_date, name):
                    st.stop()
                if start_date > end_date:
                    st.error("End date must be after start date.")
                else:
                    # Add project
                    combined_resources = (
                        st.session_state["new_project_people"]
                        + st.session_state["new_project_teams"]
                    )
                    st.session_state.data["projects"].append(
                        {
                            "name": name,
                            "start_date": start_date.strftime("%Y-%m-%d"),
                            "end_date": end_date.strftime("%Y-%m-%d"),
                            "priority": priority,
                            "allocated_budget": allocated_budget,
                            "assigned_resources": combined_resources,
                        }
                    )
                    st.session_state["new_project_people"].clear()
                    st.session_state["new_project_teams"].clear()
                    st.success(f"Added project {name}")
                    st.rerun()


def edit_project_form() -> None:
    """
    Form for editing an existing project.
    """
    # Ensure session state variables exist
    if "edit_project_people" not in st.session_state:
        st.session_state["edit_project_people"] = []
    if "edit_project_teams" not in st.session_state:
        st.session_state["edit_project_teams"] = []
    if "last_edited_project" not in st.session_state:
        st.session_state["last_edited_project"] = None
    if "edit_form_initialized" not in st.session_state:
        st.session_state["edit_form_initialized"] = False

    if not st.session_state.data["projects"]:
        return

    st.subheader("Edit Project")
    project_to_edit = st.selectbox(
        "Select project to edit",
        [p["name"] for p in st.session_state.data["projects"]],
    )

    selected_project = next(
        (p for p in st.session_state.data["projects"] if p["name"] == project_to_edit),
        None,
    )

    if not selected_project:
        return

    # Reset initialization if a different project is chosen
    if st.session_state["last_edited_project"] != project_to_edit:
        st.session_state["edit_form_initialized"] = False
        st.session_state["last_edited_project"] = project_to_edit

    with st.form("edit_project_form"):
        # Initialize form state
        if not st.session_state["edit_form_initialized"]:
            _initialize_edit_project_form(selected_project)

        new_name = st.text_input("Project Name", value=selected_project["name"])

        # Properly handle date conversion
        start_date = pd.to_datetime(selected_project["start_date"]).date()
        end_date = pd.to_datetime(selected_project["end_date"]).date()

        col1, col2 = st.columns(2)
        with col1:
            new_start_date = st.date_input("Start Date", value=start_date)
        with col2:
            new_end_date = st.date_input("End Date", value=end_date)

        new_priority = st.number_input(
            "Priority (lower = higher priority)",
            min_value=1,
            value=selected_project["priority"],
            step=1,  # Ensure consistent type (int)
        )

        new_allocated_budget = st.number_input(
            "Allocated Budget (€)",
            min_value=0.0,
            step=1000.0,  # Ensure consistent type (float)
            value=float(selected_project.get("allocated_budget", 0.0)),  # Ensure float
        )

        # Resource assignment
        all_people = [
            p["name"] for p in st.session_state.data["people"] if p["team"] is None
        ]
        all_people = list(set(all_people + st.session_state["edit_project_people"]))
        selected_people = st.multiselect(
            "Select People",
            all_people,
            default=st.session_state["edit_project_people"],
        )
        st.session_state["edit_project_people"] = selected_people

        all_teams = [t["name"] for t in st.session_state.data["teams"]]
        all_teams = list(set(all_teams + st.session_state["edit_project_teams"]))
        selected_teams = st.multiselect(
            "Select Teams",
            all_teams,
            default=st.session_state["edit_project_teams"],
        )
        st.session_state["edit_project_teams"] = selected_teams

        # Calculate project cost
        project_cost = calculate_project_cost(
            selected_project,
            st.session_state.data["people"],
            st.session_state.data["teams"],
        )

        # Budget vs. Cost Comparison
        st.markdown("### Budget vs. Cost Comparison")
        col1, col2 = st.columns(2)
        col1.metric(
            "Allocated Budget (€)", f"{new_allocated_budget:,.2f}"
        )  # Format with commas
        col2.metric("Calculated Cost (€)", f"{project_cost:,.2f}")  # Format with commas

        if project_cost > new_allocated_budget:
            st.warning("Warning: Project cost exceeds the allocated budget!")

        # Cost Breakdown by Resource Type
        st.markdown("### Cost Breakdown by Resource Type")
        resource_costs = {
            "People": sum(
                calculate_person_cost(p)
                for p in st.session_state.data["people"]
                if p["name"] in selected_people
            ),
            "Teams": sum(
                calculate_team_cost(t, st.session_state.data["people"])
                for t in st.session_state.data["teams"]
                if t["name"] in selected_teams
            ),
        }
        resource_cost_df = pd.DataFrame(
            {
                "Resource Type": resource_costs.keys(),
                "Cost (€)": [
                    f"{cost:,.2f}" for cost in resource_costs.values()
                ],  # Format with commas
            }
        )
        st.bar_chart(resource_cost_df.set_index("Resource Type"))

        submit = st.form_submit_button(
            "Update Project", use_container_width=True
        )  # Add missing submit button

        if submit:
            # Validation for budget
            if not validate_budget(new_allocated_budget):
                st.stop()
            # Detect budget overrun
            detect_budget_overrun(project_cost, new_allocated_budget)
            project_data = {
                "name": new_name,
                "start_date": new_start_date,
                "end_date": new_end_date,
                "priority": new_priority,
                "allocated_budget": new_allocated_budget,
                "assigned_resources": st.session_state["edit_project_people"]
                + st.session_state["edit_project_teams"],
            }
            is_valid, errors = validate_project_input(project_data)
            if not is_valid:
                for error in errors:
                    st.error(error)
                st.stop()
            if not validate_project_dates(new_start_date, new_end_date, new_name):
                st.stop()
            if new_start_date > new_end_date:
                st.error("End date must be after start date.")
            else:
                combined_resources = (
                    st.session_state["edit_project_people"]
                    + st.session_state["edit_project_teams"]
                )
                for i, project in enumerate(st.session_state.data["projects"]):
                    if project["name"] == project_to_edit:
                        st.session_state.data["projects"][i] = {
                            "name": new_name,
                            "start_date": new_start_date.strftime("%Y-%m-%d"),
                            "end_date": new_end_date.strftime("%Y-%m-%d"),
                            "priority": new_priority,
                            "allocated_budget": new_allocated_budget,
                            "assigned_resources": combined_resources,
                        }
                st.success(f"Updated project {project_to_edit} to {new_name}")
                st.rerun()


def _initialize_edit_project_form(selected_project: Dict[str, any]) -> None:
    """Helper function to initialize the edit project form state."""
    st.session_state["edit_project_people"] = [
        r
        for r in selected_project["assigned_resources"]
        if r in [p["name"] for p in st.session_state.data["people"]]
    ]
    st.session_state["edit_project_teams"] = [
        r
        for r in selected_project["assigned_resources"]
        if r in [t["name"] for t in st.session_state.data["teams"]]
    ]
    st.session_state["edit_form_initialized"] = True
