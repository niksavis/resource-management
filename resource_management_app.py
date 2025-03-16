import streamlit as st
import pandas as pd
import plotly.express as px

from data_handlers import (
    load_json,
    save_json,
    create_gantt_data,
    calculate_resource_utilization,
    filter_dataframe,
    find_resource_conflicts,
)
from visualizations import display_gantt_chart, display_utilization_dashboard
from resource_forms import (
    person_crud_form,
    team_crud_form,
    department_crud_form,
)

# Set up basic page configuration
st.set_page_config(page_title="Resource Management App", layout="wide")

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


def display_filtered_resource(data_key: str, label: str):
    """
    Converts session data to a DataFrame, applies filter_dataframe,
    and displays the results.
    """
    data = st.session_state.data[data_key]
    if data:
        df = pd.DataFrame(data)
        filtered_df = filter_dataframe(df, data_key)
        st.dataframe(filtered_df, use_container_width=True)
    else:
        st.warning(f"No {label} found. Please add some first.")


# Main application
def main() -> None:
    """
    Orchestrates the Streamlit application flow.
    """
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
            display_filtered_resource("people", "people")
            person_crud_form()

        elif resource_type == "Teams":
            st.subheader("Manage Teams")
            display_filtered_resource("teams", "teams")
            team_crud_form()

        elif resource_type == "Departments":
            st.subheader("Manage Departments")
            display_filtered_resource("departments", "departments")
            department_crud_form()

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
