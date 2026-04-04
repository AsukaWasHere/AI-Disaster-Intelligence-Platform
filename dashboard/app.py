import streamlit as st
from pages import overview, predictions, geospatial, insights

st.set_page_config(page_title="AI Disaster Intelligence", layout="wide")

# 🔥 GLOBAL CSS
st.markdown("""
<style>
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.glass {
    background: rgba(255,255,255,0.05);
    border-radius: 16px;
    padding: 20px;
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255,255,255,0.1);
}

.stButton > button {
    background: linear-gradient(135deg, #00C9A7, #00A8FF);
    color: white;
    border-radius: 10px;
    border: none;
    padding: 10px 20px;
    font-weight: 600;
}

.stButton > button:hover {
    transform: scale(1.05);
}

.block-container {
    padding-top: 2rem;
}
</style>
""", unsafe_allow_html=True)

# 🔥 HERO HEADER
st.markdown("""
<h1>🌪️ AI Disaster Intelligence</h1>
<p style="color:gray;">Real-time Risk Prediction & Insights</p>
""", unsafe_allow_html=True)

st.sidebar.title("⚡ Navigation")
page = st.sidebar.radio(
    "Navigation",   # ✅ proper label
    ["Overview", "Predictions", "Geospatial", "Insights"],
    label_visibility="collapsed"   # 🔥 hides label visually
)

if page == "Overview":
    overview.run()
elif page == "Predictions":
    predictions.run()
elif page == "Geospatial":
    geospatial.run()
elif page == "Insights":
    insights.run()