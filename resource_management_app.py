import json
import os

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from configuration import (
    display_color_settings,
    load_currency_settings,
    regenerate_department_colors,
    save_currency_settings,
)
from data_handlers import (
    calculate_project_cost,
    calculate_resource_utilization,
    create_gantt_data,
    load_json,
    save_json,
    sort_projects_by_priority_and_date,
    filter_gantt_data,
)
from person_crud_form import person_crud_form
from team_crud_form import team_crud_form
from department_crud_form import department_crud_form
from project_crud_form import add_project_form, edit_project_form
from utils import (
    delete_resource,
    _apply_sorting,
    check_circular_dependencies,
    confirm_action,
    display_filtered_resource,
    paginate_dataframe,
    format_circular_dependency_message,
)
from visualizations import (
    display_capacity_planning_dashboard,
    display_gantt_chart,
    display_utilization_dashboard,
    _display_resource_conflicts,
    display_resource_calendar,
)

# Set up basic page configuration
st.set_page_config(page_title="Resource Management App", layout="wide")


# Load demo data from JSON file
def load_demo_data():
    with open("resource_data.json", "r") as file:
        return json.load(file)


# Initialize session state for data persistence
if "data" not in st.session_state:
    st.session_state.data = load_demo_data()


def display_action_bar():
    """Display breadcrumbs with improved design."""
    active_tab = st.session_state.get("active_tab", "Dashboard")
    resource_view = st.session_state.get("resource_view", "All Resources")
    breadcrumb = f"Dashboard > {active_tab}"
    if active_tab == "Resource Management" and resource_view != "All Resources":
        breadcrumb += f" > {resource_view}"
    st.markdown(f"**{breadcrumb}**")


def global_search(query):
    """Search resources and projects globally."""
    results = []
    for person in st.session_state.data["people"]:
        if query.lower() in person["name"].lower():
            results.append(("Person", person["name"]))
    for team in st.session_state.data["teams"]:
        if query.lower() in team["name"].lower():
            results.append(("Team", team["name"]))
    for project in st.session_state.data["projects"]:
        if query.lower() in project["name"].lower():
            results.append(("Project", project["name"]))
    return results


def display_home_tab():
    display_action_bar()

    st.subheader("Resource Management Dashboard")

    # Resource Summary Cards
    st.markdown("### Resource Summary")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("People", len(st.session_state.data["people"]))
    with col2:
        st.metric("Teams", len(st.session_state.data["teams"]))
    with col3:
        st.metric("Departments", len(st.session_state.data["departments"]))
    with col4:
        st.metric("Projects", len(st.session_state.data["projects"]))

    # Project Timeline Overview
    st.markdown("### Project Timeline")
    if st.session_state.data["projects"]:
        currency, _ = load_currency_settings()
        projects_df = pd.DataFrame(
            [
                {
                    "Project": p["name"],
                    "Start": pd.to_datetime(p["start_date"]),
                    "Finish": pd.to_datetime(p["end_date"]),
                    "Priority": p["priority"],
                    "Resources": len(p["assigned_resources"]),
                    "Budget": f"{currency} {p.get('allocated_budget', 0):,.2f}",
                }
                for p in st.session_state.data["projects"]
            ]
        )

        # Sort projects by priority and end date
        projects_df = projects_df.sort_values(
            by=["Priority", "Finish"], ascending=[False, False]
        )

        today = pd.Timestamp.now()
        fig = px.timeline(
            projects_df,
            x_start="Start",
            x_end="Finish",
            y="Project",
            color="Priority",
            hover_data=["Resources", "Budget"],
            color_continuous_scale="Viridis_r",
            title="Project Timeline",
        )
        fig.add_vline(x=today, line_width=2, line_dash="dash", line_color="red")
        fig.update_layout(
            xaxis_title="Timeline",
            yaxis_title="Projects",
            legend_title="Priority",
            height=600,
        )
        st.plotly_chart(fig, use_container_width=True)

    # Resource Allocation Summary
    st.markdown("### Resource Allocation")
    summary_tabs = st.tabs(
        ["Department Allocation", "Resource Utilization", "Budget Overview"]
    )

    with summary_tabs[0]:
        if st.session_state.data["people"]:
            dept_counts = {}
            for person in st.session_state.data["people"]:
                dept = person["department"]
                dept_counts[dept] = dept_counts.get(dept, 0) + 1

            dept_df = pd.DataFrame(
                {
                    "Department": list(dept_counts.keys()),
                    "People": list(dept_counts.values()),
                }
            )

            fig = px.pie(
                dept_df,
                values="People",
                names="Department",
                title="People by Department",
                hole=0.4,
            )
            st.plotly_chart(fig, use_container_width=True)

    with summary_tabs[1]:
        if st.session_state.data["projects"]:
            gantt_data = create_gantt_data(
                st.session_state.data["projects"], st.session_state.data
            )
            utilization_df = calculate_resource_utilization(gantt_data)

            if not utilization_df.empty:
                type_util = (
                    utilization_df.groupby("Type")["Utilization %"].mean().reset_index()
                )
                fig = px.bar(
                    type_util,
                    x="Type",
                    y="Utilization %",
                    color="Type",
                    title="Average Utilization by Resource Type",
                )
                st.plotly_chart(fig, use_container_width=True)

    with summary_tabs[2]:
        if st.session_state.data["projects"]:
            budget_data = []
            for project in st.session_state.data["projects"]:
                if "allocated_budget" in project:
                    actual_cost = calculate_project_cost(
                        project,
                        st.session_state.data["people"],
                        st.session_state.data["teams"],
                    )
                    budget_data.append(
                        {
                            "Project": project["name"],
                            "Allocated Budget": f"{currency} {project['allocated_budget']:,.2f}",
                            "Actual Cost": f"{currency} {actual_cost:,.2f}",
                            "Variance": f"{currency} {project['allocated_budget'] - actual_cost:,.2f}",
                        }
                    )

            if budget_data:
                budget_df = pd.DataFrame(budget_data)
                fig = px.bar(
                    budget_df,
                    x="Project",
                    y=["Allocated Budget", "Actual Cost"],
                    barmode="group",
                    title="Budget vs. Actual Cost by Project",
                )
                st.plotly_chart(fig, use_container_width=True)


def display_manage_resources_tab():
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
            display_filtered_resource("people", "people")
            person_crud_form()

    with resource_tabs[2]:
        if not st.session_state.data["teams"]:
            st.info("No teams found. Please add teams to manage them.")
        else:
            st.subheader("Manage Teams")
            display_filtered_resource("teams", "teams", distinct_filters=True)
            team_crud_form()

    with resource_tabs[3]:
        if not st.session_state.data["departments"]:
            st.info("No departments found. Please add departments to manage them.")
        else:
            st.subheader("Manage Departments")
            display_filtered_resource(
                "departments", "departments", distinct_filters=True, filter_by="teams"
            )
            department_crud_form()

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
    """Display a consolidated view of all resources using cards."""
    people = st.session_state.data["people"]
    teams = st.session_state.data["teams"]
    departments = st.session_state.data["departments"]

    with st.expander("Search, Sort, and Filter Resources", expanded=False):
        search_term = st.text_input("Search Resources", key="search_all_resources")

        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            type_filter = st.multiselect(
                "Filter by Type",
                options=["Person", "Team", "Department"],
                default=["Person", "Team", "Department"],
                key="filter_type_all",
            )
        with col2:
            dept_filter = st.multiselect(
                "Filter by Department",
                options=[d["name"] for d in departments],
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

    if search_term:
        people = [p for p in people if search_term.lower() in str(p).lower()]
        teams = [t for t in teams if search_term.lower() in str(t).lower()]
        departments = [d for d in departments if search_term.lower() in str(d).lower()]

    if dept_filter:
        people = [p for p in people if p["department"] in dept_filter]
        teams = [t for t in teams if t["department"] in dept_filter]
        departments = [d for d in departments if d["name"] in dept_filter]

    if sort_option == "Name":
        people.sort(key=lambda x: x["name"], reverse=not ascending)
        teams.sort(key=lambda x: x["name"], reverse=not ascending)
        departments.sort(key=lambda x: x["name"], reverse=not ascending)
    elif sort_option == "Role":
        people.sort(key=lambda x: x.get("role", ""), reverse=not ascending)
    elif sort_option == "Department":
        people.sort(key=lambda x: x["department"], reverse=not ascending)
        teams.sort(key=lambda x: x["department"], reverse=not ascending)
        departments.sort(key=lambda x: x["name"], reverse=not ascending)
    elif sort_option == "Daily Cost":
        people.sort(key=lambda x: x.get("daily_cost", 0), reverse=not ascending)
        teams.sort(
            key=lambda x: sum(
                p["daily_cost"]
                for p in st.session_state.data["people"]
                if p["name"] in x.get("members", [])
            ),
            reverse=not ascending,
        )

    st.write("### Resources Overview")

    view_option = st.radio("View As:", ["Cards", "Visual Map"], horizontal=True)

    if view_option == "Cards":
        _display_resource_cards(people, teams, departments, type_filter)
    else:
        _display_resource_visual_map(people, teams, departments, type_filter)


def _display_resource_cards(people, teams, departments, type_filter):
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


def _display_people_summary(people, currency):
    """Display a summary for people."""
    total_people = len(people)
    avg_daily_cost = sum(p["daily_cost"] for p in people) / total_people
    st.write(f"**Total People:** {total_people}")
    st.write(f"**Average Daily Cost:** {currency} {avg_daily_cost:,.2f}")


def _display_teams_summary(teams, people, currency):
    """Display a summary for teams."""
    total_teams = len(teams)
    avg_team_cost = (
        sum(
            sum(p["daily_cost"] for p in people if p["name"] in t["members"])
            for t in teams
        )
        / total_teams
    )
    st.write(f"**Total Teams:** {total_teams}")
    st.write(f"**Average Team Daily Cost:** {currency} {avg_team_cost:,.2f}")


def _display_departments_summary(departments, people, currency):
    """Display a summary for departments."""
    total_departments = len(departments)
    avg_department_cost = (
        sum(
            sum(p["daily_cost"] for p in people if p["department"] == d["name"])
            for d in departments
        )
        / total_departments
    )
    st.write(f"**Total Departments:** {total_departments}")
    st.write(
        f"**Average Department Daily Cost:** {currency} {avg_department_cost:,.2f}"
    )


def _display_person_cards(people, currency):
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


def _display_team_cards(teams, people, currency):
    """Display team cards in a consistent grid."""
    cols = st.columns(3)
    for idx, team in enumerate(teams):
        with cols[idx % 3]:
            with st.container():
                team_cost = sum(
                    person["daily_cost"]
                    for person in people
                    if person["name"] in team["members"]
                )
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


def _display_department_cards(departments, people, currency):
    """Display department cards in a consistent grid."""
    cols = st.columns(3)
    for idx, dept in enumerate(departments):
        with cols[idx % 3]:
            dept_cost = sum(
                person["daily_cost"]
                for person in people
                if person["department"] == dept["name"]
            )
            st.markdown(
                f"""
                <div class="card department-card">
                    <h3>🏢 {dept["name"]}</h3>
                    <p><strong>Teams:</strong> {len(dept.get("teams", []))}</p>
                    <p><strong>Members:</strong> {len(dept.get("members", []))}</p>
                    <p><strong>Daily Cost:</strong> {currency} {dept_cost:,.2f}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )


def _display_resource_visual_map(people, teams, departments, type_filter):
    """Display resources as an organizational chart or network graph."""
    import networkx as nx
    import plotly.graph_objects as go

    st.write("### Organizational Structure")

    nodes = []
    edges = []

    if "Department" in type_filter:
        for dept in departments:
            nodes.append(
                {
                    "id": f"dept_{dept['name']}",
                    "label": dept["name"],
                    "group": "department",
                }
            )

    if "Team" in type_filter:
        for team in teams:
            nodes.append(
                {"id": f"team_{team['name']}", "label": team["name"], "group": "team"}
            )
            edges.append(
                {"from": f"dept_{team['department']}", "to": f"team_{team['name']}"}
            )

    if "Person" in type_filter:
        for person in people:
            nodes.append(
                {
                    "id": f"person_{person['name']}",
                    "label": person["name"],
                    "group": "person",
                }
            )
            if person["team"]:
                edges.append(
                    {"from": f"team_{person['team']}", "to": f"person_{person['name']}"}
                )
            else:
                edges.append(
                    {
                        "from": f"dept_{person['department']}",
                        "to": f"person_{person['name']}",
                    }
                )

    G = nx.Graph()

    for node in nodes:
        G.add_node(node["id"], label=node["label"], group=node["group"])

    for edge in edges:
        G.add_edge(edge["from"], edge["to"])

    pos = nx.spring_layout(G)

    node_x = []
    node_y = []
    node_text = []
    node_color = []

    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        node_text.append(G.nodes[node]["label"])

        if G.nodes[node]["group"] == "department":
            node_color.append("blue")
        elif G.nodes[node]["group"] == "team":
            node_color.append("green")
        else:
            node_color.append("red")

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        text=node_text,
        hoverinfo="text",
        marker=dict(color=node_color, size=15, line=dict(width=2)),
    )

    edge_x = []
    edge_y = []

    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        line=dict(width=1, color="#888"),
        hoverinfo="none",
        mode="lines",
    )

    fig = go.Figure(
        data=[edge_trace, node_trace],
        layout=go.Layout(
            showlegend=False,
            hovermode="closest",
            margin=dict(b=20, l=5, r=5, t=40),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        ),
    )

    st.plotly_chart(fig, use_container_width=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("🔵 Department")
    with col2:
        st.markdown("🟢 Team")
    with col3:
        st.markdown("🔴 Person")


def display_manage_projects_tab():
    display_action_bar()

    st.subheader("Project Management")

    if not st.session_state.data["projects"]:
        st.warning("No projects found. Please add a project first.")
        add_project_form()
        return

    projects_df = _create_projects_dataframe()

    # Remove Priority Count and Priority Label logic
    projects_df = _filter_projects_dataframe(projects_df)

    st.dataframe(projects_df, use_container_width=True)

    add_project_form()
    edit_project_form()

    _handle_project_deletion()


def _create_projects_dataframe():
    """Helper function to create a DataFrame from project data."""
    from data_handlers import parse_resources

    return pd.DataFrame(
        [
            {
                "Name": p["name"],
                "Start Date": pd.to_datetime(p["start_date"]).strftime("%Y-%m-%d"),
                "End Date": pd.to_datetime(p["end_date"]).strftime("%Y-%m-%d"),
                "Priority": p["priority"],  # Directly use Priority
                "Duration (days)": (
                    pd.to_datetime(p["end_date"]) - pd.to_datetime(p["start_date"])
                ).days
                + 1,
                "Assigned People": parse_resources(p["assigned_resources"])[0],
                "Assigned Teams": parse_resources(p["assigned_resources"])[1],
                "Assigned Departments": parse_resources(p["assigned_resources"])[2],
            }
            for p in st.session_state.data["projects"]
        ]
    )


def _filter_projects_dataframe(projects_df):
    with st.expander("Search and Filter Projects", expanded=False):
        search_term = _handle_search_input()
        date_filter = _handle_date_filter(projects_df)
        resource_filters = _handle_resource_filters()

        projects_df = _apply_search_filter(projects_df, search_term)
        projects_df = _apply_date_filter(projects_df, date_filter)
        projects_df = _apply_resource_filters(projects_df, resource_filters)

        projects_df = _apply_sorting(projects_df, "projects")
        projects_df = paginate_dataframe(projects_df, "projects")

    return projects_df


def _handle_search_input():
    """Handle search input for project filtering."""
    return st.text_input("Search Projects", key="search_projects")


def _handle_date_filter(projects_df):
    """Handle date range filter for project filtering."""
    col1, col2 = st.columns(2)
    with col1:
        date_range = st.date_input(
            "Filter by Date Range",
            value=(
                pd.to_datetime(projects_df["Start Date"]).min().date(),
                pd.to_datetime(projects_df["End Date"]).max().date(),
            ),
            min_value=pd.to_datetime(projects_df["Start Date"]).min().date(),
            max_value=pd.to_datetime(projects_df["End Date"]).max().date(),
        )
    return date_range


def _handle_resource_filters():
    """Handle resource filters for project filtering."""
    col3, col4 = st.columns(2)
    with col3:
        people_filter = st.multiselect(
            "Filter by Assigned People",
            options=[p["name"] for p in st.session_state.data["people"]],
            default=[],
        )
    with col4:
        teams_filter = st.multiselect(
            "Filter by Assigned Teams",
            options=[t["name"] for t in st.session_state.data["teams"]],
            default=[],
        )
    departments_filter = st.multiselect(
        "Filter by Assigned Departments",
        options=[d["name"] for d in st.session_state.data["departments"]],
        default=[],
    )
    return people_filter, teams_filter, departments_filter


def _apply_search_filter(projects_df, search_term):
    """Apply search filter to the projects dataframe."""
    if search_term:
        mask = np.column_stack(
            [
                projects_df[col]
                .fillna("")
                .astype(str)
                .str.contains(search_term, case=False, na=False)
                for col in projects_df.columns
            ]
        )
        projects_df = projects_df[mask.any(axis=1)]
    return projects_df


def _apply_date_filter(projects_df, date_range):
    """Apply date range filter to the projects dataframe."""
    if len(date_range) == 2:
        start_date, end_date = (
            pd.to_datetime(date_range[0]),
            pd.to_datetime(date_range[1]),
        )  # Ensure consistent types
        projects_df = projects_df[
            (pd.to_datetime(projects_df["Start Date"]) >= start_date)
            & (pd.to_datetime(projects_df["End Date"]) <= end_date)
        ]
    return projects_df


def _apply_resource_filters(projects_df, resource_filters):
    """Apply resource filters to the projects dataframe."""
    people_filter, teams_filter, departments_filter = resource_filters

    if people_filter:
        projects_df = projects_df[
            projects_df["Assigned People"].apply(
                lambda x: any(person in x for person in people_filter)
            )
        ]

    if teams_filter:
        projects_df = projects_df[
            projects_df["Assigned Teams"].apply(
                lambda x: any(team in x for team in teams_filter)
            )
        ]

    if departments_filter:
        projects_df = projects_df[
            projects_df["Assigned Departments"].apply(
                lambda x: any(dept in x for dept in departments_filter)
            )
        ]

    return projects_df


def _handle_project_deletion():
    """Helper function to handle project deletion."""
    if not st.session_state.data["projects"]:
        return

    st.subheader("Delete Project")
    delete_project = st.selectbox(
        "Select project to delete",
        [p["name"] for p in st.session_state.data["projects"]],
        key="delete_project",
    )

    if confirm_action(f"deleting project {delete_project}", "delete_project"):
        st.session_state.data["projects"] = [
            p for p in st.session_state.data["projects"] if p["name"] != delete_project
        ]

        st.success(f"Deleted project {delete_project}")
        st.rerun()


def display_visualize_data_tab():
    display_action_bar()

    st.subheader("Workload Distribution")

    if not st.session_state.data["projects"]:
        st.warning("No projects found. Please add projects first.")
        return

    if not (
        st.session_state.data["people"]
        or st.session_state.data["teams"]
        or st.session_state.data["departments"]
    ):
        st.warning(
            "No resources found. Please add people, teams, or departments first."
        )
        return

    filters = _get_visualization_filters()

    # Sort projects by priority and end date
    sorted_projects = sort_projects_by_priority_and_date(
        st.session_state.data["projects"]
    )
    gantt_data = create_gantt_data(sorted_projects, st.session_state.data)

    gantt_data = _apply_visualization_filters(gantt_data, filters)

    _display_gantt_chart_with_filters(gantt_data)

    _display_resource_conflicts(gantt_data)

    _display_resource_drill_down(gantt_data)


def _get_visualization_filters():
    """Get filters for the visualization tab."""
    st.subheader("Filter Options")

    col1, col2, col3 = st.columns(3)

    with col1:
        dept_filter = st.multiselect(
            "Filter by Department",
            options=[d["name"] for d in st.session_state.data["departments"]],
            default=[],
        )

    with col2:
        resource_type_filter = st.multiselect(
            "Filter by Resource Type",
            options=["Person", "Team", "Department"],
            default=[],
        )

    with col3:
        min_date = min(
            [pd.to_datetime(p["start_date"]) for p in st.session_state.data["projects"]]
        )
        max_date = max(
            [pd.to_datetime(p["end_date"]) for p in st.session_state.data["projects"]]
        )
        date_range = st.date_input(
            "Date Range",
            value=(min_date.date(), max_date.date()),
            min_value=min_date.date(),
            max_value=max_date.date(),
        )

    project_filter = st.multiselect(
        "Filter by Project",
        options=[p["name"] for p in st.session_state.data["projects"]],
        default=[],
    )

    return {
        "dept_filter": dept_filter,
        "resource_type_filter": resource_type_filter,
        "date_range": date_range,
        "project_filter": project_filter,
    }


def _apply_visualization_filters(gantt_data, filters):
    """Apply filters to the Gantt data."""
    if filters["dept_filter"]:
        gantt_data = gantt_data[gantt_data["Department"].isin(filters["dept_filter"])]

    if filters["resource_type_filter"]:
        gantt_data = gantt_data[
            gantt_data["Type"].isin(filters["resource_type_filter"])
        ]

    if filters["project_filter"]:
        gantt_data = gantt_data[gantt_data["Project"].isin(filters["project_filter"])]

    if len(filters["date_range"]) == 2:
        start_date, end_date = filters["date_range"]
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)
        gantt_data = gantt_data[
            (gantt_data["Start"] <= end_date) & (gantt_data["Finish"] >= start_date)
        ]

    return gantt_data


def _display_gantt_chart_with_filters(gantt_data):
    """Display the Gantt chart with applied filters."""
    # Get filter values from the correct session state keys
    filtered_types = st.session_state.get("filter_type_all", [])
    filtered_departments = st.session_state.get("filter_dept_all", [])

    # Apply filters
    filtered_data = gantt_data.copy()
    if filtered_types:
        filtered_data = filtered_data[filtered_data["Type"].isin(filtered_types)]
    if filtered_departments:
        filtered_data = filtered_data[
            filtered_data["Department"].isin(filtered_departments)
        ]

    # Get list of projects to show
    filtered_projects = filtered_data["Project"].unique()

    # Use a modified version of display_gantt_chart that respects filtering
    _display_filtered_gantt_chart(gantt_data, filtered_projects)


def _display_filtered_gantt_chart(gantt_data, projects_to_include):
    """Display Gantt chart with only specified projects."""
    # Create a copy of projects for safe modification
    original_projects = st.session_state.data["projects"].copy()
    filtered_projects_data = [
        p for p in original_projects if p["name"] in projects_to_include
    ]

    # Use a context manager pattern to safely modify session state
    class SessionStateContext:
        def __enter__(self):
            st.session_state.data["_temp_original_projects"] = original_projects
            st.session_state.data["projects"] = filtered_projects_data

        def __exit__(self, exc_type, exc_val, exc_tb):
            st.session_state.data["projects"] = st.session_state.data.pop(
                "_temp_original_projects"
            )

    # Apply temporary state change safely
    with SessionStateContext():
        display_gantt_chart(gantt_data)


def _display_resource_drill_down(gantt_data):
    """Display drill-down view for resources."""
    st.subheader("Resource Drill-Down")

    if not gantt_data.empty:
        drill_down_options = ["None"] + list(gantt_data["Resource"].unique())
        resource_to_drill = st.selectbox(
            "Select resource for details", options=drill_down_options
        )

        if resource_to_drill != "None":
            resource_data = gantt_data[gantt_data["Resource"] == resource_to_drill]

            col1, col2 = st.columns([1, 2])

            with col1:
                st.markdown(f"**Resource:** {resource_to_drill}")
                st.markdown(f"**Type:** {resource_data['Type'].iloc[0]}")
                st.markdown(f"**Department:** {resource_data['Department'].iloc[0]}")

                resource_util = calculate_resource_utilization(resource_data)
                if not resource_util.empty:
                    st.markdown(
                        f"**Utilization:** {resource_util['Utilization %'].iloc[0]:.1f}%"
                    )
                    st.markdown(
                        f"**Overallocation:** {resource_util['Overallocation %'].iloc[0]:.1f}%"
                    )
                    st.markdown(f"**Projects Assigned:** {len(resource_data)}")

            with col2:
                fig = px.timeline(
                    resource_data,
                    x_start="Start",
                    x_end="Finish",
                    y="Project",
                    color="Project",
                    height=200,
                )
                fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
                st.plotly_chart(fig, use_container_width=True)

            st.markdown("**Project Assignments:**")
            projects_data = resource_data.copy()
            projects_data["Duration (days)"] = (
                projects_data["Finish"] - projects_data["Start"]
            ).dt.days + 1
            projects_data["Start"] = projects_data["Start"].dt.strftime("%Y-%m-%d")
            projects_data["Finish"] = projects_data["Finish"].dt.strftime("%Y-%m-%d")

            st.dataframe(
                projects_data[
                    [
                        "Project",
                        "Start",
                        "Finish",
                        "Priority",
                        "Duration (days)",
                    ]
                ],
                use_container_width=True,
            )


def display_resource_utilization_tab():
    display_action_bar()

    st.subheader("Performance Metrics")

    if not st.session_state.data["projects"]:
        st.warning("No projects found. Please add projects first.")
        return
    elif not (
        st.session_state.data["people"]
        or st.session_state.data["teams"]
        or st.session_state.data["departments"]
    ):
        st.warning(
            "No resources found. Please add people, teams, or departments first."
        )
        return

    # Get min/max dates from projects for the filter constraints
    min_date = min(
        [pd.to_datetime(p["start_date"]) for p in st.session_state.data["projects"]]
    )
    max_date = max(
        [pd.to_datetime(p["end_date"]) for p in st.session_state.data["projects"]]
    )

    # Create the Gantt data
    gantt_data = create_gantt_data(
        st.session_state.data["projects"], st.session_state.data
    )

    # Use the unified filter component but with project date constraints
    with st.container():
        st.subheader("Filter Criteria")
        col1, col2 = st.columns(2)
        with col1:
            start_date = pd.to_datetime(
                st.date_input(
                    "From",
                    value=min_date.date(),
                    min_value=min_date.date(),
                    max_value=max_date.date(),
                )
            )
        with col2:
            end_date = pd.to_datetime(
                st.date_input(
                    "To",
                    value=max_date.date(),
                    min_value=min_date.date(),
                    max_value=max_date.date(),
                )
            )

        resource_types = st.multiselect(
            "Resource Types",
            options=["Person", "Team", "Department"],
            default=["Person", "Team", "Department"],
        )

        utilization_threshold = st.slider(
            "Minimum Utilization %", min_value=0, max_value=100, value=0, step=5
        )

    # Apply filters
    filtered_data = filter_gantt_data(
        gantt_data, start_date, end_date, resource_types, utilization_threshold
    )

    # Display the dashboard with filtered data
    if filtered_data.empty:
        st.warning("No data matches your filter criteria. Try adjusting the filters.")
    else:
        display_utilization_dashboard(filtered_data, start_date, end_date)


def display_import_export_data_tab():
    display_action_bar()

    st.subheader("Data Tools")

    col1, col2 = st.columns(2)

    with col1:
        st.write("Import Data")
        uploaded_file = st.file_uploader("Upload JSON file", type="json")

        if uploaded_file is not None:
            data = load_json(uploaded_file)
            if data:
                if st.button("Import Data"):
                    st.session_state.data = data
                    departments = [d["name"] for d in data.get("departments", [])]
                    regenerate_department_colors(departments)
                    st.success("Data imported successfully")
                    st.rerun()

    with col2:
        st.write("Export Data")
        filename = st.text_input("Filename", "resource_data.json")

        if st.button("Export Data"):
            st.markdown(
                save_json(st.session_state.data, filename), unsafe_allow_html=True
            )
            st.success("Click the link above to download the file")


def display_settings_tab():
    display_action_bar()

    st.subheader("Configuration")
    display_color_settings()

    st.subheader("Currency Settings")
    currency, currency_format = load_currency_settings()

    currency_options = [
        "USD - United States Dollar",
        "EUR - Euro",
        "GBP - British Pound",
        "JPY - Japanese Yen",
        "AUD - Australian Dollar",
        "CAD - Canadian Dollar",
        "CHF - Swiss Franc",
        "CNY - Chinese Yuan",
        "SEK - Swedish Krona",
        "NZD - New Zealand Dollar",
    ]
    currency_codes = [option.split(" - ")[0] for option in currency_options]

    with st.form("currency_settings_form"):
        selected_currency = st.selectbox(
            "Select Currency",
            options=currency_options,
            index=currency_codes.index(currency) if currency in currency_codes else 0,
        )
        currency_code = selected_currency.split(" - ")[0]

        symbol_position = st.radio(
            "Currency Symbol Position",
            options=["prefix", "suffix"],
            index=["prefix", "suffix"].index(currency_format["symbol_position"]),
        )
        decimal_places = st.number_input(
            "Decimal Places",
            min_value=0,
            max_value=4,
            value=currency_format["decimal_places"],
            step=1,
        )

        submit = st.form_submit_button("Save Currency Settings")
        if submit:
            save_currency_settings(
                currency_code,
                {"symbol_position": symbol_position, "decimal_places": decimal_places},
            )
            st.success("Currency settings updated.")

    st.subheader("Daily Cost Settings")
    from configuration import save_daily_cost_settings

    from configuration import load_daily_cost_settings

    max_daily_cost = load_daily_cost_settings()
    with st.form("daily_cost_form"):
        new_max_cost = st.number_input(
            "Max Daily Cost", min_value=1.0, value=float(max_daily_cost), step=100.0
        )
        if st.form_submit_button("Save Max Daily Cost"):
            save_daily_cost_settings(new_max_cost)
            st.success("Max daily cost updated.")


def initialize_session_state():
    """
    Initialize all session state variables used throughout the application.
    """
    if "data" not in st.session_state:
        st.session_state.data = load_demo_data()

    settings_file = "settings.json"
    if not os.path.exists(settings_file):
        departments = [d["name"] for d in st.session_state.data["departments"]]

        default_settings = {
            "department_colors": {},
            "utilization_colorscale": [
                [0, "#00FF00"],
                [0.5, "#FFFF00"],
                [1, "#FF0000"],
            ],
        }

        colorscale = px.colors.qualitative.Plotly + px.colors.qualitative.D3
        for i, dept in enumerate(departments):
            default_settings["department_colors"][dept] = colorscale[
                i % len(colorscale)
            ].lower()

        with open(settings_file, "w") as file:
            json.dump(default_settings, file, indent=4)

    if "new_project_people" not in st.session_state:
        st.session_state["new_project_people"] = []
    if "new_project_teams" not in st.session_state:
        st.session_state["new_project_teams"] = []
    if "edit_project_people" not in st.session_state:
        st.session_state["edit_project_people"] = []
    if "edit_project_teams" not in st.session_state:
        st.session_state["edit_project_teams"] = []
    if "last_edited_project" not in st.session_state:
        st.session_state["last_edited_project"] = None
    if "edit_form_initialized" not in st.session_state:
        st.session_state["edit_form_initialized"] = False

    check_data_integrity()


def apply_custom_css():
    """Apply custom CSS for better mobile experience, card styling, and hover effects."""
    st.markdown(
        """
    <style>
    /* Card styling with hover effects */
    div.stMarkdown div.card {
        border: 1px solid rgba(49, 51, 63, 0.2);
        border-radius: 0.5rem;
        padding: 1rem;
        margin-bottom: 1rem;
        transition: all 0.3s ease;
        background-color: rgba(255, 255, 255, 0.05);
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        /* Remove align-items: center to restore left-aligned text */
    }
    
    div.stMarkdown div.card:hover {
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
        transform: translateY(-2px);
        border-color: #ff4b4b;
    }

    /* Card-specific colors */
    div.stMarkdown div.person-card {
        border-left: 5px solid green;
    }
    div.stMarkdown div.team-card {
        border-left: 5px solid blue;
    }
    div.stMarkdown div.department-card {
        border-left: 5px solid purple;
    }

    /* Action buttons */
    .card-actions {
        margin-top: 10px;
        display: flex;
        justify-content: space-between;
    }
    .action-btn {
        background-color: #007bff;
        color: white;
        border: none;
        padding: 5px 10px;
        border-radius: 4px;
        cursor: pointer;
        transition: background-color 0.3s ease;
    }
    .action-btn:hover {
        background-color: #0056b3;
    }

    /* Responsive layout */
    @media (max-width: 1024px) {
        div.stMarkdown div.card {
            /* Allow dynamic height for smaller screens */
        }
    }
    @media (max-width: 768px) {
        div.stMarkdown div.card {
            /* Allow dynamic height for mobile screens */
        }
    }
    </style>
    """,
        unsafe_allow_html=True,
    )


def check_data_integrity():
    """Checks and fixes data integrity issues."""
    invalid_teams = [
        t["name"] for t in st.session_state.data["teams"] if len(t["members"]) < 2
    ]

    if invalid_teams:
        st.warning(
            f"Found {len(invalid_teams)} teams with fewer than 2 members. These teams will be automatically removed."
        )
        for team_name in invalid_teams:
            delete_resource(st.session_state.data["teams"], team_name, "team")


def main():
    """Orchestrates the Streamlit application flow with improved navigation."""
    apply_custom_css()

    initialize_session_state()

    with st.sidebar:
        st.title("Resource Management")

        st.markdown("### Quick Search")
        search_query = st.text_input("Search resources and projects")
        if search_query:
            search_results = global_search(search_query)
            if search_results:
                st.markdown("### Search Results")
                for result_type, result_name in search_results:
                    st.markdown(f"- {result_type}: {result_name}")
            else:
                st.info("No results found")

        st.markdown("---")
        st.markdown("### Navigation")

        st.markdown("#### Dashboard")
        if st.button("🏠 Dashboard", use_container_width=True):
            st.session_state["active_tab"] = "Dashboard"
            st.rerun()

        st.markdown("#### Resource Management")
        if st.button("👥 Resource Management", use_container_width=True):
            st.session_state["active_tab"] = "Resource Management"
            st.rerun()
        if st.button("📋 Project Management", use_container_width=True):
            st.session_state["active_tab"] = "Project Management"
            st.rerun()

        st.markdown("#### Resource Analytics")
        if st.button("📈 Workload Distribution", use_container_width=True):
            st.session_state["active_tab"] = "Workload Distribution"
            st.rerun()
        if st.button("📉 Performance Metrics", use_container_width=True):
            st.session_state["active_tab"] = "Performance Metrics"
            st.rerun()
        if st.button("📊 Availability Forecast", use_container_width=True):
            st.session_state["active_tab"] = "Availability Forecast"
            st.rerun()
        if st.button("🗓️ Resource Calendar", use_container_width=True):
            st.session_state["active_tab"] = "Resource Calendar"
            st.rerun()

        st.markdown("#### Tools")
        if st.button("💾 Data Tools", use_container_width=True):
            st.session_state["active_tab"] = "Data Tools"
            st.rerun()
        if st.button("⚙️ Configuration", use_container_width=True):
            st.session_state["active_tab"] = "Configuration"
            st.rerun()

    st.title("Resource Management App")

    if st.session_state.get("active_tab") == "Dashboard":
        display_home_tab()
    elif st.session_state.get("active_tab") == "Resource Management":
        display_manage_resources_tab()
    elif st.session_state.get("active_tab") == "Project Management":
        display_manage_projects_tab()
    elif st.session_state.get("active_tab") == "Workload Distribution":
        display_visualize_data_tab()
    elif st.session_state.get("active_tab") == "Performance Metrics":
        display_resource_utilization_tab()
    elif st.session_state.get("active_tab") == "Data Tools":
        display_import_export_data_tab()
    elif st.session_state.get("active_tab") == "Configuration":
        display_settings_tab()
    elif st.session_state.get("active_tab") == "Availability Forecast":
        display_capacity_planning_tab()
    elif st.session_state.get("active_tab") == "Resource Calendar":
        display_resource_calendar_tab()
    else:
        display_home_tab()


def display_resource_calendar_tab():
    display_action_bar()
    st.subheader("Resource Calendar")

    if not st.session_state.data["projects"]:
        st.warning("No projects found. Please add projects first.")
        return
    elif not (
        st.session_state.data["people"]
        or st.session_state.data["teams"]
        or st.session_state.data["departments"]
    ):
        st.warning(
            "No resources found. Please add people, teams, or departments first."
        )
        return

    # Get min/max dates from projects for filter constraints
    min_date = min(
        [pd.to_datetime(p["start_date"]) for p in st.session_state.data["projects"]]
    )
    max_date = max(
        [pd.to_datetime(p["end_date"]) for p in st.session_state.data["projects"]]
    )

    # Use the unified filter component with project date constraints
    with st.container():
        st.subheader("Filter Criteria")
        col1, col2 = st.columns(2)
        with col1:
            start_date = pd.to_datetime(
                st.date_input(
                    "From",
                    value=min_date.date(),
                    min_value=min_date.date(),
                    max_value=max_date.date(),
                )
            )
        with col2:
            end_date = pd.to_datetime(
                st.date_input(
                    "To",
                    value=max_date.date(),
                    min_value=min_date.date(),
                    max_value=max_date.date(),
                )
            )

        resource_types = st.multiselect(
            "Resource Types",
            options=["Person", "Team", "Department"],
            default=["Person", "Team", "Department"],
        )

        utilization_threshold = st.slider(
            "Minimum Utilization %", min_value=0, max_value=100, value=0, step=5
        )

    # Create and filter data
    gantt_data = create_gantt_data(
        st.session_state.data["projects"], st.session_state.data
    )

    filtered_data = filter_gantt_data(
        gantt_data, start_date, end_date, resource_types, utilization_threshold
    )

    # Display the calendar with filtered data
    if filtered_data.empty:
        st.warning("No data matches your filter criteria. Try adjusting the filters.")
    else:
        display_resource_calendar(filtered_data, start_date, end_date)


def display_capacity_planning_tab():
    display_action_bar()
    st.subheader("Availability Forecast")

    if not st.session_state.data["projects"]:
        st.warning("No projects found. Please add projects first.")
        return
    elif not (
        st.session_state.data["people"]
        or st.session_state.data["teams"]
        or st.session_state.data["departments"]
    ):
        st.warning(
            "No resources found. Please add people, teams, or departments first."
        )
        return

    # Get min/max dates from projects for filter constraints
    min_date = min(
        [pd.to_datetime(p["start_date"]) for p in st.session_state.data["projects"]]
    )
    max_date = max(
        [pd.to_datetime(p["end_date"]) for p in st.session_state.data["projects"]]
    )

    # Use the unified filter component with project date constraints
    with st.container():
        st.subheader("Filter Criteria")
        col1, col2 = st.columns(2)
        with col1:
            start_date = pd.to_datetime(
                st.date_input(
                    "From",
                    value=min_date.date(),
                    min_value=min_date.date(),
                    max_value=max_date.date(),
                )
            )
        with col2:
            end_date = pd.to_datetime(
                st.date_input(
                    "To",
                    value=max_date.date(),
                    min_value=min_date.date(),
                    max_value=max_date.date(),
                )
            )

        resource_types = st.multiselect(
            "Resource Types",
            options=["Person", "Team", "Department"],
            default=["Person", "Team", "Department"],
        )

        utilization_threshold = st.slider(
            "Minimum Utilization %", min_value=0, max_value=100, value=0, step=5
        )

    # Create and filter data
    gantt_data = create_gantt_data(
        st.session_state.data["projects"], st.session_state.data
    )

    filtered_data = filter_gantt_data(
        gantt_data, start_date, end_date, resource_types, utilization_threshold
    )

    # Display the dashboard with filtered data
    if filtered_data.empty:
        st.warning("No data matches your filter criteria. Try adjusting the filters.")
    else:
        display_capacity_planning_dashboard(filtered_data, start_date, end_date)


def display_visualization_tab():
    display_action_bar()
    st.subheader("Resource Insights")

    # Add date filters here at the top level if they should apply to all visualizations
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", value=pd.to_datetime("today"))
    with col2:
        end_date = st.date_input(
            "End Date", value=pd.to_datetime("today") + pd.Timedelta(days=90)
        )

    # Create gantt data
    gantt_data = create_gantt_data(
        st.session_state.data["projects"], st.session_state.data
    )

    # Define the main navigation tabs
    viz_tabs = st.tabs(
        [
            "Workload Distribution",
            "Performance Metrics",
            "Availability Forecast",
            "Resource Calendar",
        ]
    )

    with viz_tabs[0]:
        display_gantt_chart(gantt_data)

    with viz_tabs[1]:
        display_utilization_dashboard(gantt_data, start_date, end_date)

    with viz_tabs[2]:
        display_capacity_planning_dashboard(start_date, end_date)

    with viz_tabs[3]:
        display_resource_calendar(start_date, end_date)


if __name__ == "__main__":
    main()
