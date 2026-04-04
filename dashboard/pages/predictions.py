import streamlit as st
import requests

API_URL = "http://127.0.0.1:8000"

def run():
    st.header("🔮 AI Prediction")

    # 🔥 GLASS INPUT CARD
    st.markdown('<div class="glass">', unsafe_allow_html=True)

    c1, c2 = st.columns(2)

    with c1:
        lat = st.number_input("Latitude", value=35.0)
        lon = st.number_input("Longitude", value=-80.0)
        month = st.slider("Month", 1, 12, 5)

    with c2:
        magnitude = st.slider("Magnitude", 0.0, 10.0, 5.0)
        narrative = st.text_area("Event Description")

    st.markdown('</div>', unsafe_allow_html=True)

    if st.button("🚀 Run Prediction"):
        payload = {
            "lat": lat,
            "lon": lon,
            "month": month,
            "magnitude": magnitude,
            "narrative": narrative
        }

        try:
            with st.spinner("Running AI model..."):
                data = requests.post(f"{API_URL}/predict", json=payload).json()

            # 🔥 RESULT CARD
            st.markdown(f"""
            <div class="glass">
                <h2 style="color:#00C9A7;">🌪️ {data['event_type']}</h2>
                <p><b>Damage:</b> ${data['damage_usd']:,.0f}</p>
                <p><b>Risk Score:</b> {data['risk_score']}</p>
            </div>
            """, unsafe_allow_html=True)

            st.subheader("📊 Top Predictions")
            for p in data["top_predictions"]:
                st.write(p["label"])
                st.progress(p["probability"])

            st.info(data["explanation"])

        except:
            st.error("Prediction failed") 
            import streamlit as st
import requests

API_URL = "http://127.0.0.1:8000"

def run():
    st.header("🔮 AI Prediction")

    # 🔥 GLASS INPUT CARD
    st.markdown('<div class="glass">', unsafe_allow_html=True)

    c1, c2 = st.columns(2)

    with c1:
        lat = st.number_input("Latitude", value=35.0)
        lon = st.number_input("Longitude", value=-80.0)
        month = st.slider("Month", 1, 12, 5)

    with c2:
        magnitude = st.slider("Magnitude", 0.0, 10.0, 5.0)
        narrative = st.text_area("Event Description")

    st.markdown('</div>', unsafe_allow_html=True)

    if st.button("🚀 Run Prediction"):
        payload = {
            "lat": lat,
            "lon": lon,
            "month": month,
            "magnitude": magnitude,
            "narrative": narrative
        }

        try:
            with st.spinner("Running AI model..."):
                data = requests.post(f"{API_URL}/predict", json=payload).json()

            # 🔥 RESULT CARD
            st.markdown(f"""
            <div class="glass">
                <h2 style="color:#00C9A7;">🌪️ {data['event_type']}</h2>
                <p><b>Damage:</b> ${data['damage_usd']:,.0f}</p>
                <p><b>Risk Score:</b> {data['risk_score']}</p>
            </div>
            """, unsafe_allow_html=True)

            st.subheader("📊 Top Predictions")
            for p in data["top_predictions"]:
                st.write(p["label"])
                st.progress(p["probability"])

            st.info(data["explanation"])

        except:
            st.error("Prediction failed")