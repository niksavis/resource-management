# Import necessary libraries
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
from datetime import datetime, timedelta
import io
import base64
import numpy as np
import math

# Set up basic page configuration
st.set_page_config(page_title="Resource Management App", layout="wide")


# JSON file handling functions
def load_json(file):
    try:
        data = json.load(file)
        return data
    except Exception as e:
        st.error(f"Error loading JSON file: {e}")
        return None


def save_json(data, filename):
    json_str = json.dumps(data, indent=4)
    b64 = base64.b64encode(json_str.encode()).decode()
    href = f'<a href="data:application/json;base64,{b64}" download="{filename}">Download JSON file</a>'
    return href


# Demo data for initial app state
DEMO_DATA = {
    "people": [
        {
            "name": "John Smith",
            "role": "Developer",
            "department": "Engineering",
            "team": "Frontend Team",
        },
        {
            "name": "Sarah Johnson",
            "role": "UX/UI Designer",
            "department": "Design",
            "team": "UI Team",
        },
        {
            "name": "Michael Chen",
            "role": "Product Owner",
            "department": "Product",
            "team": "Core Product",
        },
        {
            "name": "Emily Davis",
            "role": "Project Manager",
            "department": "Project Management",
            "team": None,
        },
        {
            "name": "David Wilson",
            "role": "Developer",
            "department": "Engineering",
            "team": "Backend Team",
        },
        {
            "name": "Lisa Garcia",
            "role": "Developer",
            "department": "Engineering",
            "team": "Frontend Team",
        },
        {
            "name": "Robert Taylor",
            "role": "Domain Lead",
            "department": "Engineering",
            "team": "Backend Team",
        },
        {
            "name": "Jennifer Lee",
            "role": "UX/UI Designer",
            "department": "Design",
            "team": "UI Team",
        },
        {
            "name": "Mark Thompson",
            "role": "Head of Department",
            "department": "Engineering",
            "team": None,
        },
        {
            "name": "Patricia Rodriguez",
            "role": "Key Stakeholder",
            "department": "Executive",
            "team": None,
        },
    ],
    "teams": [
        {
            "name": "Frontend Team",
            "department": "Engineering",
            "members": ["John Smith", "Lisa Garcia"],
        },
        {
            "name": "Backend Team",
            "department": "Engineering",
            "members": ["David Wilson", "Robert Taylor"],
        },
        {
            "name": "UI Team",
            "department": "Design",
            "members": ["Sarah Johnson", "Jennifer Lee"],
        },
        {
            "name": "Core Product",
            "department": "Product",
            "members": ["Michael Chen", "Emily Davis"],
        },
    ],
    "departments": [
        {
            "name": "Engineering",
            "teams": ["Frontend Team", "Backend Team"],
            "members": [
                "John Smith",
                "Lisa Garcia",
                "David Wilson",
                "Robert Taylor",
                "Mark Thompson",
            ],
        },
        {
            "name": "Design",
            "teams": ["UI Team"],
            "members": ["Sarah Johnson", "Jennifer Lee"],
        },
        {"name": "Product", "teams": ["Core Product"], "members": ["Michael Chen"]},
        {"name": "Project Management", "teams": [], "members": ["Emily Davis"]},
        {"name": "Executive", "teams": [], "members": ["Patricia Rodriguez"]},
    ],
    "projects": [
        {
            "name": "Website Redesign",
            "start_date": "2025-04-01",
            "end_date": "2025-06-15",
            "priority": 1,
            "assigned_resources": ["Frontend Team", "UI Team", "Emily Davis"],
        },
        {
            "name": "API Development",
            "start_date": "2025-03-15",
            "end_date": "2025-05-30",
            "priority": 2,
            "assigned_resources": ["Backend Team", "Michael Chen"],
        },
        {
            "name": "Mobile App Phase 1",
            "start_date": "2025-05-01",
            "end_date": "2025-07-31",
            "priority": 1,
            "assigned_resources": ["Frontend Team", "UI Team", "Backend Team"],
        },
        {
            "name": "Security Audit",
            "start_date": "2025-04-15",
            "end_date": "2025-05-15",
            "priority": 3,
            "assigned_resources": ["David Wilson", "Mark Thompson"],
        },
        {
            "name": "Product Strategy",
            "start_date": "2025-03-01",
            "end_date": "2025-04-15",
            "priority": 2,
            "assigned_resources": ["Executive", "Product"],
        },
    ],
}

# Initialize session state for data persistence
if "data" not in st.session_state:
    st.session_state.data = DEMO_DATA


# Convert project data to DataFrame for visualization
def create_gantt_data(projects, resources):
    df_data = []

    for project in projects:
        for resource in project["assigned_resources"]:
            # Determine resource type and department
            resource_type = "Unknown"
            department = "Unknown"

            # Check if resource is a person
            for person in resources["people"]:
                if person["name"] == resource:
                    resource_type = "Person"
                    department = person["department"]
                    break

            # Check if resource is a team
            if resource_type == "Unknown":
                for team in resources["teams"]:
                    if team["name"] == resource:
                        resource_type = "Team"
                        department = team["department"]
                        break

            # Check if resource is a department
            if resource_type == "Unknown":
                for dept in resources["departments"]:
                    if dept["name"] == resource:
                        resource_type = "Department"
                        department = resource
                        break

            df_data.append(
                {
                    "Resource": resource,
                    "Type": resource_type,
                    "Department": department,
                    "Project": project["name"],
                    "Start": pd.to_datetime(project["start_date"]),
                    "Finish": pd.to_datetime(project["end_date"]),
                    "Priority": project["priority"],
                    "Duration": (
                        pd.to_datetime(project["end_date"])
                        - pd.to_datetime(project["start_date"])
                    ).days
                    + 1,
                }
            )

    return pd.DataFrame(df_data)


# NEW: Calculate resource utilization metrics
def calculate_resource_utilization(gantt_data, start_date=None, end_date=None):
    if gantt_data.empty:
        return pd.DataFrame()

    # If no date range provided, use the min and max dates from data
    if start_date is None:
        start_date = gantt_data["Start"].min()
    if end_date is None:
        end_date = gantt_data["Finish"].max()

    # Convert to pandas datetime if they are Python datetime
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

    # Calculate total period days with safeguard
    total_period_days = max(
        1, (end_date - start_date).days + 1
    )  # Avoid division by zero

    # Calculate utilization for each resource
    resource_utilization = []

    for resource in gantt_data["Resource"].unique():
        resource_df = gantt_data[gantt_data["Resource"] == resource]

        # Safeguard against empty dataframes
        if resource_df.empty:
            continue

        resource_type = resource_df["Type"].iloc[0]
        department = resource_df["Department"].iloc[0]

        # Calculate utilization days and overlaps
        date_range = pd.date_range(start=start_date, end=end_date)
        resource_dates = pd.DataFrame(0, index=date_range, columns=["count"])

        for _, row in resource_df.iterrows():
            project_start = max(row["Start"], start_date)
            project_end = min(row["Finish"], end_date)

            project_dates = pd.date_range(start=project_start, end=project_end)
            for date in project_dates:
                if date in resource_dates.index:
                    resource_dates.loc[date, "count"] += 1

        # Count days with at least one project
        days_utilized = (resource_dates["count"] > 0).sum()

        # Count days with overlapping projects
        days_overallocated = (resource_dates["count"] > 1).sum()

        # Calculate metrics with safeguards
        utilization_percentage = (days_utilized / total_period_days) * 100
        overallocation_percentage = (
            (days_overallocated / total_period_days) * 100 if days_utilized > 0 else 0
        )

        resource_utilization.append(
            {
                "Resource": resource,
                "Type": resource_type,
                "Department": department,
                "Days Utilized": days_utilized,
                "Total Period Days": total_period_days,
                "Utilization %": utilization_percentage,
                "Days Overallocated": days_overallocated,
                "Overallocation %": overallocation_percentage,
                "Projects": len(resource_df),
            }
        )

    return pd.DataFrame(resource_utilization)


# NEW: Enhance data tables with search, sort, and pagination
def filter_dataframe(df, key, columns=None):
    if columns is None:
        columns = df.columns

    with st.expander(f"Search and Filter {key}", expanded=False):
        search_term = st.text_input(f"Search {key}", key=f"search_{key}")

        # Create filter for each column
        col_filters = st.columns(min(4, len(columns)))
        active_filters = {}

        for i, col in enumerate(columns):
            with col_filters[i % 4]:
                if df[col].dtype == "object" or df[col].dtype == "string":
                    # Handle None values properly before sorting
                    unique_values = list(df[col].unique())
                    # Filter out None values, sort the rest, then add None back if it existed
                    non_none_values = [val for val in unique_values if val is not None]
                    sorted_values = sorted(non_none_values)
                    if None in unique_values:
                        sorted_values = [None] + sorted_values

                    if (
                        len(sorted_values) < 15
                    ):  # Only show multiselect for reasonable number of options
                        selected = st.multiselect(
                            f"Filter {col}",
                            options=sorted_values,
                            format_func=lambda x: "None" if x is None else x,
                            default=[],
                            key=f"filter_{key}_{col}",
                        )
                        if selected:
                            active_filters[col] = selected

        # Apply search term across all columns with safer string conversion
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

        # Apply column filters
        for col, values in active_filters.items():
            df = df[df[col].isin(values)]

        # Sorting with proper NaN handling
        if not df.empty:
            sort_options = ["None"] + list(df.columns)
            sort_col = st.selectbox(f"Sort by", options=sort_options, key=f"sort_{key}")
            if sort_col != "None":
                ascending = st.checkbox("Ascending", True, key=f"asc_{key}")
                df = df.sort_values(
                    by=sort_col, ascending=ascending, na_position="first"
                )

        # Pagination
        if len(df) > 20:
            page_size = st.slider(
                "Rows per page",
                min_value=10,
                max_value=100,
                value=20,
                step=10,
                key=f"page_size_{key}",
            )
            total_pages = math.ceil(len(df) / page_size)
            page_num = st.number_input(
                "Page",
                min_value=1,
                max_value=total_pages,
                value=1,
                step=1,
                key=f"page_num_{key}",
            )
            start_idx = (page_num - 1) * page_size
            end_idx = min(start_idx + page_size, len(df))
            st.write(f"Showing {start_idx + 1} to {end_idx} of {len(df)} entries")
            df = df.iloc[start_idx:end_idx]

    return df


# Enhanced Gantt chart visualization with interactivity
def display_gantt_chart(df):
    if df.empty:
        st.warning("No data available to visualize.")
        return

    # Calculate utilization for coloring
    utilization_df = calculate_resource_utilization(df)

    # Create a mapping of resources to their utilization percentage for coloring
    utilization_map = {}
    overallocation_map = {}
    for _, row in utilization_df.iterrows():
        utilization_map[row["Resource"]] = row["Utilization %"]
        overallocation_map[row["Resource"]] = row["Overallocation %"]

    # Add utilization data to the dataframe
    df["Utilization %"] = df["Resource"].map(utilization_map)
    df["Overallocation %"] = df["Resource"].map(overallocation_map)

    # Enhanced hover data
    df["Duration (days)"] = (df["Finish"] - df["Start"]).dt.days + 1

    # Create the Gantt chart with enhanced hover data
    fig = px.timeline(
        df,
        x_start="Start",
        x_end="Finish",
        y="Resource",
        color="Project",
        hover_data=[
            "Type",
            "Department",
            "Priority",
            "Duration (days)",
            "Utilization %",
            "Overallocation %",
        ],
        labels={"Resource": "Resource Name"},
        height=600,
    )

    # Add a vertical line for today's date
    today = pd.Timestamp.now()
    fig.add_vline(x=today, line_width=2, line_dash="dash", line_color="gray")

    # Improve layout with rangeslider for zooming
    fig.update_layout(
        title="Resource Allocation Timeline",
        xaxis_title="Timeline",
        yaxis_title="Resources",
        legend_title="Projects",
        xaxis=dict(
            rangeselector=dict(
                buttons=list(
                    [
                        dict(count=1, label="1m", step="month", stepmode="backward"),
                        dict(count=3, label="3m", step="month", stepmode="backward"),
                        dict(count=6, label="6m", step="month", stepmode="backward"),
                        dict(count=1, label="YTD", step="year", stepmode="todate"),
                        dict(count=1, label="1y", step="year", stepmode="backward"),
                        dict(step="all"),
                    ]
                )
            ),
            rangeslider=dict(visible=True),
            type="date",
        ),
    )

    # Highlight overallocated resources
    for i, resource in enumerate(df["Resource"].unique()):
        overallocation = overallocation_map.get(resource, 0)
        if overallocation > 0:
            # Add a colored rectangle to highlight overallocated resources
            fig.add_shape(
                type="rect",
                x0=df["Start"].min(),
                x1=df["Finish"].max(),
                y0=i - 0.4,
                y1=i + 0.4,
                line=dict(color="rgba(255,0,0,0.1)", width=0),
                fillcolor="rgba(255,0,0,0.1)",
                layer="below",
            )

    st.plotly_chart(fig, use_container_width=True)

    # Add explanation for the visual indicators
    with st.expander("Chart Legend"):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Visual Indicators:**")
            st.markdown(
                "- Red background: Resources with overlapping project assignments"
            )
            st.markdown("- Dashed vertical line: Today's date")
        with col2:
            st.markdown("**Interactive Features:**")
            st.markdown("- Zoom: Use the range selector or slider at the bottom")
            st.markdown(
                "- Details: Hover over bars to see project and resource details"
            )
            st.markdown("- Pan: Click and drag on the timeline")


# Check for resource conflicts
def find_resource_conflicts(df):
    conflicts = []
    for resource in df["Resource"].unique():
        resource_df = df[df["Resource"] == resource]
        if len(resource_df) > 1:
            # Check for date overlaps
            for i, row1 in resource_df.iterrows():
                for j, row2 in resource_df.iterrows():
                    if i < j:  # Avoid comparing the same pair twice
                        if (row1["Start"] <= row2["Finish"]) and (
                            row1["Finish"] >= row2["Start"]
                        ):
                            conflicts.append(
                                {
                                    "resource": resource,
                                    "project1": row1["Project"],
                                    "project2": row2["Project"],
                                    "overlap_start": max(row1["Start"], row2["Start"]),
                                    "overlap_end": min(row1["Finish"], row2["Finish"]),
                                    "overlap_days": (
                                        min(row1["Finish"], row2["Finish"])
                                        - max(row1["Start"], row2["Start"])
                                    ).days
                                    + 1,
                                }
                            )
    return conflicts


# NEW: Create resource utilization dashboard
def display_utilization_dashboard(gantt_data, start_date=None, end_date=None):
    if gantt_data.empty:
        st.warning("No data available for utilization metrics.")
        return

    # Calculate utilization metrics
    utilization_df = calculate_resource_utilization(gantt_data, start_date, end_date)

    if utilization_df.empty:
        st.warning("No utilization data available for the selected period.")
        return

    # Display summary metrics
    st.subheader("Resource Utilization Summary")

    avg_utilization = utilization_df["Utilization %"].mean()
    avg_overallocation = utilization_df["Overallocation %"].mean()
    total_resources = len(utilization_df)
    overallocated_resources = (utilization_df["Overallocation %"] > 0).sum()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Average Utilization", f"{avg_utilization:.1f}%")
    col2.metric(
        "Overallocated Resources", f"{overallocated_resources}/{total_resources}"
    )
    col3.metric("Average Overallocation", f"{avg_overallocation:.1f}%")
    col4.metric("Total Resources", total_resources)

    # Add utilization charts
    st.subheader("Resource Utilization Breakdown")

    # Sort utilization data for better visualization
    utilization_df = utilization_df.sort_values(by="Utilization %", ascending=False)

    # Display utilization by resource type
    col1, col2 = st.columns(2)

    with col1:
        # Utilization by Resource Type
        type_util = utilization_df.groupby("Type")["Utilization %"].mean().reset_index()
        fig = px.bar(
            type_util,
            x="Type",
            y="Utilization %",
            color="Type",
            title="Average Utilization by Resource Type",
            labels={"Utilization %": "Utilization Percentage (%)"},
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Utilization by Department
        dept_util = (
            utilization_df.groupby("Department")["Utilization %"].mean().reset_index()
        )
        fig = px.bar(
            dept_util,
            x="Department",
            y="Utilization %",
            color="Department",
            title="Average Utilization by Department",
            labels={"Utilization %": "Utilization Percentage (%)"},
        )
        st.plotly_chart(fig, use_container_width=True)

    # Display resource utilization heatmap
    st.subheader("Resource Utilization Heatmap")

    # Prepare data for heatmap - top 20 resources by utilization
    top_resources = utilization_df.head(20)

    # Create heatmap data
    heatmap_data = pd.DataFrame(
        {
            "Resource": top_resources["Resource"],
            "Utilization": top_resources["Utilization %"],
            "Overallocation": top_resources["Overallocation %"],
        }
    )

    # Create a wide-format dataframe for the heatmap
    heatmap_wide = pd.DataFrame()
    heatmap_wide["Resource"] = heatmap_data["Resource"]
    heatmap_wide["Utilization %"] = heatmap_data["Utilization"]
    heatmap_wide["Overallocation %"] = heatmap_data["Overallocation"]

    # Create heatmap
    fig = go.Figure()

    fig.add_trace(
        go.Heatmap(
            z=heatmap_wide[["Utilization %", "Overallocation %"]].values.T,
            x=heatmap_wide["Resource"],
            y=["Utilization %", "Overallocation %"],
            colorscale="YlOrRd",
            showscale=True,
            hoverongaps=False,
            text=[
                [f"Utilization: {val:.1f}%" for val in heatmap_wide["Utilization %"]],
                [
                    f"Overallocation: {val:.1f}%"
                    for val in heatmap_wide["Overallocation %"]
                ],
            ],
            hoverinfo="text+x+y",
        )
    )

    fig.update_layout(
        title="Resource Utilization and Overallocation Heatmap",
        xaxis_title="Resource",
        yaxis_title="Metric",
        height=400,
    )

    st.plotly_chart(fig, use_container_width=True)

    # Display detailed utilization table
    st.subheader("Detailed Resource Utilization")

    # Format the utilization dataframe for display
    display_df = utilization_df.copy()
    display_df["Utilization %"] = display_df["Utilization %"].round(1).astype(str) + "%"
    display_df["Overallocation %"] = (
        display_df["Overallocation %"].round(1).astype(str) + "%"
    )

    # Apply search and filtering
    filtered_df = filter_dataframe(
        display_df,
        "utilization",
        [
            "Resource",
            "Type",
            "Department",
            "Projects",
            "Utilization %",
            "Overallocation %",
        ],
    )

    st.dataframe(filtered_df, use_container_width=True)


# Main application
def main():
    st.title("Resource Management App")

    # Navigation sidebar
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox(
        "Select Page",
        [
            "Home",
            "Manage Resources",
            "Manage Projects",
            "Visualize Data",
            "Resource Utilization",  # New page for utilization metrics
            "Import/Export Data",
        ],
    )

    # Home page
    if page == "Home":
        st.header("Project Resource Management")
        st.write("""
        Welcome to the Resource Management App. This application helps you manage project resources 
        and visualize their allocation across multiple projects.
        
        Use the sidebar to navigate through different sections of the app.
        """)

        # Display resource summary
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("People", len(st.session_state.data["people"]))
        with col2:
            st.metric("Teams", len(st.session_state.data["teams"]))
        with col3:
            st.metric("Departments", len(st.session_state.data["departments"]))
        with col4:
            st.metric("Projects", len(st.session_state.data["projects"]))

        # Add overview visualization to home page
        if st.session_state.data["projects"]:
            st.subheader("Project Timeline Overview")

            # Create a simplified Gantt chart for the home page
            projects_df = pd.DataFrame(
                [
                    {
                        "Project": p["name"],
                        "Start": pd.to_datetime(p["start_date"]),
                        "Finish": pd.to_datetime(p["end_date"]),
                        "Priority": p["priority"],
                        "Resources": len(p["assigned_resources"]),
                    }
                    for p in st.session_state.data["projects"]
                ]
            )

            fig = px.timeline(
                projects_df,
                x_start="Start",
                x_end="Finish",
                y="Project",
                color="Priority",
                hover_data=["Resources"],
                color_continuous_scale="Viridis_r",  # Lower numbers (higher priority) are darker
                title="Project Timeline",
            )

            # Add today marker
            today = pd.Timestamp.now()
            fig.add_vline(x=today, line_width=1, line_dash="dash", line_color="red")

            st.plotly_chart(fig, use_container_width=True)

    # Manage Resources page
    elif page == "Manage Resources":
        resource_type = st.radio(
            "Select resource type", ["People", "Teams", "Departments"]
        )

        if resource_type == "People":
            st.subheader("Manage People")

            # Display existing people with enhanced filtering
            if st.session_state.data["people"]:
                people_df = pd.DataFrame(st.session_state.data["people"])
                # Apply filtering and sorting
                filtered_people_df = filter_dataframe(people_df, "people")
                st.dataframe(filtered_people_df, use_container_width=True)

            # Add new person form
            with st.form("add_person_form"):
                st.write("Add new person")
                name = st.text_input("Name")

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
                role = st.selectbox("Role", roles)
                if role == "Other":
                    role = st.text_input("Specify role")

                # Select or create department
                if st.session_state.data["departments"]:
                    dept_options = [
                        d["name"] for d in st.session_state.data["departments"]
                    ]
                    department = st.selectbox("Department", dept_options)
                else:
                    department = st.text_input("Department")

                # Select team (optional)
                team_options = ["None"]
                if st.session_state.data["teams"]:
                    for team in st.session_state.data["teams"]:
                        if team["department"] == department:
                            team_options.append(team["name"])

                team = st.selectbox("Team (optional)", team_options)
                if team == "None":
                    team = None

                submit = st.form_submit_button("Add Person")

                if submit and name and role and department:
                    # Add department if it doesn't exist
                    if not any(
                        d["name"] == department
                        for d in st.session_state.data["departments"]
                    ):
                        st.session_state.data["departments"].append(
                            {"name": department, "teams": [], "members": []}
                        )

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

            # Edit Person functionality
            if st.session_state.data["people"]:
                st.subheader("Edit Person")
                person_to_edit = st.selectbox(
                    "Select person to edit",
                    [p["name"] for p in st.session_state.data["people"]],
                )

                # Get current data for the selected person
                selected_person = next(
                    (
                        p
                        for p in st.session_state.data["people"]
                        if p["name"] == person_to_edit
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
                            current_team_index = team_options.index(
                                selected_person["team"]
                            )

                        new_team = st.selectbox(
                            "Team (optional)", team_options, index=current_team_index
                        )
                        if new_team == "None":
                            new_team = None

                        update_button = st.form_submit_button("Update Person")

                        if update_button:
                            # Update person info and related references
                            for i, person in enumerate(st.session_state.data["people"]):
                                if person["name"] == person_to_edit:
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
                                    }

                                    st.success(
                                        f"Updated {person_to_edit} to {new_name}"
                                    )
                                    st.rerun()

            # Delete Person functionality
            if st.session_state.data["people"]:
                st.subheader("Delete Person")
                delete_person = st.selectbox(
                    "Select person to delete",
                    [p["name"] for p in st.session_state.data["people"]],
                    key="delete_person",
                )

                if st.button(f"Delete {delete_person}"):
                    # Check if person can be deleted (not the only member of a team)
                    can_delete = True
                    message = ""

                    # Find teams the person belongs to
                    for team in st.session_state.data["teams"]:
                        if (
                            delete_person in team["members"]
                            and len(team["members"]) <= 2
                        ):
                            can_delete = False
                            message = f"Cannot delete {delete_person} - they are essential to team {team['name']} (team would have fewer than 2 members)"
                            break

                    if can_delete:
                        # Get person data before removal
                        person_data = next(
                            (
                                p
                                for p in st.session_state.data["people"]
                                if p["name"] == delete_person
                            ),
                            None,
                        )

                        if person_data:
                            # Remove from team if assigned
                            if person_data["team"]:
                                for team in st.session_state.data["teams"]:
                                    if (
                                        team["name"] == person_data["team"]
                                        and delete_person in team["members"]
                                    ):
                                        team["members"].remove(delete_person)

                            # Remove from department
                            for dept in st.session_state.data["departments"]:
                                if (
                                    dept["name"] == person_data["department"]
                                    and delete_person in dept["members"]
                                ):
                                    dept["members"].remove(delete_person)

                            # Remove from projects
                            for project in st.session_state.data["projects"]:
                                if delete_person in project["assigned_resources"]:
                                    project["assigned_resources"].remove(delete_person)

                            # Remove the person
                            st.session_state.data["people"] = [
                                p
                                for p in st.session_state.data["people"]
                                if p["name"] != delete_person
                            ]

                            st.success(f"Deleted {delete_person}")
                            st.rerun()
                    else:
                        st.error(message)

        elif resource_type == "Teams":
            st.subheader("Manage Teams")

            # Display existing teams with enhanced table
            if st.session_state.data["teams"]:
                teams_data = []
                for team in st.session_state.data["teams"]:
                    teams_data.append(
                        {
                            "Name": team["name"],
                            "Department": team["department"],
                            "Members": ", ".join(team["members"])
                            if team["members"]
                            else "None",
                            "Member Count": len(team["members"]),
                        }
                    )
                teams_df = pd.DataFrame(teams_data)

                # Apply filtering and sorting
                filtered_teams_df = filter_dataframe(teams_df, "teams")
                st.dataframe(filtered_teams_df, use_container_width=True)

            # Add new team form
            with st.form("add_team_form"):
                st.write("Add new team")
                name = st.text_input("Team Name")

                # Select or create department
                if st.session_state.data["departments"]:
                    dept_options = [
                        d["name"] for d in st.session_state.data["departments"]
                    ]
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
                    if len(members) < 2:
                        st.error("A team must have at least 2 members.")
                    else:
                        # Add department if it doesn't exist
                        if not any(
                            d["name"] == department
                            for d in st.session_state.data["departments"]
                        ):
                            st.session_state.data["departments"].append(
                                {"name": department, "teams": [], "members": []}
                            )

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

            # Edit Team functionality
            if st.session_state.data["teams"]:
                st.subheader("Edit Team")
                team_to_edit = st.selectbox(
                    "Select team to edit",
                    [t["name"] for t in st.session_state.data["teams"]],
                )

                # Get current data for the selected team
                selected_team = next(
                    (
                        t
                        for t in st.session_state.data["teams"]
                        if t["name"] == team_to_edit
                    ),
                    None,
                )

                if selected_team:
                    with st.form("edit_team_form"):
                        new_name = st.text_input(
                            "Team Name", value=selected_team["name"]
                        )

                        # Select department
                        dept_options = [
                            d["name"] for d in st.session_state.data["departments"]
                        ]
                        dept_index = (
                            dept_options.index(selected_team["department"])
                            if selected_team["department"] in dept_options
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
                            m for m in selected_team["members"] if m in member_options
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
                                for i, team in enumerate(
                                    st.session_state.data["teams"]
                                ):
                                    if team["name"] == team_to_edit:
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

                                        st.success(
                                            f"Updated {team_to_edit} to {new_name}"
                                        )
                                        st.rerun()

            # Delete Team functionality
            if st.session_state.data["teams"]:
                st.subheader("Delete Team")
                delete_team = st.selectbox(
                    "Select team to delete",
                    [t["name"] for t in st.session_state.data["teams"]],
                    key="delete_team",
                )

                if st.button(f"Delete {delete_team}"):
                    # Get team data before removal
                    team_data = next(
                        (
                            t
                            for t in st.session_state.data["teams"]
                            if t["name"] == delete_team
                        ),
                        None,
                    )

                    if team_data:
                        # Update people who were in this team
                        for person in st.session_state.data["people"]:
                            if person["team"] == delete_team:
                                person["team"] = None

                        # Remove from department
                        for dept in st.session_state.data["departments"]:
                            if (
                                dept["name"] == team_data["department"]
                                and delete_team in dept["teams"]
                            ):
                                dept["teams"].remove(delete_team)

                        # Remove from projects
                        for project in st.session_state.data["projects"]:
                            if delete_team in project["assigned_resources"]:
                                project["assigned_resources"].remove(delete_team)

                        # Remove the team
                        st.session_state.data["teams"] = [
                            t
                            for t in st.session_state.data["teams"]
                            if t["name"] != delete_team
                        ]

                        st.success(f"Deleted {delete_team}")
                        st.rerun()

        elif resource_type == "Departments":
            st.subheader("Manage Departments")

            # Display existing departments with enhanced table
            if st.session_state.data["departments"]:
                dept_data = []
                for dept in st.session_state.data["departments"]:
                    dept_data.append(
                        {
                            "Name": dept["name"],
                            "Teams": len(dept["teams"]),
                            "Members": len(dept["members"]),
                            "Team Names": ", ".join(dept["teams"])
                            if dept["teams"]
                            else "None",
                        }
                    )
                dept_df = pd.DataFrame(dept_data)

                # Apply filtering and sorting
                filtered_dept_df = filter_dataframe(dept_df, "departments")
                st.dataframe(filtered_dept_df, use_container_width=True)

            # Add new department form
            with st.form("add_department_form"):
                st.write("Add new department")
                name = st.text_input("Department Name")
                submit = st.form_submit_button("Add Department")

                if submit and name:
                    # Check if department already exists
                    if any(
                        d["name"] == name for d in st.session_state.data["departments"]
                    ):
                        st.error(f"Department {name} already exists.")
                    else:
                        # Add department
                        st.session_state.data["departments"].append(
                            {"name": name, "teams": [], "members": []}
                        )
                        st.success(f"Added department {name}")
                        st.rerun()

            # Edit Department functionality
            if st.session_state.data["departments"]:
                st.subheader("Edit Department")
                dept_to_edit = st.selectbox(
                    "Select department to edit",
                    [d["name"] for d in st.session_state.data["departments"]],
                )

                # Get current data for the selected department
                selected_dept = next(
                    (
                        d
                        for d in st.session_state.data["departments"]
                        if d["name"] == dept_to_edit
                    ),
                    None,
                )

                if selected_dept:
                    with st.form("edit_department_form"):
                        new_name = st.text_input(
                            "Department Name", value=selected_dept["name"]
                        )

                        update_button = st.form_submit_button("Update Department")

                        if update_button:
                            # Update department info and related references
                            for i, dept in enumerate(
                                st.session_state.data["departments"]
                            ):
                                if dept["name"] == dept_to_edit:
                                    # Update teams that belong to this department
                                    for team in st.session_state.data["teams"]:
                                        if team["department"] == dept_to_edit:
                                            team["department"] = new_name

                                    # Update people that belong to this department
                                    for person in st.session_state.data["people"]:
                                        if person["department"] == dept_to_edit:
                                            person["department"] = new_name

                                    # Update department record
                                    st.session_state.data["departments"][i]["name"] = (
                                        new_name
                                    )

                                    st.success(f"Updated {dept_to_edit} to {new_name}")
                                    st.rerun()

            # Delete Department functionality
            if (
                st.session_state.data["departments"]
                and len(st.session_state.data["departments"]) > 1
            ):
                st.subheader("Delete Department")
                delete_dept = st.selectbox(
                    "Select department to delete",
                    [d["name"] for d in st.session_state.data["departments"]],
                    key="delete_dept",
                )

                if st.button(f"Delete {delete_dept}"):
                    # Check if department can be deleted (not the only department)
                    if len(st.session_state.data["departments"]) <= 1:
                        st.error(
                            "Cannot delete the only department. Create another department first."
                        )
                    else:
                        # Get department data before removal
                        dept_data = next(
                            (
                                d
                                for d in st.session_state.data["departments"]
                                if d["name"] == delete_dept
                            ),
                            None,
                        )

                        if dept_data:
                            # Check if department has people or teams
                            if dept_data["members"] or dept_data["teams"]:
                                st.error(
                                    f"Cannot delete department '{delete_dept}' because it still has people or teams assigned. Reassign them first."
                                )
                            else:
                                # Remove from projects
                                for project in st.session_state.data["projects"]:
                                    if delete_dept in project["assigned_resources"]:
                                        project["assigned_resources"].remove(
                                            delete_dept
                                        )

                                # Remove the department
                                st.session_state.data["departments"] = [
                                    d
                                    for d in st.session_state.data["departments"]
                                    if d["name"] != delete_dept
                                ]

                                st.success(f"Deleted {delete_dept}")
                                st.rerun()

    # Manage Projects page
    elif page == "Manage Projects":
        st.subheader("Manage Projects")

        # Display existing projects with enhanced table
        if st.session_state.data["projects"]:
            projects_df = pd.DataFrame(
                [
                    {
                        "Name": p["name"],
                        "Start Date": p["start_date"],
                        "End Date": p["end_date"],
                        "Priority": p["priority"],
                        "Resources": len(p["assigned_resources"]),
                        "Duration (days)": (
                            pd.to_datetime(p["end_date"])
                            - pd.to_datetime(p["start_date"])
                        ).days
                        + 1,
                        "Assigned Resources": ", ".join(p["assigned_resources"]),
                    }
                    for p in st.session_state.data["projects"]
                ]
            )

            # Apply filtering and sorting
            filtered_projects_df = filter_dataframe(projects_df, "projects")
            st.dataframe(filtered_projects_df, use_container_width=True)

        # Add new project form
        with st.form("add_project_form"):
            st.write("Add new project")
            name = st.text_input("Project Name")

            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Start Date")
            with col2:
                end_date = st.date_input("End Date")

            priority = st.number_input(
                "Priority (lower = higher priority)", min_value=1, value=1, step=1
            )

            # Resource assignment
            resource_type = st.radio(
                "Assign resources by", ["People", "Teams", "Departments"]
            )

            if resource_type == "People":
                resource_options = [p["name"] for p in st.session_state.data["people"]]
            elif resource_type == "Teams":
                resource_options = [t["name"] for t in st.session_state.data["teams"]]
            else:  # Departments
                resource_options = [
                    d["name"] for d in st.session_state.data["departments"]
                ]

            assigned_resources = st.multiselect("Assign Resources", resource_options)

            submit = st.form_submit_button("Add Project")

            if submit and name and start_date and end_date:
                if start_date > end_date:
                    st.error("End date must be after start date.")
                else:
                    # Add project
                    st.session_state.data["projects"].append(
                        {
                            "name": name,
                            "start_date": start_date.strftime("%Y-%m-%d"),
                            "end_date": end_date.strftime("%Y-%m-%d"),
                            "priority": priority,
                            "assigned_resources": assigned_resources,
                        }
                    )
                    st.success(f"Added project {name}")
                    st.rerun()

        # Edit Project functionality
        if st.session_state.data["projects"]:
            st.subheader("Edit Project")
            project_to_edit = st.selectbox(
                "Select project to edit",
                [p["name"] for p in st.session_state.data["projects"]],
            )

            # Get current data for the selected project
            selected_project = next(
                (
                    p
                    for p in st.session_state.data["projects"]
                    if p["name"] == project_to_edit
                ),
                None,
            )

            if selected_project:
                with st.form("edit_project_form"):
                    new_name = st.text_input(
                        "Project Name", value=selected_project["name"]
                    )

                    col1, col2 = st.columns(2)
                    with col1:
                        start_date = st.date_input(
                            "Start Date",
                            value=pd.to_datetime(selected_project["start_date"]).date(),
                        )
                    with col2:
                        end_date = st.date_input(
                            "End Date",
                            value=pd.to_datetime(selected_project["end_date"]).date(),
                        )

                    priority = st.number_input(
                        "Priority (lower = higher priority)",
                        min_value=1,
                        value=selected_project["priority"],
                        step=1,
                    )

                    # Resource assignment
                    resource_type = st.radio(
                        "Manage resources by", ["People", "Teams", "Departments"]
                    )

                    if resource_type == "People":
                        resource_options = [
                            p["name"] for p in st.session_state.data["people"]
                        ]
                    elif resource_type == "Teams":
                        resource_options = [
                            t["name"] for t in st.session_state.data["teams"]
                        ]
                    else:  # Departments
                        resource_options = [
                            d["name"] for d in st.session_state.data["departments"]
                        ]

                    # Filter assigned resources by type
                    current_resources = []
                    for resource in selected_project["assigned_resources"]:
                        if resource_type == "People" and any(
                            p["name"] == resource
                            for p in st.session_state.data["people"]
                        ):
                            current_resources.append(resource)
                        elif resource_type == "Teams" and any(
                            t["name"] == resource
                            for t in st.session_state.data["teams"]
                        ):
                            current_resources.append(resource)
                        elif resource_type == "Departments" and any(
                            d["name"] == resource
                            for d in st.session_state.data["departments"]
                        ):
                            current_resources.append(resource)

                    new_resources = st.multiselect(
                        f"Assign {resource_type}",
                        resource_options,
                        default=current_resources,
                    )

                    update_button = st.form_submit_button("Update Project")

                    if update_button:
                        if start_date > end_date:
                            st.error("End date must be after start date.")
                        else:
                            # Update project info
                            for i, project in enumerate(
                                st.session_state.data["projects"]
                            ):
                                if project["name"] == project_to_edit:
                                    # Get old resources that should be kept (from different types)
                                    preserved_resources = []
                                    for resource in project["assigned_resources"]:
                                        keep = False
                                        if resource_type == "People":
                                            # Keep if it's not a person (i.e., is a team or department)
                                            keep = not any(
                                                p["name"] == resource
                                                for p in st.session_state.data["people"]
                                            )
                                        elif resource_type == "Teams":
                                            # Keep if it's not a team (i.e., is a person or department)
                                            keep = not any(
                                                t["name"] == resource
                                                for t in st.session_state.data["teams"]
                                            )
                                        else:  # Departments
                                            # Keep if it's not a department (i.e., is a person or team)
                                            keep = not any(
                                                d["name"] == resource
                                                for d in st.session_state.data[
                                                    "departments"
                                                ]
                                            )

                                        if keep:
                                            preserved_resources.append(resource)

                                    # Combine preserved resources with newly assigned ones
                                    updated_resources = (
                                        preserved_resources + new_resources
                                    )

                                    # Update project record
                                    st.session_state.data["projects"][i] = {
                                        "name": new_name,
                                        "start_date": start_date.strftime("%Y-%m-%d"),
                                        "end_date": end_date.strftime("%Y-%m-%d"),
                                        "priority": priority,
                                        "assigned_resources": updated_resources,
                                    }

                                    st.success(
                                        f"Updated project {project_to_edit} to {new_name}"
                                    )
                                    st.rerun()

        # Delete Project functionality
        if st.session_state.data["projects"]:
            st.subheader("Delete Project")
            delete_project = st.selectbox(
                "Select project to delete",
                [p["name"] for p in st.session_state.data["projects"]],
                key="delete_project",
            )

            if st.button(f"Delete {delete_project}"):
                # Remove the project
                st.session_state.data["projects"] = [
                    p
                    for p in st.session_state.data["projects"]
                    if p["name"] != delete_project
                ]

                st.success(f"Deleted project {delete_project}")
                st.rerun()

    # Visualize Data page
    elif page == "Visualize Data":
        st.subheader("Resource Allocation Visualization")

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
            # Add Resource Filtering to Visualization
            st.subheader("Filter Options")

            col1, col2, col3 = st.columns(3)

            with col1:
                # Department filter
                dept_filter = st.multiselect(
                    "Filter by Department",
                    options=[d["name"] for d in st.session_state.data["departments"]],
                    default=[d["name"] for d in st.session_state.data["departments"]],
                )

            with col2:
                # Resource type filter
                resource_type_filter = st.multiselect(
                    "Filter by Resource Type",
                    options=["Person", "Team", "Department"],
                    default=["Person", "Team", "Department"],
                )

            with col3:
                # Date range filter
                min_date = min(
                    [
                        pd.to_datetime(p["start_date"])
                        for p in st.session_state.data["projects"]
                    ]
                )
                max_date = max(
                    [
                        pd.to_datetime(p["end_date"])
                        for p in st.session_state.data["projects"]
                    ]
                )

                date_range = st.date_input(
                    "Date Range",
                    value=(min_date.date(), max_date.date()),
                    min_value=min_date.date(),
                    max_value=max_date.date(),
                )

            # Add project filter
            project_filter = st.multiselect(
                "Filter by Project",
                options=[p["name"] for p in st.session_state.data["projects"]],
                default=[p["name"] for p in st.session_state.data["projects"]],
            )

            # Create visualization data
            gantt_data = create_gantt_data(
                st.session_state.data["projects"], st.session_state.data
            )

            # Apply filters
            if dept_filter:
                gantt_data = gantt_data[gantt_data["Department"].isin(dept_filter)]

            if resource_type_filter:
                gantt_data = gantt_data[gantt_data["Type"].isin(resource_type_filter)]

            if project_filter:
                gantt_data = gantt_data[gantt_data["Project"].isin(project_filter)]

            if len(date_range) == 2:
                start_date, end_date = date_range
                start_date = pd.to_datetime(start_date)
                end_date = pd.to_datetime(end_date)

                # Filter by date overlap (any project that overlaps with the range)
                gantt_data = gantt_data[
                    (
                        (gantt_data["Start"] <= end_date)
                        & (gantt_data["Finish"] >= start_date)
                    )
                ]

            # Display enhanced Gantt chart
            display_gantt_chart(gantt_data)

            # Check for resource conflicts
            conflicts = find_resource_conflicts(gantt_data)
            if conflicts:
                st.subheader("Resource Conflicts")
                st.warning(f"{len(conflicts)} resource conflicts detected")

                # Create conflicts dataframe for better display
                conflicts_df = pd.DataFrame(conflicts)
                conflicts_df["overlap_start"] = pd.to_datetime(
                    conflicts_df["overlap_start"]
                )
                conflicts_df["overlap_end"] = pd.to_datetime(
                    conflicts_df["overlap_end"]
                )

                # Format for display
                conflicts_display = conflicts_df.copy()
                conflicts_display["overlap_period"] = conflicts_display.apply(
                    lambda x: f"{x['overlap_start'].strftime('%Y-%m-%d')} to {x['overlap_end'].strftime('%Y-%m-%d')}",
                    axis=1,
                )
                conflicts_display["projects"] = conflicts_display.apply(
                    lambda x: f"{x['project1']} and {x['project2']}", axis=1
                )

                # Display as a filterable table
                filtered_conflicts = filter_dataframe(
                    conflicts_display[
                        ["resource", "projects", "overlap_period", "overlap_days"]
                    ],
                    "conflicts",
                    ["resource", "projects", "overlap_period", "overlap_days"],
                )
                st.dataframe(filtered_conflicts, use_container_width=True)
            else:
                st.success("No resource conflicts detected")

            # Drill-down view for resources
            st.subheader("Resource Drill-Down")

            # Select resource to drill down
            if not gantt_data.empty:
                drill_down_options = ["None"] + list(gantt_data["Resource"].unique())
                resource_to_drill = st.selectbox(
                    "Select resource for details", options=drill_down_options
                )

                if resource_to_drill != "None":
                    # Filter data for selected resource
                    resource_data = gantt_data[
                        gantt_data["Resource"] == resource_to_drill
                    ]

                    # Create resource card
                    col1, col2 = st.columns([1, 2])

                    with col1:
                        st.markdown(f"**Resource:** {resource_to_drill}")
                        st.markdown(f"**Type:** {resource_data['Type'].iloc[0]}")
                        st.markdown(
                            f"**Department:** {resource_data['Department'].iloc[0]}"
                        )

                        # Calculate utilization for this resource
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
                        # Create mini Gantt chart for this resource
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

                    # Show project details
                    st.markdown("**Project Assignments:**")

                    # Format the data for display
                    projects_data = resource_data.copy()
                    projects_data["Duration (days)"] = (
                        projects_data["Finish"] - projects_data["Start"]
                    ).dt.days + 1
                    projects_data["Start"] = projects_data["Start"].dt.strftime(
                        "%Y-%m-%d"
                    )
                    projects_data["Finish"] = projects_data["Finish"].dt.strftime(
                        "%Y-%m-%d"
                    )

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

    # NEW: Resource Utilization page
    elif page == "Resource Utilization":
        st.header("Resource Utilization Dashboard")

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
                [
                    pd.to_datetime(p["start_date"])
                    for p in st.session_state.data["projects"]
                ]
            )
            max_date = max(
                [
                    pd.to_datetime(p["end_date"])
                    for p in st.session_state.data["projects"]
                ]
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

    # Import/Export Data page
    elif page == "Import/Export Data":
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


# Run the application
if __name__ == "__main__":
    main()
