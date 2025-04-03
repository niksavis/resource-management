"""
Import validation service for the resource management application.

This module provides validation and conflict resolution functions for importing data.
"""

from typing import Dict, Any, List, Tuple
from app.services.validation_service import (
    validate_imported_data,
    suggest_relationship_fixes,
)


def validate_and_process_import(
    import_data: Dict[str, List[Dict[str, Any]]],
) -> Tuple[bool, Dict[str, Any], Dict[str, List[str]]]:
    """
    Validate imported data and process it for import, identifying any conflicts.

    Args:
        import_data: Dictionary containing people, teams, departments, and projects to import

    Returns:
        Tuple of (is_valid, processed_data, validation_messages)
    """
    # First validate the data
    is_valid, validation_errors = validate_imported_data(import_data)

    # Generate suggestions for fixing errors
    suggested_fixes = suggest_relationship_fixes(validation_errors)

    # Combine errors and fixes into a single message set
    validation_messages = {
        resource_type: errors + suggested_fixes.get(resource_type, [])
        for resource_type, errors in validation_errors.items()
    }

    # If valid, or we want to process anyway, prepare the data
    processed_data = {"people": [], "teams": [], "departments": [], "projects": []}

    # Process each resource type, applying any automatic corrections
    for person in import_data.get("people", []):
        # Handle team-department alignment
        if person.get("team"):
            team = next(
                (
                    t
                    for t in import_data.get("teams", [])
                    if t["name"] == person["team"]
                ),
                None,
            )
            if team and team.get("department"):
                # Ensure person's department matches team's department
                person["department"] = team["department"]
        processed_data["people"].append(person)

    # Copy the other resource types directly for now
    processed_data["teams"] = import_data.get("teams", [])
    processed_data["departments"] = import_data.get("departments", [])
    processed_data["projects"] = import_data.get("projects", [])

    return is_valid, processed_data, validation_messages
