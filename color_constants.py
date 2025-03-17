"""
Color Constants Module

This module defines color constants for use in visualizations, including
department colors and utilization colorscales.
"""

DEPARTMENT_COLORS = {
    "Network Engineering": "#1f77b4",
    "Software Development": "#ff7f0e",
    "Information Technology": "#2ca02c",
    "Product Management": "#d62728",
    "Customer Experience": "#9467bd",
    "Operations": "#8c564b",
    "Research and Development": "#e377c2",
    # Add other departments as needed
}

UTILIZATION_COLORSCALE = [[0, "green"], [0.6, "yellow"], [0.8, "orange"], [1, "red"]]
