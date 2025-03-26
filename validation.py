from datetime import date
from typing import Tuple, List
import regex


def validate_name_field(name: str, field_type: str) -> bool:
    """
    Validates a name field to ensure it meets naming requirements.
    """
    if not name.strip():
        return False  # Name cannot be empty or whitespace

    if len(name) > 100:
        return False  # Name cannot exceed 100 characters

    # Check if name starts or ends with whitespace
    if name[0].isspace() or name[-1].isspace():
        return False

    # Use Unicode properties which are supported in the regex module
    # This allows for international characters in names
    if not regex.match(r"^[\p{L}\p{N} \-\'\.\,_]*$", name):
        return False

    return True


def validate_date_range(start_date, end_date) -> bool:
    """
    Validates that the start date is before or equal to the end date.
    """
    if start_date > end_date:
        return False
    return True


def validate_project_dates(start_date: date, end_date: date, project_name: str) -> bool:
    """
    Validates project start and end dates to ensure the start date is before the end date.
    """
    if start_date > end_date:
        return False
    return True


def validate_daily_cost(daily_cost: float) -> bool:
    return daily_cost > 0  # Daily cost must be positive


def validate_budget(budget: float) -> bool:
    return budget >= 0  # Budget must be non-negative


def validate_work_days(work_days: List[str]) -> bool:
    valid_days = {"MO", "TU", "WE", "TH", "FR", "SA", "SU"}
    return all(day in valid_days for day in work_days)


def validate_work_hours(work_hours: int) -> bool:
    return 1 <= work_hours <= 24  # Work hours must be between 1 and 24


def validate_project_input(project_data: dict) -> bool:
    """
    Validates project input data.
    """
    return (
        validate_name_field(project_data["name"], "project")
        and validate_date_range(project_data["start_date"], project_data["end_date"])
        and validate_budget(project_data["budget"])
    )


def detect_budget_overrun(
    project_cost: float, allocated_budget: float, threshold: float = 0.9
) -> Tuple[str, str]:
    """
    Detects if a project is nearing or exceeding its budget.
    """
    if project_cost > allocated_budget:
        return "Overrun", "Project has exceeded its allocated budget."
    elif project_cost >= allocated_budget * threshold:
        return "Warning", "Project is nearing its allocated budget."
    return "OK", "Project is within budget."
