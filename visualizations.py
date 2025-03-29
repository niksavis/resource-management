import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from typing import List, Tuple

from configuration import manage_visualization_colors
from data_handlers import (
    calculate_resource_utilization,
    calculate_capacity_data,
    find_resource_conflicts,
    _determine_resource_type,
)


def display_gantt_chart(df: pd.DataFrame, projects_to_include=None) -> None:
    """
    Displays an interactive Gantt chart using Plotly with optional project filtering.
    """
    if df.empty:
        st.warning("No data available to visualize.")
        return

    # Prepare Gantt data with filtering support
    df_with_utilization = _prepare_gantt_data(df, projects_to_include)

    # Check if the DataFrame is empty or missing the Resource column
    if df_with_utilization.empty or "Resource" not in df_with_utilization.columns:
        st.warning("No data available to display after filtering.")
        return

    # Calculate utilization and overallocation
    for resource in df_with_utilization["Resource"].unique():
        resource_df = df_with_utilization[df_with_utilization["Resource"] == resource]
        min_date = resource_df["Start"].min()
        max_date = resource_df["Finish"].max()
        total_days = (max_date - min_date).days + 1
        utilization_percentage = (
            resource_df["Duration (Days)"].sum() / total_days
        ) * 100
        df_with_utilization.loc[
            df_with_utilization["Resource"] == resource, "Utilization %"
        ] = min(utilization_percentage, 100)
        df_with_utilization.loc[
            df_with_utilization["Resource"] == resource, "Overallocation %"
        ] = max(0, utilization_percentage - 100)

    department_colors = {
        dept: color.lower()
        for dept, color in manage_visualization_colors(
            df_with_utilization["Department"].unique()
        ).items()
    }

    fig = px.timeline(
        df_with_utilization,
        x_start="Start",
        x_end="Finish",
        y="Resource",
        color="Department",
        hover_data=[
            "Type",
            "Department",
            "Priority",
            "Duration (Days)",
            "Utilization %",
            "Overallocation %",
            "Cost",
        ],
        labels={"Resource": "Resource Name"},
        height=600,
        color_discrete_map=department_colors,
    )

    fig = _add_today_marker(fig)
    fig = _highlight_overallocated_resources(fig, df_with_utilization)
    st.plotly_chart(fig, use_container_width=True)
    _display_chart_legend()


def _prepare_gantt_data(df: pd.DataFrame, projects_to_include=None) -> pd.DataFrame:
    """Prepare data for Gantt chart visualization with filtering support."""
    gantt_data = []

    for project in st.session_state.data["projects"]:
        # Skip projects not in the filter list if provided AND non-empty
        if (
            projects_to_include is not None
            and len(projects_to_include) > 0  # Only apply filter if list has items
            and project["name"] not in projects_to_include
        ):
            continue

        project_name = project["name"]
        project_priority = project["priority"]

        # Get resource allocations
        resource_allocations = project.get("resource_allocations", [])

        # If no specific allocations, create default ones for all assigned resources
        if not resource_allocations:
            if "assigned_resources" not in project or not project["assigned_resources"]:
                st.warning(f"Project '{project_name}' has no assigned resources.")
                continue  # Skip projects with no assigned resources

            resource_allocations = [
                {
                    "resource": r,
                    "allocation_percentage": 100,
                    "start_date": project["start_date"],
                    "end_date": project["end_date"],
                }
                for r in project["assigned_resources"]
            ]

        # Add each resource allocation as a separate Gantt bar
        for allocation in resource_allocations:
            resource = allocation["resource"]
            r_type, department = _determine_resource_type(
                resource, st.session_state.data
            )

            start_date = pd.to_datetime(allocation["start_date"])
            end_date = pd.to_datetime(allocation["end_date"])
            duration_days = (end_date - start_date).days + 1

            # Calculate cost
            cost = 0.0
            if r_type == "Person":
                person = next(
                    (
                        p
                        for p in st.session_state.data["people"]
                        if p["name"] == resource
                    ),
                    None,
                )
                if person:
                    cost = person.get("daily_cost", 0) * duration_days
            elif r_type == "Team":
                team = next(
                    (
                        t
                        for t in st.session_state.data["teams"]
                        if t["name"] == resource
                    ),
                    None,
                )
                if team:
                    team_cost = sum(
                        p.get("daily_cost", 0)
                        for p in st.session_state.data["people"]
                        if p["name"] in team.get("members", [])
                    )
                    cost = team_cost * duration_days

            gantt_data.append(
                {
                    "Resource": resource,
                    "Type": r_type,
                    "Department": department,
                    "Project": project_name,
                    "Start": start_date,
                    "Finish": end_date,
                    "Priority": project_priority,
                    "Duration (Days)": duration_days,
                    "Allocation %": allocation["allocation_percentage"],
                    "Cost": cost,
                    "Utilization %": 0.0,
                    "Overallocation %": 0.0,
                }
            )

    # Return an empty DataFrame with the expected columns if no data
    if not gantt_data:
        st.warning("No valid data available for Gantt chart.")
        return pd.DataFrame(
            columns=[
                "Resource",
                "Type",
                "Department",
                "Project",
                "Start",
                "Finish",
                "Priority",
                "Duration (Days)",
                "Allocation %",
                "Cost",
                "Utilization %",
                "Overallocation %",
            ]
        )

    df = pd.DataFrame(gantt_data)

    # Calculate utilization and overallocation for each resource
    for resource in df["Resource"].unique():
        resource_df = df[df["Resource"] == resource]

        # Calculate total days in the period
        min_date = resource_df["Start"].min()
        max_date = resource_df["Finish"].max()
        total_days = (max_date - min_date).days + 1

        # Calculate utilization percentage
        utilization_percentage = (
            resource_df["Duration (Days)"].sum() / total_days
        ) * 100
        df.loc[df["Resource"] == resource, "Utilization %"] = min(
            utilization_percentage, 100
        )

        # Calculate overallocation percentage
        df.loc[df["Resource"] == resource, "Overallocation %"] = max(
            0, utilization_percentage - 100
        )

    return df


def _add_today_marker(fig: go.Figure) -> go.Figure:
    """Add a vertical line for today's date to the Gantt chart."""
    today = pd.Timestamp.now()
    fig.add_vline(x=today, line_width=2, line_dash="dash", line_color="gray")
    return fig


def _highlight_overallocated_resources(fig: go.Figure, df: pd.DataFrame) -> go.Figure:
    """Highlight overallocated resources in the Gantt chart."""
    overallocation_map = df.set_index("Resource")["Overallocation %"].to_dict()

    for i, resource in enumerate(df["Resource"].unique()):
        overallocation = overallocation_map.get(resource, 0)
        if overallocation > 0:  # Highlight only if Overallocation % > 0
            fig.add_shape(
                type="rect",
                x0=df[df["Resource"] == resource]["Start"].min(),
                x1=df[df["Resource"] == resource]["Finish"].max(),
                y0=i - 0.4,
                y1=i + 0.4,
                line=dict(color="rgba(255,0,0,0.1)", width=0),
                fillcolor="rgba(255,0,0,0.1)",
                layer="below",
            )
    return fig


def _display_chart_legend() -> None:
    """Display the legend for the Gantt chart."""
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


def display_utilization_dashboard(filtered_data: pd.DataFrame, start_date, end_date):
    """
    Displays a unified utilization dashboard using pre-filtered data.
    """
    if filtered_data.empty:
        st.warning("No data available for utilization metrics.")
        return

    # Use the filtered data directly instead of recalculating
    utilization_df = calculate_resource_utilization(filtered_data, start_date, end_date)

    # Display core metrics
    st.subheader("Performance Metrics")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Resources", len(utilization_df))
    col2.metric("Avg Utilization", f"{utilization_df['Utilization %'].mean():.1f}%")
    col3.metric(
        "Avg Overallocation", f"{utilization_df['Overallocation %'].mean():.1f}%"
    )

    # Single visualization section
    st.subheader("Resource Utilization Analysis")
    fig = px.bar(
        utilization_df,
        x="Resource",
        y=["Utilization %", "Overallocation %"],
        barmode="group",
        color="Type",
        labels={"value": "Percentage"},
        height=500,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Detailed table
    st.subheader("Detailed Metrics")
    st.dataframe(
        utilization_df,
        column_config={
            "Utilization %": st.column_config.ProgressColumn(
                "Utilization %", format="%.1f%%", min_value=0, max_value=100
            ),
            "Overallocation %": st.column_config.NumberColumn(
                "Overallocation %", format="%.1f%%"
            ),
        },
        use_container_width=True,
    )


def _display_resource_conflicts(gantt_data: pd.DataFrame) -> None:
    """
    Check and display resource conflicts using filtered Gantt data.
    """
    if gantt_data.empty:
        st.warning("No data available to check for resource conflicts.")
        return

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
            labels={"overlap_days": "Overlapping Days"},
        )
        st.plotly_chart(fig, use_container_width=True)
        _display_resource_conflicts_chart_legend()

        st.subheader("Conflict Details")
        st.dataframe(conflicts_df, use_container_width=True)
    else:
        st.success("No resource conflicts detected.")


def _display_resource_conflicts_chart_legend():
    with st.expander("Chart Legend", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Visual Indicators:**")
            st.markdown("- **Red Bars**: Duration of overlapping assignments.")
            st.markdown("- **Hover Details**: Shows overlapping projects and days.")
        with col2:
            st.markdown("**Interactive Features:**")
            st.markdown("- **Zoom**: Use the range selector or slider at the bottom.")
            st.markdown("- **Details**: Hover over bars to see conflict details.")
            st.markdown("- **Pan**: Click and drag on the timeline.")


def display_capacity_planning_dashboard(
    filtered_data: pd.DataFrame, start_date=None, end_date=None
):
    """
    Displays the capacity planning dashboard.
    """
    if filtered_data.empty:
        st.warning("No data available for capacity planning.")
        return

    # Get filtered resources
    filtered_resources = filtered_data["Resource"].unique()

    # Calculate capacity data
    capacity_data = calculate_capacity_data(start_date, end_date)

    # Filter capacity data to only include resources from filtered_data
    capacity_data = capacity_data[capacity_data["Resource"].isin(filtered_resources)]

    if capacity_data.empty:
        st.warning("No capacity data available for the selected period and filters.")
        return

    # Display capacity overview
    st.subheader("Capacity Overview")
    col1, col2, col3 = st.columns(3)
    with col1:
        total_capacity = capacity_data["Capacity (hours)"].sum()
        st.metric("Total Capacity (hours)", f"{total_capacity:,.1f}")
    with col2:
        total_allocated = capacity_data["Allocated (hours)"].sum()
        st.metric("Total Allocated (hours)", f"{total_allocated:,.1f}")
    with col3:
        overall_utilization = (
            (total_allocated / total_capacity * 100) if total_capacity > 0 else 0
        )
        st.metric("Overall Utilization", f"{overall_utilization:.1f}%")

    # Capacity vs Allocation chart
    st.subheader("Capacity vs Allocation by Resource")

    # Sort by utilization for better visualization
    capacity_data = capacity_data.sort_values(by="Utilization %", ascending=False)

    fig = px.bar(
        capacity_data,
        x="Resource",
        y=["Capacity (hours)", "Allocated (hours)"],
        barmode="overlay",
        title="Resource Capacity vs Allocation",
        color_discrete_map={
            "Capacity (hours)": "cyan",
            "Allocated (hours)": "orange",
        },
        labels={"value": "Hours", "variable": "Metric"},
    )

    st.plotly_chart(fig, use_container_width=True)

    # Display detailed capacity table
    st.subheader("Detailed Capacity Data")
    st.dataframe(
        capacity_data,
        column_config={
            "Resource": st.column_config.TextColumn("Resource"),
            "Type": st.column_config.TextColumn("Type"),
            "Department": st.column_config.TextColumn("Department"),
            "Capacity (hours)": st.column_config.NumberColumn(
                "Capacity (Hours)", format="%.1f"
            ),
            "Allocated (hours)": st.column_config.NumberColumn(
                "Allocated (Hours)", format="%.1f"
            ),
            "Utilization %": st.column_config.ProgressColumn(
                "Utilization (%)", format="%.1f%%", min_value=0, max_value=100
            ),
            "Available (hours)": st.column_config.NumberColumn(
                "Available (Hours)", format="%.1f"
            ),
        },
        use_container_width=True,
    )


def identify_overallocated_resources(capacity_data, threshold=100):
    """Identify resources that are overallocated based on a utilization threshold."""
    overallocated = capacity_data[capacity_data["Utilization %"] > threshold]
    return overallocated


def display_overallocation_warnings(capacity_data):
    """Display warnings for overallocated resources."""
    overallocated = identify_overallocated_resources(capacity_data)

    if not overallocated.empty:
        st.warning(f"⚠️ {len(overallocated)} resources are overallocated:")

        for _, row in overallocated.iterrows():
            st.markdown(
                f"**{row['Resource']}** ({row['Type']}) - "
                f"Utilization: {row['Utilization %']:.1f}% - "
                f"Allocated: {row['Allocated (hours)']:.1f} hours / "
                f"Capacity: {row['Capacity (hours)']:.1f} hours"
            )


def display_resource_calendar(filtered_data: pd.DataFrame, start_date, end_date):
    """Display a calendar view of resource allocations."""
    if filtered_data.empty:
        st.warning("No data available for resource calendar.")
        return

    # Generate date range
    date_range = pd.date_range(start=start_date, end=end_date, freq="D")

    # Get resources from filtered data
    resources = filtered_data["Resource"].unique()

    # Create empty calendar DataFrame
    calendar_data = pd.DataFrame(0, index=resources, columns=date_range)

    # Process project data
    for project in st.session_state.data["projects"]:
        # Get resource allocations for this project
        resource_allocations = project.get("resource_allocations", [])

        # If no specific allocations, create default ones
        if not resource_allocations:
            resource_allocations = [
                {
                    "resource": r,
                    "allocation_percentage": 100,
                    "start_date": project["start_date"],
                    "end_date": project["end_date"],
                }
                for r in project["assigned_resources"]
                if r in resources
            ]

        # Process each allocation
        for allocation in resource_allocations:
            res = allocation["resource"]

            # Skip if resource is not in filtered resources
            if res not in resources:
                continue

            # Calculate overlap with the selected date range
            alloc_start = pd.to_datetime(allocation["start_date"])
            alloc_end = pd.to_datetime(allocation["end_date"])
            overlap_start = max(alloc_start, pd.Timestamp(start_date))
            overlap_end = min(alloc_end, pd.Timestamp(end_date))

            # Update calendar data
            if overlap_start <= overlap_end:
                overlap_dates = pd.date_range(
                    start=overlap_start, end=overlap_end, freq="D"
                )
                for date in overlap_dates:
                    if date in calendar_data.columns:
                        calendar_data.at[res, date] += allocation[
                            "allocation_percentage"
                        ]

    # Create heatmap visualization
    fig = px.imshow(
        calendar_data,
        labels=dict(x="Date", y="Resource", color="Allocation %"),
        x=calendar_data.columns,
        y=calendar_data.index,
        color_continuous_scale=[
            (0.0, "#ADD8E6"),  # Light blue for low allocation
            (0.5, "#32CD32"),  # Lime green for moderate allocation
            (1.0, "#FF4500"),  # Orange red for high allocation
        ],
        aspect="auto",
        height=800,
    )

    st.plotly_chart(fig, use_container_width=True)


def unified_filter_component() -> Tuple[pd.Timestamp, pd.Timestamp, List[str], float]:
    """
    Creates a unified filter component for use across multiple pages.

    Returns:
    - start_date: The start date for filtering
    - end_date: The end date for filtering
    - resource_types: List of selected resource types
    - utilization_threshold: The minimum utilization percentage to filter by
    """
    col1, col2 = st.columns(2)
    with col1:
        start_date = pd.to_datetime(
            st.date_input("Start Date", value=pd.to_datetime("today"))
        )
    with col2:
        end_date = pd.to_datetime(
            st.date_input(
                "End Date", value=pd.to_datetime("today") + pd.Timedelta(days=90)
            )
        )

    resource_types = st.multiselect(
        "Resource Type",
        options=["Person", "Team", "Department"],
        default=["Person", "Team", "Department"],
    )

    utilization_threshold = st.slider(
        "Minimum Utilization %", min_value=0, max_value=100, value=0, step=5
    )

    return start_date, end_date, resource_types, utilization_threshold


def display_standard_filters(update_session_state=True):
    """Display standard filters consistently across app."""
    with st.expander("Filter Options", expanded=True):
        col1, col2 = st.columns(2)

        # Date range selection
        with col1:
            start_date = st.date_input(
                "From",
                value=st.session_state.filter_state["date_range"]["start"],
            )
        with col2:
            end_date = st.date_input(
                "To",
                value=st.session_state.filter_state["date_range"]["end"],
            )

        # Resource type and department filters
        resource_types = st.multiselect(
            "Resource Types",
            options=["Person", "Team", "Department"],
            default=st.session_state.filter_state["resource_types"],
            key="filter_resource_types",
        )

        departments = st.multiselect(
            "Departments",
            options=sorted([d["name"] for d in st.session_state.data["departments"]]),
            default=st.session_state.filter_state["departments"],
            key="filter_departments",
        )

        # Utilization threshold
        utilization_threshold = st.slider(
            "Minimum Utilization %",
            min_value=0,
            max_value=100,
            value=st.session_state.filter_state["utilization_threshold"],
            step=5,
            key="filter_utilization",
        )

        # Update session state if requested
        if update_session_state:
            st.session_state.filter_state["date_range"]["start"] = start_date
            st.session_state.filter_state["date_range"]["end"] = end_date
            st.session_state.filter_state["resource_types"] = resource_types
            st.session_state.filter_state["departments"] = departments
            st.session_state.filter_state["utilization_threshold"] = (
                utilization_threshold
            )

    return start_date, end_date, resource_types, departments, utilization_threshold


def display_resource_matrix_view(df: pd.DataFrame, start_date=None, end_date=None):
    """Display a resource matrix view showing project allocations over time."""
    if df.empty:
        st.warning("No data available to visualize.")
        return

    # If dates not provided, use min/max from data
    if start_date is None:
        start_date = df["Start"].min()
    if end_date is None:
        end_date = df["Finish"].max()

    # Convert to pandas timestamps if needed
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

    # Calculate appropriate time periods based on date range
    range_days = (end_date - start_date).days
    if range_days <= 14:
        freq = "D"
        period_name = "Day"
    elif range_days <= 60:
        freq = "W"
        period_name = "Week"
    else:
        freq = "ME"
        period_name = "Month"

    # Generate time periods
    date_range = pd.date_range(start=start_date, end=end_date, freq=freq)
    if len(date_range) > 30:  # If too many periods, adjust frequency
        freq = "W" if freq == "D" else "ME"
        period_name = "Week" if freq == "W" else "Month"
        date_range = pd.date_range(start=start_date, end=end_date, freq=freq)

    # Get unique projects sorted by priority
    projects = df.sort_values(by="Priority", ascending=False)["Project"].unique()

    # Create empty matrix (projects × time periods)
    matrix_data = pd.DataFrame(0, index=projects, columns=date_range)

    # Ensure matrix_data is of type float64 to avoid dtype issues
    matrix_data = matrix_data.astype(float)

    # Add metadata for hover info
    hover_data = {}
    for project in projects:
        hover_data[project] = {period: [] for period in date_range}

    # Add weighted allocation to matrix
    for _, row in df.iterrows():
        project = row["Project"]
        resource = row["Resource"]
        resource_type = row["Type"]

        # Check if 'Allocation %' column exists, if not use default 100
        if "Allocation %" in row:
            allocation = row["Allocation %"]
        else:
            allocation = 100  # Default allocation percentage if not provided

        # Calculate period duration based on frequency
        if freq == "D":
            period_duration = pd.Timedelta(days=1)
        elif freq == "W":
            period_duration = pd.Timedelta(days=7)
        else:
            period_duration = pd.Timedelta(days=30)

        # Calculate overlap with each time period
        for period_start in date_range:
            period_end = period_start + period_duration - pd.Timedelta(seconds=1)

            # Check if allocation overlaps with period
            if (row["Start"] <= period_end) and (row["Finish"] >= period_start):
                # Calculate weighted allocation based on overlap
                start_overlap = max(row["Start"], period_start)
                end_overlap = min(row["Finish"], period_end)
                overlap_days = (end_overlap - start_overlap).days + 1
                period_days = (period_end - period_start).days + 1
                overlap_factor = min(1.0, overlap_days / period_days)

                # Add weighted allocation to matrix
                matrix_data.at[project, period_start] += allocation * overlap_factor

                # Store resource details for hover information
                hover_data[project][period_start].append(
                    {
                        "resource": resource,
                        "type": resource_type,
                        "allocation": allocation,
                        "dept": row["Department"],
                    }
                )

    # Generate hover text
    hover_text = []
    for project in projects:
        project_hover = []
        for period in date_range:
            period_text = (
                f"Project: {project}<br>{period_name}: {period.strftime('%b %d')}<br>"
            )
            period_text += (
                f"Total Allocation: {matrix_data.loc[project, period]:.1f}%<br>"
            )

            if hover_data[project][period]:
                period_text += "<br><b>Resources:</b><br>"
                for res in hover_data[project][period]:
                    period_text += f"• {res['resource']} ({res['type']}, {res['dept']}): {res['allocation']}%<br>"
            else:
                period_text += "<br>No resources allocated"

            project_hover.append(period_text)
        hover_text.append(project_hover)

    # Create color scale from configuration
    try:
        from configuration import load_heatmap_colorscale

        colorscale = load_heatmap_colorscale()
    except (ImportError, AttributeError):
        colorscale = [
            (0.0, "#f0f2f6"),  # No allocation
            (0.5, "#ffd700"),  # Moderate allocation
            (1.0, "#4b0082"),  # Full/over allocation
        ]

    # Create heatmap visualization
    fig = px.imshow(
        matrix_data,
        labels=dict(x=period_name, y="Project", color="Resource Allocation %"),
        x=[period.strftime("%b %d") for period in date_range],
        y=projects,
        color_continuous_scale=colorscale,
        aspect="auto",
        zmin=0,
        zmax=150,  # Allow visualization of overallocation
    )

    # Add custom hover information
    fig.update_traces(hovertemplate="%{hovertext}", hovertext=np.array(hover_text))

    # Add today marker line
    today = pd.Timestamp("today")
    if start_date <= today <= end_date:
        # Find the nearest date period
        nearest_period = min(date_range, key=lambda x: abs(x - today))
        period_idx = list(date_range).index(nearest_period)

        fig.add_vline(
            x=period_idx,
            line_width=2,
            line_color="red",
            line_dash="dash",
            annotation_text="Today",
            annotation_position="top",
        )

    # Customize layout
    fig.update_layout(
        height=max(400, len(projects) * 30),  # Dynamic height based on projects
        margin=dict(l=150, r=30, t=30, b=50),
        coloraxis_colorbar=dict(
            title="Allocation %",
            tickvals=[0, 50, 100, 150],
            ticktext=["0%", "50%", "100%", ">150%"],
        ),
        xaxis_title=f"{period_name}s",
        yaxis_title="Projects",
    )

    st.plotly_chart(fig, use_container_width=True)


def display_sunburst_organization(data):
    """Creates a sunburst chart showing organizational hierarchy with clear text labels."""
    import plotly.express as px
    import streamlit as st

    # Prepare data for sunburst chart
    labels = []
    parents = []
    values = []

    # Add root
    labels.append("Organization")
    parents.append("")  # Empty string is crucial for root node
    values.append(1)

    # Add departments
    for dept in data["departments"]:
        labels.append(dept["name"])
        parents.append("Organization")  # Connect to root
        values.append(
            len([t for t in data["teams"] if t.get("department") == dept["name"]]) + 1
        )

    # Add teams
    for team in data["teams"]:
        labels.append(team["name"])
        parents.append(
            team.get("department", "Organization")
        )  # Fallback to root if no department
        values.append(
            len([p for p in data["people"] if p.get("team") == team["name"]]) + 1
        )

    # Add people
    for person in data["people"]:
        if person.get("team"):
            labels.append(person["name"])
            parents.append(person["team"])
            values.append(1)
        elif person.get("department"):
            # People directly in department (not in any team)
            labels.append(person["name"])
            parents.append(person["department"])
            values.append(1)

    # Try branchvalues='remainder' instead of 'total' if chart is empty
    fig = px.sunburst(
        names=labels,
        parents=parents,
        values=values,
        branchvalues="remainder",
        color_discrete_sequence=px.colors.qualitative.Bold,
        height=1000,
    )

    # Customize text and hover information
    fig.update_traces(
        insidetextorientation="auto",
        textinfo="label",
        textfont=dict(size=16),
        hovertemplate="<b>%{label}</b><br>Parent: %{parent}",
    )

    # Update layout for better readability
    fig.update_layout(margin=dict(t=30, l=0, r=0, b=0))

    # Display the chart with Streamlit theme
    st.plotly_chart(fig, use_container_width=True, theme="streamlit")
