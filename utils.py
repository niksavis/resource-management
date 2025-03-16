import streamlit as st
import pandas as pd
from data_handlers import filter_dataframe


def display_filtered_resource(data_key: str, label: str):
    """
    Converts session data to a DataFrame, applies filter_dataframe,
    and displays the results.
    """
    data = st.session_state.data[data_key]
    if data:
        df = pd.DataFrame(data)
        filtered_df = filter_dataframe(df, data_key)
        st.dataframe(filtered_df, use_container_width=True)
    else:
        st.warning(f"No {label} found. Please add some first.")
