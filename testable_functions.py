"""
Testable Functions Module

This module contains pure functions that can be tested independently.
"""

# Standard library imports
from datetime import datetime


def calculate_project_duration(start_date: datetime, end_date: datetime) -> int:
    """Calculate project duration in days."""
    return (end_date - start_date).days + 1


def is_resource_overallocated(
    allocation_days: int, total_days: int, threshold: float = 0.8
) -> bool:
    """Determine if a resource is overallocated based on percentage."""
    return (allocation_days / total_days) > threshold
