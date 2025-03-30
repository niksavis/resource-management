"""
UI styling utilities for the resource management application.

This module provides functions for styling the UI with CSS.
"""

import streamlit as st


def apply_custom_css():
    """Apply custom CSS to the Streamlit app."""
    st.markdown(
        """
        <style>
        /* Card styling with better dark mode support */
        div.card {
            border: 1px solid rgba(128, 128, 128, 0.2);
            border-radius: 5px;
            padding: 15px;
            margin-bottom: 15px;
            background-color: rgba(255, 255, 255, 0.05); /* Very slight white overlay */
            box-shadow: 2px 2px 12px rgba(0,0,0,0.05);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
            color: inherit; /* Inherit color from parent, works with both themes */
        }
        
        /* Hover effects */
        div.card:hover {
            transform: translateY(-2px);
            box-shadow: 2px 4px 16px rgba(0,0,0,0.1);
            border-color: rgba(128, 128, 128, 0.4);
            background-color: rgba(255, 255, 255, 0.1); /* Slightly lighter on hover */
        }
        
        /* Light mode specific styles */
        .light-mode div.card {
            background-color: white;
            color: #262730; /* Default Streamlit dark text color */
        }
        
        /* Dark mode specific styles */
        .dark-mode div.card {
            background-color: rgba(255, 255, 255, 0.1); /* Lighter background for dark mode */
            color: white;
        }
        
        /* Card headers - use theme-aware colors with better contrast */
        div.person-card h3 { color: #1f77b4; }
        .dark-mode div.person-card h3 { color: #4c9be8; } /* Lighter blue for dark mode */
        
        div.team-card h3 { color: #ff7f0e; }
        .dark-mode div.team-card h3 { color: #ffaa56; } /* Lighter orange for dark mode */
        
        div.department-card h3 { color: #2ca02c; }
        .dark-mode div.department-card h3 { color: #5cd75c; } /* Lighter green for dark mode */
        
        /* Resource cards */
        div.card p {
            margin: 5px 0;
            color: inherit; /* Inherit from parent for theme-awareness */
        }
        
        /* Resource card content */
        div.card strong {
            opacity: 0.9;
        }
        
        /* Add theme class to body based on Streamlit's theme */
        body {
            font-family: "Source Sans Pro", sans-serif;
        }
        
        body.light-mode-theme { 
            background-color: white;
            color: #262730;
        }
        
        body.dark-mode-theme {
            background-color: #0e1117;
            color: white;
        }
        
        /* Action buttons */
        div.action-buttons {
            padding: 10px;
            background-color: rgba(0, 0, 0, 0.05); /* Very slight shading */
            border-radius: 5px;
            margin-bottom: 20px;
        }
        
        /* Custom header styling */
        h1, h2, h3 {
            color: inherit; /* Use the text color from theme */
        }
        
        /* Expander styling */
        .streamlit-expanderHeader {
            font-weight: bold;
            color: inherit;
        }
        
        /* Script to detect and apply theme class */
        </style>
        <script>
            // Script to detect dark mode and apply appropriate class
            const isDarkTheme = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
            document.body.classList.add(isDarkTheme ? 'dark-mode' : 'light-mode');
            
            // Listen for theme changes
            window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
                document.body.classList.remove('dark-mode', 'light-mode');
                document.body.classList.add(e.matches ? 'dark-mode' : 'light-mode');
            });
        </script>
        """,
        unsafe_allow_html=True,
    )
