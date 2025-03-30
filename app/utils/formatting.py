"""
Formatting utility functions for the resource management application.

This module provides functions for formatting data in various ways.
"""

from typing import List, Dict, Union


def format_circular_dependency_message(
    cycles: List[str],
    multi_team_members: Dict[str, List[str]],
    multi_department_members: Dict[str, List[str]],
    multi_department_teams: Dict[str, List[str]],
) -> str:
    """
    Format a warning message about circular dependencies.

    Args:
        cycles: List of circular dependency paths
        multi_team_members: Dict of people in multiple teams
        multi_department_members: Dict of people in multiple departments
        multi_department_teams: Dict of teams in multiple departments

    Returns:
        Formatted warning message
    """
    message_parts = []

    if cycles:
        message_parts.append("⚠️ **Circular Dependencies Detected**\n")
        message_parts.append("The following circular dependencies were found:\n")
        for cycle in cycles:
            message_parts.append(f"- {cycle}\n")

    if multi_team_members:
        message_parts.append("\n⚠️ **People in Multiple Teams**\n")
        for person, teams in multi_team_members.items():
            message_parts.append(f"- {person}: {', '.join(teams)}\n")

    if multi_department_members:
        message_parts.append("\n⚠️ **People in Multiple Departments**\n")
        for person, departments in multi_department_members.items():
            message_parts.append(f"- {person}: {', '.join(departments)}\n")

    if multi_department_teams:
        message_parts.append("\n⚠️ **Teams in Multiple Departments**\n")
        for team, departments in multi_department_teams.items():
            message_parts.append(f"- {team}: {', '.join(departments)}\n")

    if not message_parts:
        message_parts.append("No circular dependencies or conflicts detected.")

    return "".join(message_parts)


def format_currency(
    value: Union[float, int],
    currency: str = "$",
    decimal_places: int = 2,
    symbol_position: str = "prefix",
) -> str:
    """
    Format a numeric value as currency.

    Args:
        value: The numeric value to format
        currency: Currency symbol to use
        decimal_places: Number of decimal places to display
        symbol_position: Whether to show symbol before or after value ('prefix' or 'suffix')

    Returns:
        Formatted currency string
    """
    formatted_value = f"{value:,.{decimal_places}f}"
    if symbol_position == "prefix":
        return f"{currency} {formatted_value}"
    else:
        return f"{formatted_value} {currency}"
