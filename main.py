"""
Resource Management Application Entry Point
"""

import streamlit as st
from app.app import main

if __name__ == "__main__":
    st.set_page_config(page_title="Resource Management App", layout="wide")
    main()
