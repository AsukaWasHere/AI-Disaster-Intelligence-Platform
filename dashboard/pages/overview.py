import streamlit as st
import requests

API_URL = "http://127.0.0.1:8000"

def card(title, value):
    st.markdown(f"""
    <div class="glass">
        <h4>{title}</h4>
        <h2 style="color:#00C9A7;">{value}</h2>
    </div>
    """, unsafe_allow_html=True)

def run():
    st.header("📊 Overview")

    try:
        data = requests.get(f"{API_URL}/insights").json()

        c1, c2, c3 = st.columns(3)
        with c1: card("Total Events", data["total_events"])
        with c2: card("Avg Damage", f"${data['avg_damage_usd']:,.0f}")
        with c3: card("Avg Risk", f"{data['avg_risk_score']:.2f}")

        st.subheader("⚠️ High Risk States")
        st.write(" • ".join(data["high_risk_states"]))

    except:
        st.error("API error")