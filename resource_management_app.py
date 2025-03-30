"""
Resource Management Application

A comprehensive tool for managing resources, projects, and workload analysis.
"""

import streamlit as st
import os
import sys
import base64

# Add the current directory to the path to allow importing local modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set environment variables to control Streamlit behavior
os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
os.environ["STREAMLIT_SERVER_HEADLESS"] = "true"  # For deployment

# Import app modules (avoid importing any modules that aren't absolutely needed)
try:
    from app.main import main
except ImportError as e:
    st.error(f"Failed to import required modules: {str(e)}")
    st.info(
        "Please ensure all required packages are installed using pip install -r requirements.txt"
    )
    st.stop()

if __name__ == "__main__":
    # Configure page settings
    st.set_page_config(
        page_title="Resource Management App",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            "About": """
            # Resource Management Application
            
            A comprehensive tool for managing resources, projects, and analyzing workload.
            
            Version: 1.0
            """
        },
    )

    try:
        # Add a favicon to make the app look more professional
        favicon = """
        <link rel="shortcut icon" href="data:image/x-icon;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAMASURBVFhH7ZZNaBNBFMffjNkmbbYmadpgaxVbP0CkIF5UEA+iIOJJEcGLFE968CS0qAfBkyAIHjwUBKEHQRAP4smD4EFExIO0UhD8aI2W2jRNY5JustmdcWaTTbomm26bHnzwY3Z35s3+/+/NvFmCMGEfBduRZQOyQaMohsQdqIRxYfcQsIRIFJbhJjAVRRGa6QLVarVEliHDMHowRTlir9VVfN0EpMN+Gw7yPL8XU5RD2+12Z6VSUebA5/M5ZVku4HvLRoGBgUKh4MbUJpqUYDAYw2HLKRAI7EP5bkyZggIcn8lkNJ+Eoihq/X4/j+lGYACOC4IwhsN1RSwWG0WVK5gmFosNoMCNcICDZgkGg+MooIv7/X4hm81qdRyNRndhNKxRRkZGOD6VSglo1Sk/X+GwSalUymJPVdUYhqxJxWJR3axtAsSfVxQlqao/dGPp3IBV4vF4ik2OYkNfgMoHcGhZrVbPU0qL6bQ2HY1o3K97d+97q9WqeJHTsNjPWF0jjzCqXVjDYLNCsVg8s7qaKZwyF7hULN6uaRh8O47y+TwXDofjdj0ZQGAoFDoei8W8v6oVNR6Ph9xutzERjWAONv6PpCOAiNR0oVAQu7u7aTgc5iqVioQpIZlM8qlUij906JAIxZVoNOpCCVEqlTq7AxSJRDZ1Cz6fz4fT2ePZt98X6e2dyGxs17icbKuBTHYw9R6NqSHsw2mYXbD5IQiwx67f5bnxE8fdJJtNs0yb6XJHEKQtnXB0dOzVhvSKdsnC4RUEzLDLJrKswNY/LUqb3qIU26dbWOjfI4oSuzVz+cpU0dDSApRYEWAo9a2k03/KOL9tkn29qlv+JwLQmSJuHsZXi1txKplc/uByuepSVj6yqWcQfqrIcj67vpZ93Cxw/sbdO4lPJrlpAYr9VvKF+cWHycXXj2eSlMXn32xUHEBWPB5jYxr/1m1bQOu10AzS30uDlEqBhXefauvrdyY/C3lzjpLLLPTxcD88+8AJAQo9gJ8UXjkCzLUZOXuMbYxS+htRiv0JCPkOKn7GVUkDxKYAAAAASUVORK5CYII=">
        """
        st.markdown(favicon, unsafe_allow_html=True)

        # Run the main application
        main()
    except Exception as e:
        st.error(f"Application error: {str(e)}")
        st.exception(e)

        # Provide recovery steps
        st.info("""
        ### Troubleshooting:
        1. Ensure all Python dependencies are installed
        2. Check if the data file exists and has proper permissions
        3. Restart the application
        """)
