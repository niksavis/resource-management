"""
Styling utilities for the resource management application.
"""

import streamlit as st


def apply_custom_css():
    """Apply custom CSS for better mobile experience, card styling, and hover effects."""
    st.markdown(
        """
    <style>
    /* Card styling with hover effects */
    div.stMarkdown div.card {
        border: 1px solid rgba(49, 51, 63, 0.2);
        border-radius: 0.5rem;
        padding: 1rem;
        margin-bottom: 1rem;
        transition: all 0.3s ease;
        background-color: rgba(255, 255, 255, 0.05);
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        /* Remove align-items: center to restore left-aligned text */
    }
    
    div.stMarkdown div.card:hover {
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
        transform: translateY(-2px);
        border-color: #ff4b4b;
    }

    /* Card-specific colors */
    div.stMarkdown div.person-card {
        border-left: 5px solid green;
    }
    div.stMarkdown div.team-card {
        border-left: 5px solid blue;
    }
    div.stMarkdown div.department-card {
        border-left: 5px solid purple;
    }

    /* Action buttons */
    .card-actions {
        margin-top: 10px;
        display: flex;
        justify-content: space-between;
    }
    .action-btn {
        background-color: #007bff;
        color: white;
        border: none;
        padding: 5px 10px;
        border-radius: 4px;
        cursor: pointer;
        transition: background-color 0.3s ease;
    }
    .action-btn:hover {
        background-color: #0056b3;
    }

    /* Responsive layout */
    @media (max-width: 1024px) {
        div.stMarkdown div.card {
            /* Allow dynamic height for smaller screens */
        }
    }
    @media (max-width: 768px) {
        div.stMarkdown div.card {
            /* Allow dynamic height for mobile screens */
        }
    }
    </style>
    """,
        unsafe_allow_html=True,
    )


def format_currency(value, currency="$", decimal_places=2, symbol_position="prefix"):
    """Format a value as currency according to settings."""
    formatted_value = f"{value:,.{decimal_places}f}"
    if symbol_position == "prefix":
        return f"{currency} {formatted_value}"
    else:
        return f"{formatted_value} {currency}"
