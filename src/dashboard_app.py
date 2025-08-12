"""
Interactive Dashboard for Policy Analysis (RBI-UCCS)
---------------------------------------------------

This Streamlit app visualizes trends, comparative views, and snapshots from the
consolidated RBI Urban Households' Inflation Expectations Survey (UCCS) data.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import os

# --- Page Configuration ---
st.set_page_config(
    page_title="RBI-UCCS Policy Dashboard",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Data Loading ---
@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    """
    Loads and preprocesses the UCCS data from a CSV file.
    Converts 'survey_round' to datetime objects for proper sorting.
    """
    try:
        df = pd.read_csv(path)
        # Convert survey_round to datetime for correct chronological sorting
        df['survey_round_dt'] = pd.to_datetime(df['survey_round'], errors='coerce')
        df = df.dropna(subset=['survey_round_dt']).sort_values('survey_round_dt')
        return df
    except FileNotFoundError:
        st.error(f"🚨 Data file not found at `{path}`. Please ensure your project has the correct folder structure.")
        return pd.DataFrame()

# --- UI Components ---
def display_sidebar(df: pd.DataFrame):
    """
    Renders the sidebar with all the interactive filter widgets.
    """
    st.sidebar.header("📊 Dashboard Filters")

    # Filter by Perception Category
    perception_categories = df['perception_category'].dropna().unique().tolist()
    selected_categories = st.sidebar.multiselect(
        "Select Perception Categories:",
        options=perception_categories,
        default=perception_categories[:2] if len(perception_categories) > 1 else perception_categories
    )

    # Filter by Perception Type
    perception_types = df['perception_type'].dropna().unique().tolist()
    selected_types = st.sidebar.multiselect(
        "Select Perception Types:",
        options=perception_types,
        default=perception_types
    )

    # Dynamic metric selection for the y-axis
    numeric_columns = df.select_dtypes(include='number').columns.tolist()
    numeric_columns = [col for col in numeric_columns if 'dt' not in col]
    selected_metric = st.sidebar.selectbox(
        "Select Metric for Trend Analysis:",
        options=numeric_columns,
        index=numeric_columns.index('response_percentage') if 'response_percentage' in numeric_columns else 0
    )

    return selected_categories, selected_types, selected_metric

def display_trend_tab(df: pd.DataFrame, metric: str):
    """
    Renders the 'Trend Analysis' tab with a line chart.
    """
    st.subheader(f"📈 Trend of Perceptions Over Time")

    if df.empty:
        st.warning("No data available for the selected filters. Please adjust your selections.")
        return

    # Create the trend chart
    trend_fig = px.line(
        df,
        x='survey_round_dt',
        y=metric,
        color='response_category',
        line_dash='perception_type',
        markers=True,
        title=f"Trend of '{metric.replace('_', ' ').title()}' by Perception",
        labels={
            "survey_round_dt": "Survey Round",
            metric: metric.replace('_', ' ').title(),
            "response_category": "Response Category",
            "perception_type": "Perception Horizon"
        },
        template="plotly_white"
    )
    trend_fig.update_layout(legend_title_text='Legend')
    st.plotly_chart(trend_fig, use_container_width=True)
    st.caption("This chart shows how different response categories have evolved across survey rounds. Use the legend to toggle lines.")

def display_comparison_tab(df: pd.DataFrame):
    """
    Renders the 'Comparative Insight' tab with grouped bar charts.
    """
    st.subheader("🔍 Comparative Insight Between Survey Rounds")

    all_rounds = df['survey_round'].unique()

    if len(all_rounds) < 2:
        st.info("You need at least two survey rounds in your filtered data to make a comparison.")
        return

    col1, col2 = st.columns(2)
    with col1:
        round1 = st.selectbox("Select Base Round:", options=all_rounds, index=len(all_rounds)-2)
    with col2:
        round2 = st.selectbox("Select Comparison Round:", options=all_rounds, index=len(all_rounds)-1)

    comp_df = df[df['survey_round'].isin([round1, round2])]

    if comp_df.empty:
        st.warning("No data to compare for the selected rounds and filters.")
        return

    comp_fig = px.bar(
        comp_df,
        x='perception_category',
        y='response_percentage',
        color='survey_round',
        barmode='group',
        facet_col='response_category',
        facet_col_wrap=3,
        title=f"Comparison of Responses: {round1} vs. {round2}",
        labels={
            "response_percentage": "Response Percentage (%)",
            "perception_category": "Perception Category",
            "survey_round": "Survey Round"
        },
        height=500
    )
    comp_fig.update_layout(legend_title_text='Survey Round')
    st.plotly_chart(comp_fig, use_container_width=True)
    st.caption(f"This view contrasts response percentages for selected categories between two different survey rounds.")

def display_snapshot_tab(df: pd.DataFrame):
    """
    Renders the 'Period Snapshot' tab with donut charts for a single round.
    """
    st.subheader("🎯 Period Snapshot")
    all_rounds = df['survey_round'].unique()

    if not all_rounds.any():
        st.warning("No survey rounds available in the filtered data.")
        return

    selected_round = st.selectbox(
        "Select a Survey Round to Analyze:",
        options=all_rounds,
        index=len(all_rounds)-1,
        key="snapshot_round"
    )

    snapshot_df = df[df['survey_round'] == selected_round]

    if snapshot_df.empty:
        st.warning(f"No data available for {selected_round} with current filters.")
        return

    snapshot_categories = snapshot_df['perception_category'].unique()

    if not snapshot_categories.any():
        st.info("No perception categories to display for this round.")
        return

    cols = st.columns(min(len(snapshot_categories), 4))

    for i, category in enumerate(snapshot_categories):
        cat_df = snapshot_df[snapshot_df['perception_category'] == category]
        with cols[i % 4]:
            fig = px.pie(
                cat_df,
                values='response_percentage',
                names='response_category',
                title=f"{category}",
                hole=0.4,
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            fig.update_layout(showlegend=False, margin=dict(t=40, b=0, l=0, r=0))
            st.plotly_chart(fig, use_container_width=True)

# --- Main Application ---
def main():
    """
    Main function to run the Streamlit application.
    """
    st.title("🏦 RBI UCCS Policy Analysis Dashboard")
    st.markdown("""
    Welcome to the interactive dashboard for the **RBI's Survey of Urban Households on Inflation and Economic Perceptions**.
    Use the filters on the left to explore trends, compare survey rounds, and analyze public perception data.
    """)
    st.markdown("---")

    DATA_PATH = os.path.join(
        os.path.dirname(__file__),
        '../data/processed/consolidated_uccs_data.csv'
    )

    df = load_data(DATA_PATH)
    if df.empty:
        st.stop()

    selected_categories, selected_types, selected_metric = display_sidebar(df)

    if not selected_categories or not selected_types:
        st.warning("Please select at least one perception category and one perception type from the sidebar.")
        st.stop()

    filtered_df = df[
        (df['perception_category'].isin(selected_categories)) &
        (df['perception_type'].isin(selected_types))
    ]

    if filtered_df.empty:
        st.warning("No data matches the current filter criteria. Please broaden your selections.")
        st.stop()

    # --- Analysis Tabs ---
    tab1, tab2, tab3 = st.tabs(["📊 Trend Analysis", "⚖️ Comparative Insight", "📸 Period Snapshot"])

    with tab1:
        display_trend_tab(filtered_df, selected_metric)

    with tab2:
        display_comparison_tab(filtered_df)

    with tab3:
        display_snapshot_tab(filtered_df)

    # --- Data Explorer ---
    with st.expander("🔍 Data Explorer"):
        st.dataframe(filtered_df, use_container_width=True)
        csv = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Filtered Data as CSV",
            data=csv,
            file_name="filtered_uccs_data.csv",
            mime="text/csv",
        )

if __name__ == "__main__":
    main()



    # ajaychoudhary@Ajays-MacBook-Pro rbi-uccs-ajay-clean % cd "/Users/ajaychoudhary/Documents/Data Research Fellow Task/rbi-uccs-ajay-clean" && cp ../rbi-uccs-ajay/src/dashboard_app.py src/dashboard_app.py && git add src/dashboard_app.py && git commit -m "Sort trend analysis data by survey_round for correct chart order" && git push;  cd -