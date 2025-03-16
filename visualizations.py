import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime
from typing import Optional
from data_handlers import calculate_resource_utilization, filter_dataframe


def display_gantt_chart(df: pd.DataFrame) -> None:
    """
    Displays an interactive Gantt chart using Plotly.
    """
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


def display_utilization_dashboard(
    gantt_data: pd.DataFrame,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> None:
    """
    Displays a dashboard with resource utilization metrics.
    """
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
