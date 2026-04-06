# geo_int_act_1.py

# ------------------------------
# 1️⃣ Imports
# ------------------------------
import streamlit as st
import pandas as pd
import numpy as np
from datetime import date, timedelta
import matplotlib.pyplot as plt
import requests_cache
from tenacity import retry, stop_after_attempt, wait_fixed
from geopy.geocoders import Nominatim
from shapely.geometry import shape, Point, mapping, Polygon
import json
import random
import folium
from streamlit_folium import st_folium

# ------------------------------
# 2️⃣ Streamlit Page Setup
# ------------------------------
st.set_page_config(
    page_title="🌦 Geo-Intelligence Weather Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)
st.title("🌦 Geo-Intelligence Weather Dashboard")

# ------------------------------
# 3️⃣ Session State Defaults
# ------------------------------
for key in ["mozambique", "lat", "lon", "nearest_place"]:
    if key not in st.session_state:
        st.session_state[key] = None

# ------------------------------
# 4️⃣ Load Mozambique Polygon
# ------------------------------
@st.cache_data
def load_mozambique():
    with open("mozambique.geojson", "r", encoding="utf-8") as f:
        gj = json.load(f)
    if "features" in gj:
        return shape(gj["features"][0]["geometry"])
    return shape(gj)

if st.session_state.mozambique is None:
    st.session_state.mozambique = load_mozambique()

mozambique: Polygon = st.session_state.mozambique

# ------------------------------
# 4.1️⃣ Random Point Generator
# ------------------------------
def random_point_in_polygon(polygon: Polygon):
    minx, miny, maxx, maxy = polygon.bounds
    while True:
        p = Point(random.uniform(minx, maxx), random.uniform(miny, maxy))
        if polygon.contains(p):
            return p

# ------------------------------
# 5️⃣ Sidebar Controls
# ------------------------------
st.sidebar.header("⚙️ Controls")

if st.sidebar.button("🎲 Pick a random location in Mozambique"):
    p = random_point_in_polygon(mozambique)
    st.session_state.lat = round(p.y, 6)
    st.session_state.lon = round(p.x, 6)
    st.session_state.nearest_place = None

st.sidebar.markdown("---")
st.sidebar.caption("Or enter coordinates manually:")

# ✅ Vertical inputs (clean UX)
manual_lat = st.sidebar.number_input("Latitude", value=-14.007674, format="%.6f")
manual_lon = st.sidebar.number_input("Longitude", value=36.519443, format="%.6f")

if st.sidebar.button("📍 Use these coordinates"):
    st.session_state.lat = round(manual_lat, 6)
    st.session_state.lon = round(manual_lon, 6)
    st.session_state.nearest_place = None

# ------------------------------
# 6️⃣ Require Location
# ------------------------------
if st.session_state.lat is None or st.session_state.lon is None:
    st.info("👈 Use the sidebar to pick a location.")
    st.stop()

lat = st.session_state.lat
lon = st.session_state.lon

# ------------------------------
# 7️⃣ Reverse Geocoding
# ------------------------------
@st.cache_data(show_spinner=False)
def reverse_geocode(lat, lon):
    geolocator = Nominatim(user_agent="geo_intelligence_app")
    location = geolocator.reverse((lat, lon), exactly_one=True)
    return location.address if location else "Unknown"

if st.session_state.nearest_place is None:
    st.session_state.nearest_place = reverse_geocode(lat, lon)

nearest_place = st.session_state.nearest_place

st.subheader(f"📍 Location: {lat}, {lon}")
st.caption(f"Nearest place: **{nearest_place}**")

# ------------------------------
# 8️⃣ Point in Mozambique Check
# ------------------------------
point = Point(lon, lat)
if mozambique.contains(point):
    st.success("✅ Point is inside Mozambique.")
else:
    st.error("❌ Point is outside Mozambique.")

# ------------------------------
# 9️⃣ Weather Data
# ------------------------------
st.subheader("🌧 Weather Data (last 30 days)")

session = requests_cache.CachedSession(".cache", expire_after=86400)

@retry(stop=stop_after_attempt(5), wait=wait_fixed(1))
def fetch_weather(url, params):
    r = session.get(url, params=params)
    r.raise_for_status()
    return r.json()

end_date = date.today() - timedelta(days=1)
start_date = end_date - timedelta(days=30)

url = "https://archive-api.open-meteo.com/v1/archive"

params = {
    "latitude": lat,
    "longitude": lon,
    "start_date": start_date.isoformat(),
    "end_date": end_date.isoformat(),
    "daily": "precipitation_sum,temperature_2m_max,temperature_2m_min",
    "timezone": "UTC"
}

data = fetch_weather(url, params=params)["daily"]

df = pd.DataFrame({
    "date": pd.to_datetime(data["time"]),
    "rainfall_mm": data["precipitation_sum"],
    "temperature_max": data["temperature_2m_max"],
    "temperature_min": data["temperature_2m_min"]
})

# ------------------------------
# 🔟 Feature Engineering
# ------------------------------
df["temp_category"] = df["temperature_max"].apply(
    lambda x: 0 if x < 20 else (1 if x <= 30 else 2)
)

df["rain_flag"] = df["rainfall_mm"].apply(lambda x: 1 if x > 0 else 0)

df["extreme_flag"] = df.apply(
    lambda r: 1 if (r["rainfall_mm"] > 10 or r["temperature_max"] > 35) else 0,
    axis=1
)

# Synthetic revenue
np.random.seed(42)

def generate_revenue(row):
    revenue = 1000
    if row["rainfall_mm"] > 5:
        revenue *= 0.8
    if row["temperature_max"] > 30:
        revenue *= 1.1
    elif row["temperature_max"] < 20:
        revenue *= 0.9
    revenue *= np.random.uniform(0.9, 1.1)
    return round(revenue, 2)

df["synthetic_revenue"] = df.apply(generate_revenue, axis=1)

st.dataframe(df)

# ------------------------------
# 1️⃣1️⃣ Map
# ------------------------------
st.subheader("🗺 Location Map")

m = folium.Map(location=[lat, lon], zoom_start=6)

folium.Marker(
    location=[lat, lon],
    popup=f"<b>Selected Location:</b><br>{nearest_place}<br>Lat: {lat}<br>Lon: {lon}",
    tooltip="Click for details",
    icon=folium.Icon(color="red"),
    parse_html=True
).add_to(m)

moz_coords = mapping(mozambique)["coordinates"][0]

folium.PolyLine(
    locations=[(lat, lon) for lon, lat in moz_coords],
    color="blue",
    weight=2
).add_to(m)

st_folium(m, width=700, height=500)

# ------------------------------
# 1️⃣2️⃣ Plots
# ------------------------------
st.subheader("🌧 Rainfall & Temperature")

fig, ax1 = plt.subplots(figsize=(12, 5))
ax1.bar(df["date"], df["rainfall_mm"])

ax2 = ax1.twinx()
ax2.plot(df["date"], df["temperature_max"], marker="o")
ax2.plot(df["date"], df["temperature_min"], marker="x")

st.pyplot(fig)

# Revenue
st.subheader("💰 Rainfall vs Revenue")

fig, ax1 = plt.subplots(figsize=(12, 5))
ax1.bar(df["date"], df["rainfall_mm"])

ax2 = ax1.twinx()
ax2.plot(df["date"], df["synthetic_revenue"], marker="o")

st.pyplot(fig)
