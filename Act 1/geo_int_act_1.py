import streamlit as st
import random
import json
import urllib.request
from shapely.geometry import shape, Point
from geopy.geocoders import Nominatim

# ─── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="🌍 Geo Intelligence – Mozambique Weather",
    page_icon="🌍",
    layout="wide",
)

# ─── Helpers ──────────────────────────────────────────────────────────────────
BBOX = {"lat": (-26.9, -10.3), "lon": (30.2, 40.8)}  # Mozambique bounding box

@st.cache_data(show_spinner=False)
def load_mozambique():
    """Load Mozambique polygon from GeoJSON."""
    url = "https://raw.githubusercontent.com/datasets/geo-countries/master/data/countries.geojson"
    with urllib.request.urlopen(url) as r:
        data = json.loads(r.read())
    for feature in data["features"]:
        props = feature.get("properties", {})
        if props.get("ISO3166-1-Alpha-3") == "MOZ":
            return shape(feature["geometry"])
    raise ValueError("Mozambique not found in GeoJSON")

def get_random_location_mozambique(mozambique_shape):
    """Return a random (lat, lon) strictly inside Mozambique."""
    while True:
        lat = random.uniform(*BBOX["lat"])
        lon = random.uniform(*BBOX["lon"])
        if mozambique_shape.contains(Point(lon, lat)):
            return round(lat, 6), round(lon, 6)

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
