"""
Resource Management Application

This module orchestrates the Streamlit application flow, including
navigation, data loading, and rendering of various tabs for managing
resources, projects, and visualizing data.
"""

# Standard library imports
import json
import os

# Third-party imports
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

# Local module imports
from color_management import (
    display_color_settings,
    load_currency_settings,
    regenerate_department_colors,
    save_currency_settings,
)
from data_handlers import (
    calculate_project_cost,
    calculate_resource_utilization,
    create_gantt_data,
    filter_dataframe,
    find_resource_conflicts,
    load_json,
    save_json,
)
from resource_forms import (
    add_project_form,
    department_crud_form,
    edit_project_form,
    person_crud_form,
    team_crud_form,
)
from utils import (
    _apply_sorting,
    check_circular_dependencies,
    confirm_action,
    display_filtered_resource,
    paginate_dataframe,
)
from visualizations import display_gantt_chart, display_utilization_dashboard

# Set up basic page configuration
st.set_page_config(page_title="Resource Management App", layout="wide")


# Load demo data from JSON file
def load_demo_data():
    with open("resource_data.json", "r") as file:
        return json.load(file)


# Initialize session state for data persistence
if "data" not in st.session_state:
    st.session_state.data = load_demo_data()


def display_home_tab():
    """Displays an enhanced home dashboard with key metrics and charts."""
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
        projects_df = pd.DataFrame(
            [
                {
                    "Project": p["name"],
                    "Start": pd.to_datetime(p["start_date"]),
                    "Finish": pd.to_datetime(p["end_date"]),
                    "Priority": p["priority"],
                    "Resources": len(p["assigned_resources"]),
                    "Budget": p.get("allocated_budget", 0),
                }
                for p in st.session_state.data["projects"]
            ]
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
            height=300,
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
                            "Allocated Budget": project["allocated_budget"],
                            "Actual Cost": actual_cost,
                            "Variance": project["allocated_budget"] - actual_cost,
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
    """Displays a consolidated view of all resources with type filtering."""
    st.subheader("Manage Resources")

    # Add tabs for different resource views
    view_type = st.radio(
        "View", ["All Resources", "People", "Teams", "Departments"], horizontal=True
    )

    if view_type == "All Resources":
        display_consolidated_resources()
    elif view_type == "People":
        st.subheader("Manage People")
        display_filtered_resource("people", "people")
        person_crud_form()
    elif view_type == "Teams":
        st.subheader("Manage Teams")
        display_filtered_resource("teams", "teams", distinct_filters=True)
        team_crud_form()
    elif view_type == "Departments":
        st.subheader("Manage Departments")
        display_filtered_resource(
            "departments", "departments", distinct_filters=True, filter_by="teams"
        )
        department_crud_form()

    # Check for circular dependencies
    cycles = check_circular_dependencies()
    if cycles:
        with st.expander("⚠️ Circular Dependencies Detected", expanded=True):
            st.error("The following circular dependencies were detected:")
            for cycle in cycles:
                st.markdown(f"- {cycle}")
            st.markdown(
                "**Impact:** Circular dependencies can cause issues with resource allocation and cost calculations."
            )
            st.markdown(
                "**Solution:** Review the team memberships to eliminate overlapping assignments."
            )


def display_consolidated_resources():
    """Display a consolidated view of all resources using cards."""
    # Create filtered collections of resources
    people = st.session_state.data["people"]
    teams = st.session_state.data["teams"]
    departments = st.session_state.data["departments"]

    # Add filter controls
    with st.expander("Search and Filter Resources", expanded=False):
        search_term = st.text_input("Search Resources", key="search_all_resources")

        col1, col2 = st.columns(2)
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

    # Apply filters
    if search_term:
        people = [p for p in people if search_term.lower() in str(p).lower()]
        teams = [t for t in teams if search_term.lower() in str(t).lower()]
        departments = [d for d in departments if search_term.lower() in str(d).lower()]

    if dept_filter:
        people = [p for p in people if p["department"] in dept_filter]
        teams = [t for t in teams if t["department"] in dept_filter]
        departments = [d for d in departments if d["name"] in dept_filter]

    # Display resources as cards
    st.write("### Resources Overview")

    # Create tabs for different view options
    view_option = st.radio("View As:", ["Cards", "Visual Map"], horizontal=True)

    if view_option == "Cards":
        _display_resource_cards(people, teams, departments, type_filter)
    else:
        _display_resource_visual_map(people, teams, departments, type_filter)


def _display_resource_cards(people, teams, departments, type_filter):
    """Display resources as visual cards with consistent sizing."""
    # Load currency settings
    currency, _ = load_currency_settings()

    # Calculate columns based on screen width (responsive design)
    cols = st.columns(3)

    # Track index for distributing cards across columns
    idx = 0

    # Display people cards
    if "Person" in type_filter:
        for person in people:
            with cols[idx % 3]:
                st.markdown(
                    f"""
                    <div class="card">
                        <h3>👤 {person["name"]}</h3>
                        <div style="background-color: {"rgba(255,215,0,0.2)" if person["team"] else "rgba(100,100,100,0.1)"}; padding: 5px; border-radius: 4px; margin-bottom: 10px; display: inline-block;">
                            <span style="font-weight: bold;">{"👥 " + person["team"] if person["team"] else "Individual Contributor"}</span>
                        </div>
                        <p><strong>Role:</strong> {person["role"]}</p>
                        <p><strong>Department:</strong> {person["department"]}</p>
                        <p><strong>Daily Cost:</strong> {currency} {person["daily_cost"]:,.2f}</p>
                        <p><strong>Work Days:</strong> {", ".join(person["work_days"])}</p>
                        <p><strong>Hours:</strong> {person["daily_work_hours"]} per day</p>
                        <div style="height: 10px;"></div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            idx += 1

    # Display team cards
    if "Team" in type_filter:
        for team in teams:
            with cols[idx % 3]:
                team_cost = sum(
                    person["daily_cost"]
                    for person in people
                    if person["name"] in team["members"]
                )
                st.markdown(
                    f"""
                    <div class="card">
                        <h3>👥 {team["name"]}</h3>
                        <div style="height: 40px;"></div> <!-- Placeholder for consistent height -->
                        <p><strong>Department:</strong> {team["department"]}</p>
                        <p><strong>Members:</strong> {len(team["members"])}</p>
                        <p><strong>Daily Cost:</strong> {currency} {team_cost:,.2f}</p>
                        <div style="height: 30px;"></div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            idx += 1

    # Display department cards
    if "Department" in type_filter:
        for dept in departments:
            dept_cost = sum(
                person["daily_cost"]
                for person in people
                if person["department"] == dept["name"]
            )
            st.markdown(
                f"""
                <div class="card">
                    <h3>🏢 {dept["name"]}</h3>
                    <div style="height: 40px;"></div> <!-- Placeholder for consistent height -->
                    <p><strong>Teams:</strong> {len(dept["teams"])}</p>
                    <p><strong>Members:</strong> {len(dept["members"])}</p>
                    <p><strong>Daily Cost:</strong> {currency} {dept_cost:,.2f}</p>
                    <div style="height: 30px;"></div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            idx += 1


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
    """
    Displays the content for the Manage Projects tab.
    Fixed priority handling and improved project management.
    """
    st.subheader("Manage Projects")

    # Display existing projects with enhanced table
    if not st.session_state.data["projects"]:
        st.warning("No projects found. Please add a project first.")
        add_project_form()
        return

    # Create the projects DataFrame with proper parsing
    projects_df = _create_projects_dataframe()

    # Add priority count column to identify duplicate priorities
    projects_df["Priority Count"] = projects_df.groupby("Priority")[
        "Priority"
    ].transform("count")
    projects_df["Priority Label"] = projects_df.apply(
        lambda row: f"Priority {row['Priority']} (Duplicate)"
        if row["Priority Count"] > 1
        else f"Priority {row['Priority']}",
        axis=1,
    )

    # Apply search and filtering
    projects_df = _filter_projects_dataframe(projects_df)

    # Display the filtered dataframe
    st.dataframe(projects_df, use_container_width=True)

    # Add and edit project forms
    add_project_form()
    edit_project_form()

    # Delete project functionality
    _handle_project_deletion()


def _create_projects_dataframe():
    """Helper function to create a DataFrame from project data."""
    # Fix undefined function `parse_resources`
    from data_handlers import parse_resources

    return pd.DataFrame(
        [
            {
                "Name": p["name"],
                "Start Date": pd.to_datetime(p["start_date"]).strftime("%Y-%m-%d"),
                "End Date": pd.to_datetime(p["end_date"]).strftime("%Y-%m-%d"),
                "Priority": p["priority"],
                "Duration (days)": (
                    pd.to_datetime(p["end_date"]) - pd.to_datetime(p["start_date"])
                ).days
                + 1,
                # Parse assigned resources
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

        # Apply filters
        projects_df = _apply_search_filter(projects_df, search_term)
        projects_df = _apply_date_filter(projects_df, date_filter)
        projects_df = _apply_resource_filters(projects_df, resource_filters)

        # Apply sorting and pagination
        projects_df = _apply_sorting(projects_df, "projects")  # Use imported function
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
        start_date, end_date = date_range
        projects_df = projects_df[
            (pd.to_datetime(projects_df["Start Date"]) >= pd.to_datetime(start_date))
            & (pd.to_datetime(projects_df["End Date"]) <= pd.to_datetime(end_date))
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
        # Remove the project from the data
        st.session_state.data["projects"] = [
            p for p in st.session_state.data["projects"] if p["name"] != delete_project
        ]

        st.success(f"Deleted project {delete_project}")
        st.rerun()


def display_visualize_data_tab():
    """
    Displays the content for the Visualize Data tab.
    """
    st.subheader("Resource Allocation Visualization")

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

    # Filter Options
    filters = _get_visualization_filters()

    # Create visualization data
    gantt_data = create_gantt_data(
        st.session_state.data["projects"], st.session_state.data
    )

    # Apply filters
    gantt_data = _apply_visualization_filters(gantt_data, filters)

    # Display Gantt chart
    _display_gantt_chart_with_filters(gantt_data)

    # Check for resource conflicts
    _display_resource_conflicts(gantt_data)

    # Drill-down view for resources
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
    display_gantt_chart(gantt_data)


def _display_resource_conflicts(gantt_data):
    """Check and display resource conflicts."""
    conflicts = find_resource_conflicts(gantt_data)
    if conflicts:
        st.subheader("Resource Conflicts")

        conflict_summary = {}
        for conflict in conflicts:
            resource = conflict["resource"]
            if resource not in conflict_summary:
                conflict_summary[resource] = 0
            conflict_summary[resource] += 1

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Conflicts", len(conflicts))
        with col2:
            st.metric("Affected Resources", len(conflict_summary))

        conflicts_df = pd.DataFrame(conflicts)
        conflicts_df["overlap_start"] = pd.to_datetime(conflicts_df["overlap_start"])
        conflicts_df["overlap_end"] = pd.to_datetime(conflicts_df["overlap_end"])

        fig = px.timeline(
            conflicts_df,
            x_start="overlap_start",
            x_end="overlap_end",
            y="resource",
            color="overlap_days",
            hover_data=["project1", "project2", "overlap_days"],
            color_continuous_scale="Reds",
            title="Resource Conflict Timeline",
        )
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Conflict Details")
        filtered_conflicts = filter_dataframe(
            conflicts_df.rename(
                columns={
                    "resource": "Resource",
                    "project1": "Project 1",
                    "project2": "Project 2",
                    "overlap_days": "Overlapping Days",
                }
            ),
            key="Conflicts",
            columns=["Resource", "Project 1", "Project 2", "Overlapping Days"],
        )
        st.dataframe(filtered_conflicts, use_container_width=True)

        # Update dropdown labels
        with st.expander("Search and Filter Conflicts", expanded=False):
            st.text_input("Search Conflicts", key="search_conflicts")
            st.multiselect("Filter Resource", options=[], key="filter_resource")
            st.multiselect("Filter Project 1", options=[], key="filter_project1")
            st.multiselect("Filter Project 2", options=[], key="filter_project2")
    else:
        st.success("No resource conflicts detected")


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
    """
    Displays the content for the Resource Utilization tab.
    """
    st.subheader("Resource Utilization Dashboard")

    if not st.session_state.data["projects"]:
        st.warning("No projects found. Please add projects first.")
    elif not (
        st.session_state.data["people"]
        or st.session_state.data["teams"]
        or st.session_state.data["departments"]
    ):
        st.warning(
            "No resources found. Please add people, teams, or departments first."
        )
    else:
        # Create base data
        gantt_data = create_gantt_data(
            st.session_state.data["projects"], st.session_state.data
        )

        # Date range filter for utilization
        st.subheader("Utilization Period")

        # Get min and max dates from projects
        min_date = min(
            [pd.to_datetime(p["start_date"]) for p in st.session_state.data["projects"]]
        )
        max_date = max(
            [pd.to_datetime(p["end_date"]) for p in st.session_state.data["projects"]]
        )

        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input(
                "From",
                value=min_date.date(),
                min_value=min_date.date(),
                max_value=max_date.date(),
            )

        with col2:
            end_date = st.date_input(
                "To",
                value=max_date.date(),
                min_value=min_date.date(),
                max_value=max_date.date(),
            )

        # Resource type filter
        resource_types = st.multiselect(
            "Resource Types",
            options=["Person", "Team", "Department"],
            default=["Person", "Team", "Department"],
        )

        # Filter data by resource type
        if resource_types:
            filtered_data = gantt_data[gantt_data["Type"].isin(resource_types)]
        else:
            filtered_data = gantt_data

        # Display utilization dashboard with the filtered data
        display_utilization_dashboard(filtered_data, start_date, end_date)


def display_import_export_data_tab():
    """
    Displays the content for the Import/Export Data tab.
    """
    st.subheader("Import/Export Data")

    col1, col2 = st.columns(2)

    with col1:
        st.write("Import Data")
        uploaded_file = st.file_uploader("Upload JSON file", type="json")

        if uploaded_file is not None:
            data = load_json(uploaded_file)
            if data:
                if st.button("Import Data"):
                    st.session_state.data = data
                    # Regenerate department colors based on the imported data
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
    """
    Displays the content for the Settings tab.
    """
    st.subheader("Settings")
    display_color_settings()

    st.subheader("Currency Settings")
    currency, currency_format = load_currency_settings()

    # Define a list of common currencies with both code and name
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
        # Display currency dropdown with code and name
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
    from color_management import save_daily_cost_settings

    # Define or import the load_daily_cost_settings function
    from color_management import load_daily_cost_settings

    max_daily_cost = load_daily_cost_settings()
    with st.form("daily_cost_form"):
        new_max_cost = st.number_input(
            "Max Daily Cost (€)", min_value=1.0, value=float(max_daily_cost), step=100.0
        )
        if st.form_submit_button("Save Max Daily Cost"):
            save_daily_cost_settings(new_max_cost)
            st.success("Max daily cost updated.")


def initialize_session_state():
    """
    Initialize all session state variables used throughout the application.
    """
    # Load data if not already loaded
    if "data" not in st.session_state:
        st.session_state.data = load_demo_data()

    # Initialize settings.json with proper values
    settings_file = "settings.json"
    if not os.path.exists(settings_file):
        # Get departments from the data
        departments = [d["name"] for d in st.session_state.data["departments"]]

        # Create default settings structure
        default_settings = {
            "department_colors": {},
            "utilization_colorscale": [
                [0, "#00FF00"],  # Green for 0% utilization
                [0.5, "#FFFF00"],  # Yellow for 50% utilization
                [1, "#FF0000"],  # Red for 100% or over-utilization
            ],
        }

        # Generate colors for departments
        colorscale = px.colors.qualitative.Plotly + px.colors.qualitative.D3
        for i, dept in enumerate(departments):
            default_settings["department_colors"][dept] = colorscale[
                i % len(colorscale)
            ].lower()

        # Save the settings file
        with open(settings_file, "w") as file:
            json.dump(default_settings, file, indent=4)

    # Project form state variables
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


def apply_custom_css():
    """Apply custom CSS for better mobile experience and card styling."""
    st.markdown(
        """
    <style>
    /* Card styling with theme-compatible colors */
    div.stMarkdown div.card {
        border: 1px solid rgba(49, 51, 63, 0.2);
        border-radius: 0.5rem;
        padding: 1rem;
        margin-bottom: 1rem;
        transition: all 0.3s ease;
        background-color: rgba(255, 255, 255, 0.05);
    }
    
    div.stMarkdown div.card:hover {
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
        transform: translateY(-2px);
        border-color: #ff4b4b;
    }
    
    /* Team member indicator */
    .team-member {
        color: #00cc96;
        font-weight: bold;
    }
    
    /* Individual contributor indicator */
    .individual {
        color: #ff9e4a;
        font-weight: bold;
    }
    
    @media (max-width: 640px) {
        .stButton button {
            height: 3rem;
            font-size: 1rem;
        }
    }
    </style>
    """,
        unsafe_allow_html=True,
    )


# Call the function to apply CSS
apply_custom_css()


def main():
    """Orchestrates the Streamlit application flow with responsive design."""
    apply_custom_css()

    st.title("Resource Management App")

    # Detect viewport width (workaround, as Streamlit doesn't expose it directly)
    is_mobile = False

    # Create sidebar navigation
    st.sidebar.title("Navigation")

    with st.sidebar.expander("Quick Actions", expanded=True):
        if is_mobile:
            # Single column for mobile
            if st.button("➕ Add Person", use_container_width=True):
                st.session_state["active_tab"] = "Manage Resources"
                st.session_state["resource_type"] = "People"
                st.rerun()

            if st.button("➕ Add Team", use_container_width=True):
                st.session_state["active_tab"] = "Manage Resources"
                st.session_state["resource_type"] = "Teams"
                st.rerun()

            if st.button("➕ Add Project", use_container_width=True):
                st.session_state["active_tab"] = "Manage Projects"
                st.rerun()

            if st.button("📊 View Gantt", use_container_width=True):
                st.session_state["active_tab"] = "Visualize Data"
                st.rerun()
        else:
            # Two columns for desktop
            col1, col2 = st.sidebar.columns(2)
            with col1:
                if st.button("➕ Add Person", use_container_width=True):
                    st.session_state["active_tab"] = "Manage Resources"
                    st.session_state["resource_type"] = "People"
                    st.rerun()

                if st.button("➕ Add Team", use_container_width=True):
                    st.session_state["active_tab"] = "Manage Resources"
                    st.session_state["resource_type"] = "Teams"
                    st.rerun()
            with col2:
                if st.button("➕ Add Project", use_container_width=True):
                    st.session_state["active_tab"] = "Manage Projects"
                    st.rerun()

                if st.button("📊 View Gantt", use_container_width=True):
                    st.session_state["active_tab"] = "Visualize Data"
                    st.rerun()

    page = st.sidebar.radio(
        "Go to",
        [
            "Home",
            "Manage Resources",
            "Manage Projects",
            "Visualize Data",
            "Resource Utilization",
            "Import/Export Data",
            "Settings",
        ],
        key="active_tab",
    )

    if page == "Home":
        display_home_tab()
    elif page == "Manage Resources":
        display_manage_resources_tab()
    elif page == "Manage Projects":
        display_manage_projects_tab()
    elif page == "Visualize Data":
        display_visualize_data_tab()
    elif page == "Resource Utilization":
        display_resource_utilization_tab()
    elif page == "Import/Export Data":
        display_import_export_data_tab()
    elif page == "Settings":
        display_settings_tab()


if __name__ == "__main__":
    main()
