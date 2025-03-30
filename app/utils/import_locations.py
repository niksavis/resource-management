"""
Reference guide for locating functions in the new project structure.

This module lists the new locations of commonly used functions that were
moved during refactoring. Use this as a reference when updating imports.
"""

# From data_handlers.py -> app.services.data_service
DATA_HANDLERS_MAP = {
    "load_json": "app.services.data_service.load_json",
    "save_json": "app.services.data_service.save_json",
    "create_gantt_data": "app.services.data_service.create_gantt_data",
    "calculate_resource_utilization": "app.services.data_service.calculate_resource_utilization",
    "calculate_project_cost": "app.services.data_service.calculate_project_cost",
    "sort_projects_by_priority_and_date": "app.services.data_service.sort_projects_by_priority_and_date",
    "apply_filters": "app.services.data_service.apply_filters",
    "parse_resources": "app.services.data_service.parse_resources",
    "calculate_capacity_data": "app.services.data_service.calculate_capacity_data",
    "find_resource_conflicts": "app.services.data_service.find_resource_conflicts",
}

# From utils.py -> app.ui.components, app.services.data_service, app.utils.formatting
UTILS_MAP = {
    "display_filtered_resource": "app.ui.components.display_filtered_resource",
    "filter_dataframe": "app.ui.components.filter_dataframe",
    "confirm_action": "app.ui.components.confirm_action",
    "paginate_dataframe": "app.services.data_service.paginate_dataframe",
    "check_circular_dependencies": "app.services.data_service.check_circular_dependencies",
    "get_resource_type": "app.services.data_service.get_resource_type",
    "format_circular_dependency_message": "app.utils.formatting.format_circular_dependency_message",
    "format_currency": "app.utils.formatting.format_currency",
}

# From configuration.py -> app.services.config_service
CONFIG_MAP = {
    "load_settings": "app.services.config_service.load_settings",
    "save_settings": "app.services.config_service.save_settings",
    "load_currency_settings": "app.services.config_service.load_currency_settings",
    "load_department_colors": "app.services.config_service.load_department_colors",
    "add_department_color": "app.services.config_service.add_department_color",
}

# From visualization.py -> app.ui.visualizations, app.services.visualization_service
VISUALIZATION_MAP = {
    "create_gantt_chart": "app.ui.visualizations.display_gantt_chart",
    "create_utilization_chart": "app.ui.visualizations.display_utilization_chart",
    "create_sunburst_chart": "app.ui.visualizations.display_sunburst_organization",
    "create_department_distribution": "app.ui.visualizations.display_department_distribution",
    "prepare_gantt_data": "app.services.visualization_service.prepare_gantt_data",
    "prepare_utilization_data": "app.services.visualization_service.prepare_utilization_data",
    "create_resource_calendar": "app.services.visualization_service.prepare_capacity_data",
    "create_capacity_heatmap": "app.services.visualization_service.prepare_capacity_data",
}
