# geo_int_act_1.py
import streamlit as st
import pandas as pd
import numpy as np
import requests
import geopy
import shapely
import json
import matplotlib.pyplot as plt

from datetime import datetime, timedelta
from geopy.geocoders import Nominatim
from shapely.geometry import shape, Point


# ------------------------------
# 1️⃣ Page setup
# ------------------------------
st.set_page_config(
    page_title="Geo-Intelligence Weather Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🌦 Geo-Intelligence Weather Dashboard")

# ------------------------------
# 2️⃣ Sidebar inputs
# ------------------------------
st.sidebar.header("Settings")

# Example bounding box: Mozambique (lat/lon)
BBOX = {"lat": (-26.9, -10.3), "lon": (30.2, 40.0)}

latitude = st.sidebar.slider("Latitude", float(BBOX["lat"][0]), float(BBOX["lat"][1]),  -25.0)
longitude = st.sidebar.slider("Longitude", float(BBOX["lon"][0]), float(BBOX["lon"][1]),  35.0)
days_back = st.sidebar.slider("Days back for historical data", 1, 7, 3)

# ------------------------------
# 3️⃣ Reverse geocoding
# ------------------------------
geolocator = Nominatim(user_agent="geo_intel_app")
location = geolocator.reverse((latitude, longitude), exactly_one=True)
nearest_place = location.address if location else "Unknown location"
st.subheader(f"📍 Selected Location: {nearest_place}")

# ------------------------------
# 4️⃣ Fetch weather data (placeholder)
# ------------------------------
st.subheader("🌧 Weather Data")

# Example: Mock data (replace with Open-Meteo API call if needed)
dates = [datetime.today() - timedelta(days=i) for i in range(days_back)]
dates.reverse()
rain_mm = np.random.randint(0, 30, size=days_back)
temperature = np.random.randint(20, 35, size=days_back)

weather_df = pd.DataFrame({
    "date": dates,
    "rain_mm": rain_mm,
    "temperature_C": temperature
})

st.dataframe(weather_df)

# ------------------------------
# 5️⃣ Plotting
# ------------------------------
fig, ax1 = plt.subplots(figsize=(10, 5))

ax1.bar(weather_df["date"], weather_df["rain_mm"], color='skyblue', label="Rain (mm)")
ax1.set_ylabel("Rain (mm)", color='blue')
ax1.tick_params(axis='y', labelcolor='blue')

ax2 = ax1.twinx()
ax2.plot(weather_df["date"], weather_df["temperature_C"], color='red', marker='o', label="Temp (°C)")
ax2.set_ylabel("Temperature (°C)", color='red')
ax2.tick_params(axis='y', labelcolor='red')

fig.autofmt_xdate()
plt.title(f"Daily Weather – {nearest_place}")
ax1.legend(loc="upper left")
ax2.legend(loc="upper right")

st.pyplot(fig)

# ------------------------------
# 6️⃣ Shapely Example: Point in Bounding Box
# ------------------------------
st.subheader("📌 Point in Bounding Box Check")
point = Point(longitude, latitude)
bbox_polygon = shape({
    "type": "Polygon",
    "coordinates": [[
        [BBOX["lon"][0], BBOX["lat"][0]],
        [BBOX["lon"][1], BBOX["lat"][0]],
        [BBOX["lon"][1], BBOX["lat"][1]],
        [BBOX["lon"][0], BBOX["lat"][1]],
        [BBOX["lon"][0], BBOX["lat"][0]]
    ]]
})

if bbox_polygon.contains(point):
    st.success("✅ Point is inside the bounding box.")
else:
    st.error("❌ Point is outside the bounding box.")
@st.cache_data(show_spinner=False)
def reverse_geocode(lat, lon):
    geolocator = Nominatim(user_agent="geo_intelligence_app")
    location = geolocator.reverse((lat, lon), exactly_one=True)
    return location.address if location else "Unknown"

# ─── Session State ─────────────────────────────────────────────────────────────
for key in ["mozambique", "lat", "lon", "nearest_place"]:
    if key not in st.session_state:
        st.session_state[key] = None

# ─── UI ────────────────────────────────────────────────────────────────────────
st.title("🌍 Weather Data – Core Setup")
st.markdown(
    """
This is the first step of the Geo-Intelligence app:
- Load Mozambique geography
- Pick a random location or enter coordinates
- Reverse geocode to nearest place
"""
)

# Load Mozambique polygon
with st.spinner("Loading Mozambique geography…"):
    if st.session_state.mozambique is None:
        st.session_state.mozambique = load_mozambique()
mozambique = st.session_state.mozambique

# ── Sidebar controls ──
with st.sidebar:
    st.header("⚙️ Controls")

    if st.button("🎲 Pick a random location in Mozambique", use_container_width=True):
        lat, lon = get_random_location_mozambique(mozambique)
        st.session_state.lat = lat
        st.session_state.lon = lon
        st.session_state.nearest_place = None

    st.markdown("---")
    st.caption("Or enter coordinates manually:")
    col1, col2 = st.columns(2)
    with col1:
        manual_lat = st.number_input("Latitude", value=-14.007674, format="%.6f")
    with col2:
        manual_lon = st.number_input("Longitude", value=36.519443, format="%.6f")

    if st.button("📍 Use these coordinates", use_container_width=True):
        st.session_state.lat = round(manual_lat, 6)
        st.session_state.lon = round(manual_lon, 6)
        st.session_state.nearest_place = None

# Require location
if st.session_state.lat is None:
    st.info("👈 Use the sidebar to pick a random location or enter coordinates.")
    st.stop()

lat, lon = st.session_state.lat, st.session_state.lon

# Reverse geocode
if st.session_state.nearest_place is None:
    with st.spinner("Reverse geocoding…"):
        st.session_state.nearest_place = reverse_geocode(lat, lon)

nearest_place = st.session_state.nearest_place

st.subheader(f"📍 Location: `{lat}, {lon}`")
st.caption(f"Nearest place: **{nearest_place}**")
