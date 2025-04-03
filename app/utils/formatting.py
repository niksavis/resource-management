"""
Formatting utility functions for the resource management application.

This module provides functions for formatting data in various ways.
"""

from typing import List, Tuple, Union


def format_circular_dependency_message(
    cycles: List[List[str]],
    multi_team_members: List[Tuple[str, List[str]]],
    multi_department_members: List[Tuple[str, List[str]]],
    multi_department_teams: List[Tuple[str, List[str]]],
) -> str:
    """
    Format circular dependency message for display.

    Args:
        cycles: List of dependency cycles
        multi_team_members: List of tuples (person, team_list) for people in multiple teams
        multi_department_members: List of tuples (person, dept_list) for people in multiple departments
        multi_department_teams: List of tuples (team, dept_list) for teams in multiple departments

    Returns:
        Formatted message for display
    """
    message_parts = []

    if cycles:
        message_parts.append("### Circular Dependencies Detected")
        for cycle in cycles:
            message_parts.append(f"- {' → '.join(cycle)}")

    if multi_team_members:
        message_parts.append("### People in Multiple Teams")
        for person, teams in multi_team_members:
            message_parts.append(f"- **{person}** is in teams: {', '.join(teams)}")

    if multi_department_members:
        message_parts.append("### People in Multiple Departments")
        for person, departments in multi_department_members:
            message_parts.append(
                f"- **{person}** is in departments: {', '.join(departments)}"
            )

    if multi_department_teams:
        message_parts.append("### Teams in Multiple Departments")
        for team, departments in multi_department_teams:
            message_parts.append(
                f"- **{team}** is in departments: {', '.join(departments)}"
            )

    if not any(
        [cycles, multi_team_members, multi_department_members, multi_department_teams]
    ):
        return "No circular dependencies detected."

    return "\n\n".join(message_parts)


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
