"""
Search service for resource management application.
"""

from typing import List, Tuple
import streamlit as st


def global_search(query: str) -> List[Tuple[str, str]]:
    """
    Search resources and projects globally.

    Args:
        query: The search query string

    Returns:
        A list of tuples containing (resource_type, resource_name)
    """
    if not query:
        return []

    results = []
    # Search people
    for person in st.session_state.data["people"]:
        if query.lower() in person["name"].lower():
            results.append(("Person", person["name"]))

    # Search teams
    for team in st.session_state.data["teams"]:
        if query.lower() in team["name"].lower():
            results.append(("Team", team["name"]))

    # Search projects
    for project in st.session_state.data["projects"]:
        if query.lower() in project["name"].lower():
            results.append(("Project", project["name"]))

    return results
