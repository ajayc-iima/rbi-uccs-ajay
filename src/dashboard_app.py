"""
Interactive Dashboard for Policy Analysis (RBI-UCCS)
---------------------------------------------------

This Streamlit app visualizes trends and comparative views from the consolidated UCCS data.
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import os

DATA_PATH = os.path.join(
    os.path.dirname(__file__),
    '../data/processed/consolidated_uccs_data.csv'
)

@st.cache_data
def load_data():
    df = pd.read_csv(DATA_PATH)
    return df

def main():
    st.set_page_config(page_title="RBI-UCCS Policy Dashboard", layout="wide")
    st.title("RBI-UCCS Policy Analysis Dashboard")
    st.markdown("""
    This dashboard provides interactive visualizations for policy analysis using the consolidated UCCS survey data.
    """)

    df = load_data()

    # Sidebar filters
    st.sidebar.header("Filters")
    perception_categories = df['perception_category'].unique().tolist()
    selected_categories = st.sidebar.multiselect(
        "Select Perception Categories:", perception_categories, default=perception_categories[:2]
    )
    response_types = ['Current Perception', 'One Year Ahead Expectation']
    selected_response = st.sidebar.radio("Response Type:", response_types)

    # Filtered Data
    filtered_df = df[
        (df['perception_category'].isin(selected_categories)) &
        (df['response_type'] == selected_response)
    ]

    # Trend Analysis
    st.subheader("Trend Analysis")
    trend_fig = px.line(
        filtered_df,
        x='survey_round',
        y='response_percentage',
        color='response_category',
        line_dash='perception_category',
        markers=True,
        title=f"Trend of Response Categories ({selected_response})"
    )
    st.plotly_chart(trend_fig, use_container_width=True)

    # Comparative View (Optional)
    st.subheader("Comparative View (Current vs. One Year Ahead)")
    indicator = st.selectbox("Select Indicator:", perception_categories)
    round_options = df['survey_round'].unique().tolist()
    selected_round = st.selectbox("Select Survey Round:", round_options)
    comp_df = df[(df['perception_category'] == indicator) & (df['survey_round'] == selected_round)]
    comp_fig = px.bar(
        comp_df,
        x='response_category',
        y='response_percentage',
        color='response_type',
        barmode='group',
        title=f"Comparative View for {indicator} ({selected_round})"
    )
    st.plotly_chart(comp_fig, use_container_width=True)

    # Data Export (Optional)
    st.subheader("Export Filtered Data")
    st.download_button(
        label="Download Filtered Data as CSV",
        data=filtered_df.to_csv(index=False),
        file_name="filtered_uccs_data.csv",
        mime="text/csv"
    )

    # Drill-down Table (Optional)
    st.subheader("Detailed Data Table")
    st.dataframe(filtered_df)

if __name__ == "__main__":
    main()
