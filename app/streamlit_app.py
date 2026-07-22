"""Food Desert Map — Worcester County, MA. Run: streamlit run app/streamlit_app.py"""
import os

import folium
import geopandas as gpd
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine
from streamlit_folium import st_folium

load_dotenv()
st.set_page_config(page_title="Worcester County Food Access", layout="wide")


@st.cache_data(ttl=600)
def load_data() -> gpd.GeoDataFrame:
    engine = create_engine(os.environ["DATABASE_URL"])
    sql = """
        SELECT s.geoid, s.tract_name, s.total_pop,
               s.composite_score::float AS composite_score,
               s.severity_tier,
               s.poverty_rate::float   AS poverty_rate,
               s.pct_no_vehicle::float AS pct_no_vehicle,
               s.lila_flag, t.geom
        FROM food_desert_tracts s
        JOIN tracts t USING (geoid)
    """
    return gpd.read_postgis(sql, engine, geom_col="geom")


gdf = load_data()

st.title("Food Access in Worcester County, MA")
st.caption(
    "Composite score = 40% supermarket access + 35% poverty rate + "
    "25% households without a vehicle, normalized within the county. "
    "Outlined tracts are USDA-designated Low-Income Low-Access."
)

TIER_COLORS = {"Severe": "#b30000", "High": "#e34a33",
               "Moderate": "#fdbb84", "Low": "#fee8c8"}

m = folium.Map(location=[42.35, -71.90], zoom_start=10,
               tiles="cartodbpositron")

folium.GeoJson(
    gdf,
    style_function=lambda feat: {
        "fillColor": TIER_COLORS[feat["properties"]["severity_tier"]],
        "fillOpacity": 0.65,
        "color": "#333" if feat["properties"]["lila_flag"] else "#999",
        "weight": 2.0 if feat["properties"]["lila_flag"] else 0.5,
    },
    tooltip=folium.GeoJsonTooltip(
        fields=["tract_name", "composite_score", "severity_tier",
                "poverty_rate", "pct_no_vehicle"],
        aliases=["Tract", "Score", "Tier", "Poverty %", "No vehicle %"],
    ),
).add_to(m)

col_map, col_table = st.columns([2, 1])
with col_map:
    st_folium(m, height=650, use_container_width=True)
with col_table:
    st.subheader("Highest-need tracts")
    st.dataframe(
        gdf.sort_values("composite_score", ascending=False)
           [["tract_name", "composite_score", "severity_tier"]]
           .head(15),
        hide_index=True, use_container_width=True,
    )
    agree = gdf[gdf["lila_flag"]]["severity_tier"].isin(["Severe", "High"]).mean()
    st.metric("USDA LILA tracts landing in our top two tiers",
              f"{agree:.0%}")