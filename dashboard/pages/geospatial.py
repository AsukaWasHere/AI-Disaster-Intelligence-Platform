import streamlit as st
import folium
from streamlit_folium import st_folium

def run():
    st.header("🌍 Global Risk Map")

    m = folium.Map(location=[20, 0], zoom_start=2, tiles="CartoDB dark_matter")

    folium.CircleMarker(
        location=[35.22, -80.82],
        radius=10,
        color="red",
        fill=True,
        fill_opacity=0.7,
        popup="High Risk Area"
    ).add_to(m)

    st_folium(m, width=900)