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
    try:
        df = pd.read_csv(DATA_PATH)
        return df
    except FileNotFoundError:
        st.error(f"Data file not found at {DATA_PATH}. Please check the path and upload the data.")
        return pd.DataFrame()

def main():
    st.set_page_config(page_title="RBI-UCCS Policy Dashboard", layout="wide")
    st.title("RBI-UCCS Policy Analysis Dashboard")
    st.markdown("""
    This dashboard provides interactive visualizations for policy analysis using the consolidated UCCS survey data.
    """)

    df = load_data()
    if df.empty:
        st.stop()

    st.write("### Data Preview")
    st.dataframe(df.head(10))
    st.write(f"**Columns available:** {', '.join(df.columns)}")

    # Sidebar filters
    st.sidebar.header("Filters")
    if 'perception_category' in df.columns:
        perception_categories = df['perception_category'].dropna().unique().tolist()
    else:
        perception_categories = []
    if perception_categories:
        selected_categories = st.sidebar.multiselect(
            "Select Perception Categories:", perception_categories, default=perception_categories[:2]
        )
    else:
        selected_categories = []
    if 'perception_type' in df.columns:
        response_types = df['perception_type'].dropna().unique().tolist()
    else:
        response_types = []
    if response_types:
        selected_responses = st.sidebar.multiselect("Select Response Types:", response_types, default=response_types)
    else:
        selected_responses = []

    # Filtered Data
    if selected_categories and selected_responses:
        filtered_df = df[
            (df['perception_category'].isin(selected_categories)) &
            (df['perception_type'].isin(selected_responses))
        ]
    else:
        filtered_df = df.copy()

    # Trend Analysis
    st.subheader("Trend Analysis")
    if not filtered_df.empty:
        # Group by survey_round, perception_category, perception_type, response_category
        # and plot lines for each response_type and response_category
        trend_fig = px.line(
            filtered_df,
            x='survey_round',
            y='response_percentage',
            color='response_category',
            line_dash='perception_type',
            markers=True,
            title=f"Trend of Response Categories by Response Type"
        )
        st.plotly_chart(trend_fig, use_container_width=True)
    else:
        st.info("No data available for the selected filters.")

    # Comparative View (Optional)
    st.subheader("Comparative View (Current vs. One Year Ahead)")
    if perception_categories:
        indicator = st.selectbox("Select Indicator:", perception_categories)
    else:
        indicator = None
    if 'survey_round' in df.columns:
        round_options = df['survey_round'].dropna().unique().tolist()
    else:
        round_options = []
    if round_options:
        selected_round = st.selectbox("Select Survey Round:", round_options)
    else:
        selected_round = None
    if indicator and selected_round:
        comp_df = df[(df['perception_category'] == indicator) & (df['survey_round'] == selected_round)]
        if not comp_df.empty:
            comp_fig = px.bar(
                comp_df,
                x='response_category',
                y='response_percentage',
                color='perception_type',
                barmode='group',
                title=f"Comparative View for {indicator} ({selected_round})"
            )
            st.plotly_chart(comp_fig, use_container_width=True)
        else:
            st.info("No comparative data available for the selected indicator and round.")

    # Data Export (Optional)
    st.subheader("Export Filtered Data")
    if not filtered_df.empty:
        st.download_button(
            label="Download Filtered Data as CSV",
            data=filtered_df.to_csv(index=False),
            file_name="filtered_uccs_data.csv",
            mime="text/csv"
        )
    else:
        st.info("No filtered data to export.")

    # Drill-down Table (Optional)
    st.subheader("Detailed Data Table")
    st.dataframe(filtered_df)

if __name__ == "__main__":
    main()
