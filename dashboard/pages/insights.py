import streamlit as st
import requests
import pandas as pd
import plotly.express as px

API_URL = "http://127.0.0.1:8000"

def run():
    st.header("📈 Insights")

    try:
        data = requests.get(f"{API_URL}/insights").json()

        counts = [x["count"] for x in data["top_event_types"]]

        df = pd.DataFrame({
            "Category": list(range(1, len(counts)+1)),
            "Count": counts
        })

        fig = px.bar(df, x="Category", y="Count", title="Top Event Types")

        fig.update_layout(
            plot_bgcolor="#0E1117",
            paper_bgcolor="#0E1117",
            font_color="white"
        )

        st.plotly_chart(fig, use_container_width=True)

    except:
        st.error("API error")