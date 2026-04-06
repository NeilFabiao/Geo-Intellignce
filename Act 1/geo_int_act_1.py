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
# 4️⃣ Load Mozambique Polygon from GeoJSON
# ------------------------------
@st.cache_data
def load_mozambique():
    with open("mozambique.geojson", "r", encoding="utf-8") as f:
        gj = json.load(f)
    if "features" in gj:
        return shape(gj["features"][0]["geometry"])
    else:
        return shape(gj)

if st.session_state.mozambique is None:
    st.session_state.mozambique = load_mozambique()
mozambique: Polygon = st.session_state.mozambique

# ------------------------------
# 4.1️⃣ Random point inside polygon
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

# Random location
if st.sidebar.button("🎲 Pick a random location in Mozambique"):
    p = random_point_in_polygon(mozambique)
    st.session_state.lat = round(p.y, 6)
    st.session_state.lon = round(p.x, 6)
    st.session_state.nearest_place = None

# Manual coordinates
st.sidebar.markdown("---")
st.sidebar.caption("Or enter coordinates manually:")
col1, col2 = st.sidebar.columns(2)
with col1:
    manual_lat = st.number_input("Latitude", value=-14.007674, format="%.6f")
with col2:
    manual_lon = st.number_input("Longitude", value=36.519443, format="%.6f")

if st.sidebar.button("📍 Use these coordinates"):
    st.session_state.lat = round(manual_lat, 6)
    st.session_state.lon = round(manual_lon, 6)
    st.session_state.nearest_place = None

# ------------------------------
# 6️⃣ Require Location
# ------------------------------
if st.session_state.lat is None or st.session_state.lon is None:
    st.info("👈 Use the sidebar to pick a random location or enter coordinates.")
    st.stop()

lat = st.session_state.lat
lon = st.session_state.lon

# Validate numbers
if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
    st.error("Latitude or longitude not set correctly. Please pick a location.")
    st.stop()

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
st.subheader(f"📍 Location: `{lat}, {lon}`")
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
# 9️⃣ Fetch Real Weather Data
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
# 10️⃣ Process Data
# ------------------------------
def temp_category(max_temp):
    if max_temp < 20:
        return 0
    elif max_temp <= 30:
        return 1
    else:
        return 2

df["temp_category"] = df["temperature_max"].apply(temp_category)
df["rain_flag"] = df["rainfall_mm"].apply(lambda x: 1 if x > 0 else 0)
df["extreme_flag"] = df.apply(lambda row: 1 if (row["rainfall_mm"] > 10 or row["temperature_max"] > 35) else 0, axis=1)

# Synthetic revenue
base_revenue = 1000
np.random.seed(42)
def generate_revenue(row):
    revenue = base_revenue
    if row['rainfall_mm'] > 5:
        revenue *= 0.8
    if row['temperature_max'] > 30:
        revenue *= 1.1
    elif row['temperature_max'] < 20:
        revenue *= 0.9
    revenue *= np.random.uniform(0.9, 1.1)
    return round(revenue, 2)

# ------------------------------
# 11️⃣ Show Map
# ------------------------------
st.subheader("🗺 Location Map")

m = folium.Map(location=[lat, lon], zoom_start=6)
folium.Marker(
    location=[lat, lon],
    popup=f"Selected Location:\n{nearest_place}",
    tooltip="Click for details",
    icon=folium.Icon(color="red", icon="info-sign")
).add_to(m)

folium.Marker(
    location=[lat, lon],
    popup=f"<b>Selected Location:</b><br>{nearest_place}",
    tooltip="Click for details",
    icon=folium.Icon(color="red", icon="info-sign"),
    parse_html=True
).add_to(m)

# Mozambique polygon from GeoJSON
moz_coords = mapping(mozambique)["coordinates"][0]
folium.PolyLine(locations=[(lat, lon) for lon, lat in moz_coords], color="blue", weight=2).add_to(m)

st_folium(m, width=700, height=500)

df['synthetic_revenue'] = df.apply(generate_revenue, axis=1)
st.dataframe(df)

# ------------------------------
# 12️⃣ Plots
# ------------------------------
# Rainfall & Temperature
st.subheader("🌧 Rainfall & Temperature")
fig, ax1 = plt.subplots(figsize=(12,5))
ax1.bar(df['date'], df['rainfall_mm'], color='skyblue', label='Rainfall (mm)')
ax1.set_ylabel("Rainfall (mm)", color='skyblue')
ax1.tick_params(axis='y', labelcolor='skyblue')
plt.setp(ax1.get_xticklabels(), rotation=45, ha='right')

ax2 = ax1.twinx()
ax2.plot(df['date'], df['temperature_max'], color='red', marker='o', label='Max Temp (°C)')
ax2.plot(df['date'], df['temperature_min'], color='orange', marker='x', label='Min Temp (°C)')
ax2.set_ylabel("Temperature (°C)", color='red')
ax2.tick_params(axis='y', labelcolor='red')

lines_1, labels_1 = ax1.get_legend_handles_labels()
lines_2, labels_2 = ax2.get_legend_handles_labels()
ax2.legend(lines_1 + lines_2, labels_1 + labels_2, loc='upper right')
st.pyplot(fig)

# Max Temperature by Category
st.subheader("🌡 Max Temperature by Category")
colors = {0:'blue', 1:'green', 2:'red'}
labels = {0:'Cold (<20°C)', 1:'Moderate (20-30°C)', 2:'Hot (>30°C)'}
fig, ax = plt.subplots(figsize=(12,6))
for t in df['temp_category'].unique():
    subset = df[df['temp_category']==t]
    ax.scatter(subset['date'], subset['temperature_max'], color=colors[t], label=labels[t], s=80)
ax.set_xlabel("Date")
ax.set_ylabel("Max Temp (°C)")
ax.set_title("Max Temperature by Category")
ax.legend(title="Temperature Categories")
plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
st.pyplot(fig)

# Rainfall vs Revenue
st.subheader("💰 Rainfall vs Synthetic Revenue")
fig, ax1 = plt.subplots(figsize=(12,5))
ax1.bar(df['date'], df['rainfall_mm'], color='skyblue', label='Rainfall (mm)')
ax1.set_xlabel("Date")
ax1.set_ylabel("Rainfall (mm)", color='skyblue')
ax1.tick_params(axis='y', labelcolor='skyblue')
plt.setp(ax1.get_xticklabels(), rotation=45, ha='right')

ax2 = ax1.twinx()
ax2.plot(df['date'], df['synthetic_revenue'], color='red', marker='o', label='Revenue')
ax2.set_ylabel("Revenue", color='red')
ax2.tick_params(axis='y', labelcolor='red')

lines_1, labels_1 = ax1.get_legend_handles_labels()
lines_2, labels_2 = ax2.get_legend_handles_labels()
ax2.legend(lines_1 + lines_2, labels_1 + labels_2, loc='upper right')
st.pyplot(fig)
