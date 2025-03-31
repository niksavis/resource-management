"""
Dashboard UI components.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Any, List
from datetime import datetime, timedelta

from app.utils.ui_components import display_action_bar
from app.services.config_service import (
    load_currency_settings,
    load_display_preferences,
    load_utilization_thresholds,
    load_department_colors,
)
from app.services.data_service import (
    paginate_dataframe,
    create_gantt_data,
    calculate_resource_utilization,
    calculate_project_cost,
)


def display_home_tab():
    """Display the main dashboard/home screen."""
    display_action_bar()

    # Page header with refresh indicator
    col1, col2 = st.columns([9, 1])
    with col1:
        st.subheader("Resource Management Dashboard")
    with col2:
        st.caption(f"Updated: {datetime.now().strftime('%H:%M')}")

    # Key insights panel
    _display_key_insights()

    # Summary metrics
    _display_summary_metrics()

    # Project timeline
    st.markdown("### Project Timeline")
    if st.session_state.data["projects"]:
        _display_project_timeline()
    else:
        st.info("No projects found. Add projects to see a timeline.")

    # Resource overview tabs
    st.markdown("### Resource Overview")
    tabs = st.tabs(["Department Allocation", "Utilization", "Budget Overview"])

    with tabs[0]:
        _display_department_allocation()

    with tabs[1]:
        _display_utilization_summary()

    with tabs[2]:
        _display_budget_overview()


def _display_key_insights():
    """Display key insights summary at the top of dashboard."""
    # Calculate insights
    active_projects_count = 0
    high_priority_count = 0
    over_utilized_count = 0
    under_utilized_count = 0
    over_budget_count = 0

    if st.session_state.data["projects"]:
        # Count active and high priority projects
        today = datetime.now()
        for project in st.session_state.data["projects"]:
            start_date = pd.to_datetime(project["start_date"])
            end_date = pd.to_datetime(project["end_date"])
            if start_date <= today <= end_date:
                active_projects_count += 1
            if project.get("priority") == 1:
                high_priority_count += 1

        # Get utilization data
        if st.session_state.data["people"]:
            gantt_data = create_gantt_data(
                st.session_state.data["projects"], st.session_state.data
            )
            if not gantt_data.empty:
                utilization_df = calculate_resource_utilization(gantt_data)
                if not utilization_df.empty:
                    thresholds = load_utilization_thresholds()
                    under_threshold = thresholds.get("under", 50)
                    over_threshold = thresholds.get("over", 100)

                    over_utilized_count = len(
                        utilization_df[utilization_df["Utilization %"] > over_threshold]
                    )
                    under_utilized_count = len(
                        utilization_df[
                            utilization_df["Utilization %"] < under_threshold
                        ]
                    )

        # Count over budget projects
        for project in st.session_state.data["projects"]:
            if "allocated_budget" in project:
                actual_cost = calculate_project_cost(
                    project,
                    st.session_state.data["people"],
                    st.session_state.data["teams"],
                )
                if actual_cost > project["allocated_budget"]:
                    over_budget_count += 1

    # Display insights in collapsible card
    with st.expander("🔍 Dashboard Insights", expanded=True):
        cols = st.columns(5)

        with cols[0]:
            st.markdown(f"**Active Projects**")
            st.markdown(
                f"<h2 style='margin-top:-10px;'>{active_projects_count}</h2>",
                unsafe_allow_html=True,
            )

        with cols[1]:
            st.markdown(f"**High Priority**")
            st.markdown(
                f"<h2 style='margin-top:-10px;'>{high_priority_count}</h2>",
                unsafe_allow_html=True,
            )

        with cols[2]:
            st.markdown(f"**Over-utilized**")
            color = "red" if over_utilized_count > 0 else "inherit"
            st.markdown(
                f"<h2 style='margin-top:-10px;color:{color};'>{over_utilized_count}</h2>",
                unsafe_allow_html=True,
            )

        with cols[3]:
            st.markdown(f"**Under-utilized**")
            color = "orange" if under_utilized_count > 0 else "inherit"
            st.markdown(
                f"<h2 style='margin-top:-10px;color:{color};'>{under_utilized_count}</h2>",
                unsafe_allow_html=True,
            )

        with cols[4]:
            st.markdown(f"**Over Budget**")
            color = "red" if over_budget_count > 0 else "inherit"
            st.markdown(
                f"<h2 style='margin-top:-10px;color:{color};'>{over_budget_count}</h2>",
                unsafe_allow_html=True,
            )


def _display_summary_metrics():
    """Display the summary metrics section of the dashboard."""
    # Count metrics
    people_count = len(st.session_state.data["people"])
    teams_count = len(st.session_state.data["teams"])
    dept_count = len(st.session_state.data["departments"])
    project_count = len(st.session_state.data["projects"])

    # Calculate utilization average if data exists
    avg_utilization = None
    if st.session_state.data["projects"] and st.session_state.data["people"]:
        gantt_data = create_gantt_data(
            st.session_state.data["projects"], st.session_state.data
        )
        if not gantt_data.empty:
            utilization_df = calculate_resource_utilization(gantt_data)
            if not utilization_df.empty:
                avg_utilization = utilization_df["Utilization %"].mean()

    # Display in a 5-column layout
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("People", people_count)
    with col2:
        st.metric("Teams", teams_count)
    with col3:
        st.metric("Departments", dept_count)
    with col4:
        st.metric("Projects", project_count)
    with col5:
        if avg_utilization is not None:
            st.metric("Avg Utilization", f"{avg_utilization:.1f}%")
        else:
            st.metric("Avg Utilization", "N/A")


def _display_project_timeline():
    """Display project timeline visualization."""
    # Create project dataframe for timeline with status
    today = datetime.now()
    projects_df = pd.DataFrame(
        [
            {
                "Project": p["name"],
                "Start": pd.to_datetime(p["start_date"]),
                "End": pd.to_datetime(p["end_date"]),
                "Priority": p["priority"],
                "Resources": len(p.get("assigned_resources", [])),
                # Add status based on timeline
                "Status": "Upcoming"
                if pd.to_datetime(p["start_date"]) > today
                else "Complete"
                if pd.to_datetime(p["end_date"]) < today
                else "Active",
            }
            for p in st.session_state.data["projects"]
        ]
    )

    # Add status filter
    status_filter = st.selectbox(
        "Filter by status:",
        options=["All"] + sorted(projects_df["Status"].unique().tolist()),
    )

    if status_filter != "All":
        projects_df = projects_df[projects_df["Status"] == status_filter]

    # Sort by priority and start date
    projects_df = projects_df.sort_values(by=["Priority", "Start"])

    # Color map for status - colors that work in both themes
    status_color_map = {
        "Active": "#4CAF50",  # Green
        "Upcoming": "#2196F3",  # Blue
        "Complete": "#9E9E9E",  # Gray
    }

    # Create timeline chart colored by status instead of priority
    fig = px.timeline(
        projects_df,
        x_start="Start",
        x_end="End",
        y="Project",
        color="Status",
        color_discrete_map=status_color_map,
        hover_data=["Priority", "Resources"],
        labels={"Status": "Project Status", "Priority": "Priority (1=Highest)"},
        title="Project Timeline",
    )

    # Add today's date line
    today_date = datetime.now().date()

    # Add a simple vertical line annotation
    fig.add_shape(
        type="line",
        x0=today_date,
        x1=today_date,
        y0=0,
        y1=1,
        yref="paper",
        line=dict(
            color="#FF5252", width=2, dash="dash"
        ),  # Brighter red for both themes
    )

    # Add text annotation for "Today"
    fig.add_annotation(
        x=today_date,
        y=1.0,
        yref="paper",
        text="Today",
        showarrow=False,
        font=dict(color="#FF5252"),
        bgcolor="rgba(255, 255, 255, 0.5)",  # Semi-transparent background
        bordercolor="#FF5252",
        borderwidth=1,
    )

    # Theme compatibility
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",  # Transparent background
        plot_bgcolor="rgba(0,0,0,0)",  # Transparent background
        font=dict(size=12),  # Slightly larger font
        margin=dict(l=10, r=10, t=30, b=10),
    )

    # Update axes for better visibility
    fig.update_xaxes(
        gridcolor="rgba(128, 128, 128, 0.2)",
        mirror=True,
        showline=True,
        linecolor="rgba(128, 128, 128, 0.4)",
    )
    fig.update_yaxes(
        gridcolor="rgba(128, 128, 128, 0.2)",
        mirror=True,
        showline=True,
        linecolor="rgba(128, 128, 128, 0.4)",
    )

    # Display chart
    st.plotly_chart(fig, use_container_width=True)

    # Add completion metrics
    with st.expander("Project Completion Metrics"):
        active_count = len(projects_df[projects_df["Status"] == "Active"])
        upcoming_count = len(projects_df[projects_df["Status"] == "Upcoming"])
        completed_count = len(projects_df[projects_df["Status"] == "Complete"])

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Active Projects", active_count)
        with col2:
            st.metric("Upcoming Projects", upcoming_count)
        with col3:
            st.metric("Completed Projects", completed_count)


def _display_department_allocation():
    """Display department allocation pie chart."""
    if not st.session_state.data["people"]:
        st.info("No people data available.")
        return

    # Create department counts
    dept_counts = {}
    for person in st.session_state.data["people"]:
        dept = person["department"]
        dept_counts[dept] = dept_counts.get(dept, 0) + 1

    # Create dataframe
    dept_df = pd.DataFrame(
        {"Department": list(dept_counts.keys()), "People": list(dept_counts.values())}
    )

    # Calculate percentages
    total_people = dept_df["People"].sum()
    dept_df["Percentage"] = (dept_df["People"] / total_people * 100).round(1)

    # Load department colors
    dept_colors = load_department_colors()
    color_map = {
        dept: color for dept, color in dept_colors.items() if dept in dept_counts
    }

    # Create two-column layout
    col1, col2 = st.columns(2)

    with col1:
        # Create pie chart
        fig_pie = px.pie(
            dept_df,
            names="Department",
            values="People",
            title="People by Department",
            color="Department",
            color_discrete_map=color_map,
            hole=0.4,
            labels={"People": "Count"},
            hover_data=["Percentage"],
        )

        # Improve pie chart for theme compatibility
        fig_pie.update_traces(
            textinfo="percent+label",
            textposition="inside",
            textfont=dict(color="white", size=12),
            insidetextorientation="radial",
        )

        # Transparent background for theme compatibility
        fig_pie.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=30, b=10),
        )

        # Display chart
        st.plotly_chart(fig_pie, use_container_width=True)

    with col2:
        # Create horizontal bar chart
        fig_bar = px.bar(
            dept_df.sort_values("People", ascending=True),
            y="Department",
            x="People",
            color="Department",
            color_discrete_map=color_map,
            orientation="h",
            text="People",
            title="Department Size",
            labels={"People": "Number of People"},
        )

        # Improve bar chart
        fig_bar.update_traces(
            textposition="outside",
            texttemplate="%{text} (%{x})",
        )

        # Theme compatibility
        fig_bar.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=30, b=10, r=150),
            showlegend=False,
        )

        fig_bar.update_xaxes(
            gridcolor="rgba(128, 128, 128, 0.2)",
            mirror=True,
            showline=True,
            linecolor="rgba(128, 128, 128, 0.4)",
        )
        fig_bar.update_yaxes(
            gridcolor="rgba(128, 128, 128, 0.2)",
            mirror=True,
            showline=True,
            linecolor="rgba(128, 128, 128, 0.4)",
        )

        st.plotly_chart(fig_bar, use_container_width=True)

    # Show department table
    with st.expander("Department Details"):
        st.dataframe(
            dept_df.sort_values("People", ascending=False),
            use_container_width=True,
            hide_index=True,
        )


def _display_utilization_summary():
    """Display utilization summary chart."""
    if not st.session_state.data["projects"] or not st.session_state.data["people"]:
        st.info("No project or resource data available.")
        return

    # Create Gantt data for utilization calculation
    gantt_data = create_gantt_data(
        st.session_state.data["projects"], st.session_state.data
    )

    if gantt_data.empty:
        st.info("No allocation data available.")
        return

    # Calculate utilization
    utilization_df = calculate_resource_utilization(gantt_data)

    if utilization_df.empty:
        st.info("No utilization data available.")
        return

    # Load thresholds
    thresholds = load_utilization_thresholds()
    under_threshold = thresholds.get("under", 50)
    over_threshold = thresholds.get("over", 100)

    # Add resource type filter
    resource_types = sorted(utilization_df["Type"].unique().tolist())
    selected_types = st.multiselect(
        "Filter by resource type:", options=resource_types, default=resource_types
    )

    if selected_types:
        filtered_df = utilization_df[utilization_df["Type"].isin(selected_types)]
    else:
        filtered_df = utilization_df.copy()

    # Create utilization metrics
    avg_utilization = filtered_df["Utilization %"].mean()
    over_utilized = len(filtered_df[filtered_df["Utilization %"] > over_threshold])
    under_utilized = len(filtered_df[filtered_df["Utilization %"] < under_threshold])
    optimal_utilized = len(
        filtered_df[
            (filtered_df["Utilization %"] >= under_threshold)
            & (filtered_df["Utilization %"] <= over_threshold)
        ]
    )

    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Average Utilization", f"{avg_utilization:.1f}%")
    with col2:
        st.metric(
            "Overutilized",
            over_utilized,
            delta=f"{over_utilized}",
            delta_color="inverse",
        )
    with col3:
        st.metric(
            "Underutilized",
            under_utilized,
            delta=f"{under_utilized}",
            delta_color="inverse",
        )
    with col4:
        st.metric(
            "Optimal Range",
            optimal_utilized,
        )

    # Create bar chart of top resources
    # Use colors that work in both light and dark themes
    color_map = {
        "Person": "#42A5F5",  # Blue
        "Team": "#FFA726",  # Orange
        "Department": "#66BB6A",  # Green
    }

    # Sort by utilization
    top_utilized = filtered_df.sort_values("Utilization %", ascending=False).head(10)

    fig = px.bar(
        top_utilized,
        x="Resource",
        y="Utilization %",
        color="Type",
        title="Top 10 Most Utilized Resources",
        labels={"Resource": "Resource", "Utilization %": "Utilization %"},
        color_discrete_map=color_map,
        text="Utilization %",
    )

    # Format the text to show percentages
    fig.update_traces(
        texttemplate="%{text:.1f}%",
        textposition="outside",
    )

    # Add threshold zones
    fig.add_hrect(
        y0=0,
        y1=under_threshold,
        fillcolor="rgba(65, 105, 225, 0.2)",  # Blue with opacity
        line_width=0,
        annotation_text="Underutilized",
        annotation_position="left",
    )

    fig.add_hrect(
        y0=under_threshold,
        y1=over_threshold,
        fillcolor="rgba(50, 205, 50, 0.2)",  # Green with opacity
        line_width=0,
        annotation_text="Optimal",
        annotation_position="left",
    )

    fig.add_hrect(
        y0=over_threshold,
        y1=150,
        fillcolor="rgba(220, 20, 60, 0.2)",  # Red with opacity
        line_width=0,
        annotation_text="Overutilized",
        annotation_position="left",
    )

    # Add threshold lines
    fig.add_hline(
        y=over_threshold, line_width=2, line_dash="dash", line_color="#E57373"
    )  # Lighter red
    fig.add_hline(
        y=under_threshold, line_width=2, line_dash="dash", line_color="#64B5F6"
    )  # Lighter blue

    # Theme compatibility
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis_title="Resource",
        yaxis_title="Utilization (%)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=10, r=10, t=50, b=100),  # More bottom space for x labels
    )

    # Update axes for better visibility
    fig.update_xaxes(
        gridcolor="rgba(128, 128, 128, 0.2)",
        mirror=True,
        showline=True,
        linecolor="rgba(128, 128, 128, 0.4)",
        tickangle=-45,  # Angle labels for better readability
    )
    fig.update_yaxes(
        gridcolor="rgba(128, 128, 128, 0.2)",
        mirror=True,
        showline=True,
        linecolor="rgba(128, 128, 128, 0.4)",
        range=[0, max(150, filtered_df["Utilization %"].max() * 1.1)],
    )

    # Display chart
    st.plotly_chart(fig, use_container_width=True)

    # Show utilization table with expanded data
    with st.expander("Detailed Utilization Data"):
        st.dataframe(
            filtered_df.sort_values("Utilization %", ascending=False),
            use_container_width=True,
        )


def _display_budget_overview():
    """Display budget overview chart."""
    if not st.session_state.data["projects"]:
        st.info("No project data available.")
        return

    # Get currency symbol and format
    currency, currency_format = load_currency_settings()

    # Determine if space should be added between currency and amount
    add_space = currency_format.get("add_space", False)
    currency_prefix = f"{currency} " if add_space else currency
    currency_suffix = f" {currency}" if add_space else currency

    # Formatter function for currency
    def format_currency(value):
        if currency_format["symbol_position"] == "prefix":
            return f"{currency_prefix}{value:,.0f}"
        else:
            return f"{value:,.0f}{currency_suffix}"

    # Create budget data
    budget_data = []
    for project in st.session_state.data["projects"]:
        if "allocated_budget" in project:
            actual_cost = calculate_project_cost(
                project, st.session_state.data["people"], st.session_state.data["teams"]
            )

            # Calculate variance and status
            variance = project["allocated_budget"] - actual_cost
            variance_pct = (
                (variance / project["allocated_budget"] * 100)
                if project["allocated_budget"] > 0
                else 0
            )

            budget_data.append(
                {
                    "Project": project["name"],
                    "Allocated Budget": project["allocated_budget"],
                    "Estimated Cost": actual_cost,
                    "Variance": variance,
                    "Variance %": variance_pct,
                    "Status": "Under Budget" if variance >= 0 else "Over Budget",
                }
            )

    if not budget_data:
        st.info("No budget data available.")
        return

    # Create dataframe
    budget_df = pd.DataFrame(budget_data)

    # Add budget status filter
    status_filter = st.selectbox(
        "Filter by budget status:", options=["All", "Under Budget", "Over Budget"]
    )

    if status_filter != "All":
        budget_df = budget_df[budget_df["Status"] == status_filter]

    # Summary metrics
    total_budget = budget_df["Allocated Budget"].sum()
    total_cost = budget_df["Estimated Cost"].sum()
    total_variance = budget_df["Variance"].sum()

    # Create metrics row
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Budget", format_currency(total_budget))
    with col2:
        st.metric("Total Cost", format_currency(total_cost))
    with col3:
        st.metric(
            "Variance",
            format_currency(abs(total_variance)),
            delta=f"{'Under' if total_variance >= 0 else 'Over'} Budget",
            delta_color="normal" if total_variance >= 0 else "inverse",
        )

    # Sort for better visualization
    budget_df_sorted = budget_df.sort_values("Project")

    # Create grouped bar chart
    fig = go.Figure()

    # Add bars for budget and cost
    fig.add_trace(
        go.Bar(
            x=budget_df_sorted["Project"],
            y=budget_df_sorted["Allocated Budget"],
            name=f"Allocated Budget ({currency})",
            marker_color="#42A5F5",  # Blue - works in both themes
            text=budget_df_sorted["Allocated Budget"].apply(
                lambda x: format_currency(x)
            ),
            textposition="outside",
        )
    )

    fig.add_trace(
        go.Bar(
            x=budget_df_sorted["Project"],
            y=budget_df_sorted["Estimated Cost"],
            name=f"Estimated Cost ({currency})",
            marker_color="#EF5350",  # Red - works in both themes
            text=budget_df_sorted["Estimated Cost"].apply(lambda x: format_currency(x)),
            textposition="outside",
        )
    )

    # Add variance indicator
    for i, row in budget_df_sorted.iterrows():
        variance_color = (
            "#4CAF50" if row["Variance"] >= 0 else "#F44336"
        )  # Green or red
        fig.add_shape(
            type="line",
            x0=i - 0.2,
            x1=i + 0.2,
            y0=max(row["Allocated Budget"], row["Estimated Cost"])
            + total_budget * 0.03,
            y1=max(row["Allocated Budget"], row["Estimated Cost"])
            + total_budget * 0.03,
            line=dict(color=variance_color, width=4),
        )

    # Update layout
    fig.update_layout(
        title="Budget vs. Estimated Cost by Project",
        xaxis_title="Project",
        yaxis_title=f"Amount ({currency})",
        barmode="group",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    # Format y-axis with currency symbol and thousands separator
    # Adjust tickprefix with space if needed
    y_tickprefix = (
        f"{currency_prefix}" if currency_format["symbol_position"] == "prefix" else ""
    )
    y_ticksuffix = (
        f"{currency_suffix}" if currency_format["symbol_position"] == "suffix" else ""
    )

    fig.update_layout(
        yaxis=dict(
            tickprefix=y_tickprefix,
            ticksuffix=y_ticksuffix,
            separatethousands=True,
            gridcolor="rgba(128, 128, 128, 0.2)",
            mirror=True,
            showline=True,
            linecolor="rgba(128, 128, 128, 0.4)",
        ),
        xaxis=dict(
            gridcolor="rgba(128, 128, 128, 0.2)",
            mirror=True,
            showline=True,
            linecolor="rgba(128, 128, 128, 0.4)",
            tickangle=-45 if len(budget_df) > 5 else 0,  # Angle labels if many projects
        ),
    )

    # Display chart
    st.plotly_chart(fig, use_container_width=True)

    # Show budget details table
    with st.expander("Budget Details"):
        # Format columns for display
        display_df = budget_df.copy()
        display_df["Allocated Budget"] = display_df["Allocated Budget"].apply(
            lambda x: format_currency(x)
        )
        display_df["Estimated Cost"] = display_df["Estimated Cost"].apply(
            lambda x: format_currency(x)
        )
        display_df["Variance"] = display_df["Variance"].apply(
            lambda x: format_currency(x)
        )
        display_df["Variance %"] = display_df["Variance %"].apply(lambda x: f"{x:.1f}%")

        st.dataframe(
            display_df.sort_values("Project"),
            use_container_width=True,
            hide_index=True,
        )
