"""
Visualization module for the resource management application.

DEPRECATED: This module is maintained for backward compatibility.
Please use app.ui.visualizations and app.services.visualization_service instead.
"""

import warnings

warnings.warn(
    "The visualization module is deprecated. Use app.ui.visualizations and "
    "app.services.visualization_service instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export visualization UI functions
from app.ui.visualizations import (
    display_gantt_chart,
    display_utilization_chart,
    display_sunburst_organization,
    # Add aliases for backward compatibility
    display_gantt_chart as create_gantt_chart,
    display_utilization_chart as create_utilization_chart,
    display_sunburst_organization as create_sunburst_chart,
)

# Re-export visualization service functions
from app.services.visualization_service import (
    prepare_gantt_data,
    prepare_utilization_data,
    prepare_capacity_data,
    prepare_budget_data,
    calculate_project_cost,
    # Add aliases for backward compatibility
    prepare_gantt_data as create_gantt_data,
    prepare_utilization_data as create_utilization_data,
    prepare_capacity_data as create_resource_calendar,
    prepare_capacity_data as create_capacity_heatmap,
)

# Re-export needed types and libraries for backward compatibility
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, List, Any, Optional, Tuple
from app.services.config_service import (
    load_department_colors,
    load_heatmap_colorscale,
)


# Add any missing functions that haven't been moved yet
def create_department_distribution(departments, department_colors=None):
    """
    DEPRECATED: Use app.ui.visualizations.display_department_distribution instead.

    Create a departmental distribution chart.
    This function is maintained for backward compatibility only.
    """
    warnings.warn(
        "create_department_distribution is deprecated.",
        DeprecationWarning,
        stacklevel=2,
    )
    # Import here to avoid circular imports
    from app.ui.visualizations import display_department_distribution

    return display_department_distribution(departments, department_colors)
