import streamlit as st
import pandas as pd
import plotly.express as px
import json

from data_handlers import (
    load_json,
    save_json,
    create_gantt_data,
    calculate_resource_utilization,
    filter_dataframe,
    find_resource_conflicts,
    parse_resources,  # Corrected import
)
from visualizations import display_gantt_chart, display_utilization_dashboard
from resource_forms import (
    person_crud_form,
    team_crud_form,
    department_crud_form,
    add_project_form,
    edit_project_form,
)
from utils import display_filtered_resource

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
    """
    Displays the content for the Home tab.
    """
    st.subheader("Home")
    # Introduction section
    st.subheader("Introduction")
    st.write("""
    This application helps you manage project resources and visualize
    their allocation across multiple projects.

    Use the sidebar to navigate through different sections of the app.
    """)

    # Resource summary section
    st.subheader("Resource Summary")
    st.markdown(
        "Below is the total number of each resource type currently available in the system:"
    )

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

    # Project timeline section
    st.subheader("Project Timeline Overview")
    st.write(
        "A snapshot of ongoing projects, their priorities, and assigned resources."
    )

    # Add overview visualization to home page
    if st.session_state.data["projects"]:
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
        # Mark duplicate priorities
        projects_df["priority_count"] = projects_df.groupby("Priority")[
            "Priority"
        ].transform("count")
        projects_df["Priority Label"] = projects_df.apply(
            lambda row: f"Priority {row['Priority']} (Duplicate)"
            if row["priority_count"] > 1
            else f"Priority {row['Priority']}",
            axis=1,
        )

        fig = px.timeline(
            projects_df,
            x_start="Start",
            x_end="Finish",
            y="Project",
            color="Priority Label",
            hover_data=["Resources"],
            color_continuous_scale="Viridis_r",  # Lower numbers (higher priority) are darker
            title="Project Timeline",
        )

        # Add today marker
        today = pd.Timestamp.now()
        fig.add_vline(x=today, line_width=1, line_dash="dash", line_color="red")

        st.plotly_chart(fig, use_container_width=True)


def display_manage_resources_tab():
    """
    Displays the content for the Manage Resources tab.
    """
    st.subheader("Manage Resources")
    resource_type = st.radio("Select resource type", ["People", "Teams", "Departments"])

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


def display_manage_projects_tab():
    """
    Displays the content for the Manage Projects tab.
    """
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
                    "Duration (days)": (
                        pd.to_datetime(p["end_date"]) - pd.to_datetime(p["start_date"])
                    ).days
                    + 1,
                    # Split assigned resources
                    "Assigned People": ", ".join(
                        parse_resources(p["assigned_resources"])[0]
                    ),
                    "Assigned Teams": ", ".join(
                        parse_resources(p["assigned_resources"])[1]
                    ),
                    "Assigned Departments": ", ".join(
                        parse_resources(p["assigned_resources"])[2]
                    ),
                }
                for p in st.session_state.data["projects"]
            ]
        )

        # Add priority_count column and rename it to Priority
        projects_df["Priority"] = projects_df.groupby("Priority")["Priority"].transform(
            "count"
        )

        st.dataframe(projects_df, use_container_width=True)

    if "new_project_people" not in st.session_state:
        st.session_state["new_project_people"] = []
    if "new_project_teams" not in st.session_state:
        st.session_state["new_project_teams"] = []

    add_project_form()
    edit_project_form()

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


def display_visualize_data_tab():
    """
    Displays the content for the Visualize Data tab.
    """
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
            conflicts_df["overlap_end"] = pd.to_datetime(conflicts_df["overlap_end"])

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
                resource_data = gantt_data[gantt_data["Resource"] == resource_to_drill]

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
                projects_data["Start"] = projects_data["Start"].dt.strftime("%Y-%m-%d")
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


def main():
    """
    Orchestrates the Streamlit application flow.
    """
    st.title("Resource Management App")

    # Navigation tabs
    tabs = st.tabs(
        [
            "Home",
            "Manage Resources",
            "Manage Projects",
            "Visualize Data",
            "Resource Utilization",
            "Import/Export Data",
        ]
    )

    with tabs[0]:
        display_home_tab()

    with tabs[1]:
        display_manage_resources_tab()

    with tabs[2]:
        display_manage_projects_tab()

    with tabs[3]:
        display_visualize_data_tab()

    with tabs[4]:
        display_resource_utilization_tab()

    with tabs[5]:
        display_import_export_data_tab()


if __name__ == "__main__":
    main()
