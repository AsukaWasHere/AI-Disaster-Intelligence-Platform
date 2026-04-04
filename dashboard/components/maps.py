# dashboard/components/maps.py
import folium
from folium.plugins import HeatMap, MarkerCluster
import pandas as pd


def build_risk_heatmap(df: pd.DataFrame) -> folium.Map:
    """Build a Folium risk heatmap from event records with lat/lon."""
    geo_df = df.dropna(subset=["BEGIN_LAT", "BEGIN_LON", "RISK_SCORE"])

    m = folium.Map(
        location=[38.5, -96.0],   # Continental US center
        zoom_start=4,
        tiles="CartoDB positron",
    )

    heat_data = geo_df[["BEGIN_LAT", "BEGIN_LON", "RISK_SCORE"]].values.tolist()
    HeatMap(heat_data, radius=12, blur=8, max_zoom=10).add_to(m)

    return m


def build_cluster_map(df: pd.DataFrame) -> folium.Map:
    """Marker cluster map with event-level popups."""
    geo_df = df.dropna(subset=["BEGIN_LAT", "BEGIN_LON"])

    m = folium.Map(location=[38.5, -96.0], zoom_start=4, tiles="CartoDB positron")
    cluster = MarkerCluster().add_to(m)

    for _, row in geo_df.iterrows():
        popup_text = (
            f"<b>{row['EVENT_TYPE']}</b><br>"
            f"State: {row['STATE']}<br>"
            f"Risk Score: {row.get('RISK_SCORE', 'N/A'):.1f}<br>"
            f"Damage: ${row.get('TOTAL_DAMAGE_USD', 0):,.0f}"
        )
        folium.Marker(
            location=[row["BEGIN_LAT"], row["BEGIN_LON"]],
            popup=folium.Popup(popup_text, max_width=200),
        ).add_to(cluster)

    return m