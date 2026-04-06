import streamlit as st
import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from shapely.geometry import shape, Point
from geopy.geocoders import Nominatim
from datetime import date, timedelta
import random
import json
import urllib.request

# ─── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="🌍 Geo Intelligence – Mozambique Weather",
    page_icon="🌍",
    layout="wide",
)

# ─── Helpers (cached) ──────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def load_mozambique():
    """Load Mozambique polygon from GeoJSON (cached)."""
    url = "https://raw.githubusercontent.com/datasets/geo-countries/master/data/countries.geojson"
    with urllib.request.urlopen(url) as r:
        data = json.loads(r.read())
    for feature in data["features"]:
        props = feature.get("properties", {})
        if props.get("ISO3166-1-Alpha-3") == "MOZ":
            return shape(feature["geometry"])
    raise ValueError("Mozambique not found in GeoJSON")


BBOX = {"lat": (-26.9, -10.3), "lon": (30.2, 40.8)}

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


@st.cache_data(show_spinner=False)
def fetch_weather(lat, lon):
    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=30)
    
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "daily": "precipitation_sum,temperature_2m_max,temperature_2m_min",
        "timezone": "UTC",
    }

    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()
    daily = data["daily"]

    dates = pd.to_datetime(daily["time"]).date
    rainfall_mm = daily["precipitation_sum"]
    temperature_max = daily["temperature_2m_max"]
    temperature_min = daily["temperature_2m_min"]

    df = pd.DataFrame({
        "latitude": lat,
        "longitude": lon,
        "date": dates,
        "rainfall_mm": rainfall_mm,
        "temperature_2m_max": temperature_max,
        "temperature_2m_min": temperature_min,
    })

    def temp_category(max_temp):
        if max_temp < 20:
            return 0
        elif max_temp <= 30:
            return 1
        else:
            return 2

    df["temp_category"] = df["temperature_2m_max"].apply(temp_category)
    df["rain_flag"] = df["rainfall_mm"].apply(lambda x: 1 if x > 0 else 0)
    df["extreme_flag"] = df.apply(
        lambda row: 1 if (row["rainfall_mm"] > 10 or row["temperature_2m_max"] > 35) else 0,
        axis=1,
    )
    return df


def generate_revenue(df, seed=42):
    np.random.seed(seed)
    base_revenue = 1000

    def calc(row):
        rev = base_revenue
        if row["rainfall_mm"] > 5:
            rev *= 0.8
        if row["temperature_2m_max"] > 30:
            rev *= 1.1
        elif row["temperature_2m_max"] < 20:
            rev *= 0.9
        rev *= np.random.uniform(0.9, 1.1)
        return round(rev, 2)

    df = df.copy()
    df["synthetic_revenue"] = df.apply(calc, axis=1)
    return df


# ─── Session State ─────────────────────────────────────────────────────────────
for key in ["mozambique", "lat", "lon", "nearest_place", "df"]:
    if key not in st.session_state:
        st.session_state[key] = None

# ─── UI ────────────────────────────────────────────────────────────────────────
st.title("🌍 Weather Data – First Step into Geo Intelligence")
st.markdown(
    """
Every morning, before stepping outside, we check the weather on our phones.
Will it rain? ☔ Is it hot? Do we need a jacket?

This app is a starting point for a broader journey into **Geo-Intelligence** —
using location-based data to support smarter decisions. Weather is our fun
first layer of a **location intelligence framework**.
"""
)

st.divider()

# ── Load Mozambique (once) ──
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
        st.session_state.df = None

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
        st.session_state.df = None

# ── Require a location ──
if st.session_state.lat is None:
    st.info("👈 Use the sidebar to pick a random location or enter coordinates.")
    st.stop()

lat = st.session_state.lat
lon = st.session_state.lon

# ── Reverse geocode ──
if st.session_state.nearest_place is None:
    with st.spinner("Reverse geocoding…"):
        st.session_state.nearest_place = reverse_geocode(lat, lon)

nearest_place = st.session_state.nearest_place

st.subheader(f"📍 Location: `{lat}, {lon}`")
st.caption(f"Nearest place: **{nearest_place}**")

# ── Fetch weather ──
if st.session_state.df is None:
    with st.spinner("Fetching weather data from Open-Meteo archive…"):
        df_base = fetch_weather(lat, lon)
        st.session_state.df = generate_revenue(df_base)

df = st.session_state.df

# ─── KPI cards ──────────────────────────────────────────────────────────────────
st.divider()
st.subheader("📊 30-day summary")

k1, k2, k3, k4 = st.columns(4)
k1.metric("☔ Total Rainfall", f"{df['rainfall_mm'].sum():.1f} mm")
k2.metric("🌡️ Avg Max Temp", f"{df['temperature_2m_max'].mean():.1f} °C")
k3.metric("🌡️ Avg Min Temp", f"{df['temperature_2m_min'].mean():.1f} °C")
k4.metric("⚡ Extreme-weather days", int(df["extreme_flag"].sum()))

# ─── Data table ─────────────────────────────────────────────────────────────────
with st.expander("📋 View raw data table"):
    st.dataframe(
        df.rename(columns={
            "date": "Date",
            "rainfall_mm": "Rainfall (mm)",
            "temperature_2m_max": "Max Temp (°C)",
            "temperature_2m_min": "Min Temp (°C)",
            "temp_category": "Temp Category (0=Cold, 1=Mod, 2=Hot)",
            "rain_flag": "Rain Flag",
            "extreme_flag": "Extreme Flag",
            "synthetic_revenue": "Synthetic Revenue",
        }),
        use_container_width=True,
        hide_index=True,
    )

# ─── Chart helpers ───────────────────────────────────────────────────────────────
dates_plot = pd.to_datetime(df["date"])

def make_fig(figsize=(10, 4)):
    fig, ax = plt.subplots(figsize=figsize)
    return fig, ax

# ── Chart 1 – Rainfall + Temperature ──
st.divider()
st.subheader("📈 Daily Rainfall & Temperature")

fig1, ax1 = make_fig()
ax1.plot(dates_plot, df["rainfall_mm"], label="Rainfall (mm)", color="blue", marker="o", markersize=4)
ax1.plot(dates_plot, df["temperature_2m_max"], label="Max Temp (°C)", color="red", marker="x", markersize=5)
ax1.plot(dates_plot, df["temperature_2m_min"], label="Min Temp (°C)", color="orange", marker="x", markersize=5)
ax1.set_title(f"Daily Weather – {nearest_place}", fontsize=11)
ax1.set_xlabel("Date")
ax1.set_ylabel("Rainfall / Temperature")
ax1.tick_params(axis="x", rotation=45)
ax1.legend()
ax1.grid(True)
fig1.tight_layout()
st.pyplot(fig1)

# ── Chart 2 – Rainfall bars ──
st.divider()
st.subheader("🌧️ Daily Rainfall (bar chart)")

fig2, ax2 = make_fig()
ax2.bar(dates_plot, df["rainfall_mm"], color="skyblue", width=0.8)
ax2.set_title(f"Daily Rainfall – {nearest_place}", fontsize=11)
ax2.set_xlabel("Date")
ax2.set_ylabel("Rainfall (mm)")
ax2.tick_params(axis="x", rotation=45)
fig2.tight_layout()
st.pyplot(fig2)

# ── Chart 3 – Temperature category scatter ──
st.divider()
st.subheader("🌡️ Max Temperature by Category")

colors_map = {0: "blue", 1: "green", 2: "red"}
labels_map = {0: "Cold (<20 °C)", 1: "Moderate (20–30 °C)", 2: "Hot (>30 °C)"}

fig3, ax3 = make_fig()
for t in sorted(df["temp_category"].unique()):
    subset = df[df["temp_category"] == t]
    subset_dates = pd.to_datetime(subset["date"])
    ax3.scatter(subset_dates, subset["temperature_2m_max"],
                color=colors_map[t], label=labels_map[t], s=80)
ax3.set_title("Max Temperature by Category", fontsize=11)
ax3.set_xlabel("Date")
ax3.set_ylabel("Max Temp (°C)")
ax3.tick_params(axis="x", rotation=45)
ax3.legend(title="Temperature Categories")
ax3.grid(True)
fig3.tight_layout()
st.pyplot(fig3)

# ── Chart 4 – Rainfall + Revenue (dual axis) ──
st.divider()
st.subheader("💰 Daily Rainfall vs Synthetic Revenue")

fig4, ax4a = plt.subplots(figsize=(10, 4))
ax4a.bar(dates_plot, df["rainfall_mm"], color="skyblue", label="Rainfall (mm)", width=0.8)
ax4a.set_xlabel("Date")
ax4a.set_ylabel("Rainfall (mm)", color="steelblue")
ax4a.tick_params(axis="y", labelcolor="steelblue")
ax4a.tick_params(axis="x", rotation=45)

ax4b = ax4a.twinx()
ax4b.plot(dates_plot, df["synthetic_revenue"], color="red", marker="o", markersize=4, label="Revenue")
ax4b.set_ylabel("Revenue (synthetic)", color="red")
ax4b.tick_params(axis="y", labelcolor="red")

fig4.suptitle(f"Daily Rainfall and Revenue – {nearest_place}", fontsize=11)
lines_a, labels_a = ax4a.get_legend_handles_labels()
lines_b, labels_b = ax4b.get_legend_handles_labels()
ax4b.legend(lines_a + lines_b, labels_a + labels_b, loc="upper right")
fig4.tight_layout()
st.pyplot(fig4)

st.divider()
st.caption("Data source: [Open-Meteo Archive API](https://open-meteo.com/) · Geography: [datasets/geo-countries](https://github.com/datasets/geo-countries)")BBOX = {"lat": (-26.9, -10.3), "lon": (30.2, 40.8)}


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


@st.cache_data(show_spinner=False)
def fetch_weather(lat, lon):
    """Fetch last 30 days of daily weather data from Open-Meteo API."""
    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=30)

    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "daily": "precipitation_sum,temperature_2m_max,temperature_2m_min",
        "timezone": "UTC",
    }

    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    daily = data["daily"]
    dates = pd.to_datetime(daily["time"])
    rainfall_mm = daily["precipitation_sum"]
    temperature_max = daily["temperature_2m_max"]
    temperature_min = daily["temperature_2m_min"]

    df = pd.DataFrame({
        "latitude": lat,
        "longitude": lon,
        "date": dates,
        "rainfall_mm": rainfall_mm,
        "temperature_2m_max": temperature_max,
        "temperature_2m_min": temperature_min,
    })

    def temp_category(max_temp):
        if max_temp < 20:
            return 0
        elif max_temp <= 30:
            return 1
        else:
            return 2

    df["temp_category"] = df["temperature_2m_max"].apply(temp_category)
    df["rain_flag"] = df["rainfall_mm"].apply(lambda x: 1 if x > 0 else 0)
    df["extreme_flag"] = df.apply(
        lambda row: 1 if (row["rainfall_mm"] > 10 or row["temperature_2m_max"] > 35) else 0,
        axis=1,
    )
    return df


def generate_revenue(df, seed=42):
    np.random.seed(seed)
    base_revenue = 1000

    def calc(row):
        rev = base_revenue
        if row["rainfall_mm"] > 5:
            rev *= 0.8
        if row["temperature_2m_max"] > 30:
            rev *= 1.1
        elif row["temperature_2m_max"] < 20:
            rev *= 0.9
        rev *= np.random.uniform(0.9, 1.1)
        return round(rev, 2)

    df = df.copy()
    df["synthetic_revenue"] = df.apply(calc, axis=1)
    return df

# ─── Session State ─────────────────────────────────────────────────────────────
if "mozambique" not in st.session_state:
    st.session_state.mozambique = None
if "lat" not in st.session_state:
    st.session_state.lat = None
if "lon" not in st.session_state:
    st.session_state.lon = None
if "nearest_place" not in st.session_state:
    st.session_state.nearest_place = None
if "df" not in st.session_state:
    st.session_state.df = None

# ─── UI ────────────────────────────────────────────────────────────────────────
st.title("🌍 Weather Data – First Step into Geo Intelligence")
st.markdown(
    """
Every morning, before stepping outside, we check the weather on our phones.
Will it rain? ☔ Is it hot? Do we need a jacket?

This app is a starting point for a broader journey into **Geo-Intelligence** —
using location-based data to support smarter decisions. Weather is our fun
first layer of a **location intelligence framework**.
"""
)

st.divider()

# ── Load Mozambique (once) ──
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
        st.session_state.df = None

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
        st.session_state.df = None

# ── Require a location ──
if st.session_state.lat is None:
    st.info("👈 Use the sidebar to pick a random location or enter coordinates.")
    st.stop()

lat = st.session_state.lat
lon = st.session_state.lon

# ── Reverse geocode ──
if st.session_state.nearest_place is None:
    with st.spinner("Reverse geocoding…"):
        st.session_state.nearest_place = reverse_geocode(lat, lon)

nearest_place = st.session_state.nearest_place

st.subheader(f"📍 Location: `{lat}, {lon}`")
st.caption(f"Nearest place: **{nearest_place}**")

# ── Fetch weather ──
if st.session_state.df is None:
    with st.spinner("Fetching weather data from Open-Meteo archive…"):
        df_base = fetch_weather(lat, lon)
        st.session_state.df = generate_revenue(df_base)

df = st.session_state.df

# ─── KPI cards ──────────────────────────────────────────────────────────────────
st.divider()
st.subheader("📊 30-day summary")

k1, k2, k3, k4 = st.columns(4)
k1.metric("☔ Total Rainfall", f"{df['rainfall_mm'].sum():.1f} mm")
k2.metric("🌡️ Avg Max Temp", f"{df['temperature_2m_max'].mean():.1f} °C")
k3.metric("🌡️ Avg Min Temp", f"{df['temperature_2m_min'].mean():.1f} °C")
k4.metric("⚡ Extreme-weather days", int(df["extreme_flag"].sum()))

# ─── Data table ─────────────────────────────────────────────────────────────────
with st.expander("📋 View raw data table"):
    st.dataframe(
        df.rename(columns={
            "date": "Date",
            "rainfall_mm": "Rainfall (mm)",
            "temperature_2m_max": "Max Temp (°C)",
            "temperature_2m_min": "Min Temp (°C)",
            "temp_category": "Temp Category (0=Cold, 1=Mod, 2=Hot)",
            "rain_flag": "Rain Flag",
            "extreme_flag": "Extreme Flag",
            "synthetic_revenue": "Synthetic Revenue",
        }),
        use_container_width=True,
        hide_index=True,
    )

# ─── Chart helpers ───────────────────────────────────────────────────────────────
dates_plot = [pd.Timestamp(d) for d in df["date"]]

def make_fig(figsize=(10, 4)):
    fig, ax = plt.subplots(figsize=figsize)
    return fig, ax

# ── Chart 1 – Rainfall + Temperature ──
st.divider()
st.subheader("📈 Daily Rainfall & Temperature")

fig1, ax1 = make_fig((10, 4))
ax1.plot(dates_plot, df["rainfall_mm"], label="Rainfall (mm)", color="blue", marker="o", markersize=4)
ax1.plot(dates_plot, df["temperature_2m_max"], label="Max Temp (°C)", color="red", marker="x", markersize=5)
ax1.plot(dates_plot, df["temperature_2m_min"], label="Min Temp (°C)", color="orange", marker="x", markersize=5)
ax1.set_title(f"Daily Weather – {nearest_place}", fontsize=11)
ax1.set_xlabel("Date")
ax1.set_ylabel("Rainfall / Temperature")
ax1.tick_params(axis="x", rotation=45)
ax1.legend()
ax1.grid(True)
fig1.tight_layout()
st.pyplot(fig1)

# ── Chart 2 – Rainfall bars ──
st.divider()
st.subheader("🌧️ Daily Rainfall (bar chart)")

fig2, ax2 = make_fig((10, 4))
ax2.bar(dates_plot, df["rainfall_mm"], color="skyblue", width=0.8)
ax2.set_title(f"Daily Rainfall – {nearest_place}", fontsize=11)
ax2.set_xlabel("Date")
ax2.set_ylabel("Rainfall (mm)")
ax2.tick_params(axis="x", rotation=45)
fig2.tight_layout()
st.pyplot(fig2)

# ── Chart 3 – Temperature category scatter ──
st.divider()
st.subheader("🌡️ Max Temperature by Category")

colors_map = {0: "blue", 1: "green", 2: "red"}
labels_map = {0: "Cold (<20 °C)", 1: "Moderate (20–30 °C)", 2: "Hot (>30 °C)"}

fig3, ax3 = make_fig((10, 4))
for t in sorted(df["temp_category"].unique()):
    subset = df[df["temp_category"] == t]
    subset_dates = [pd.Timestamp(d) for d in subset["date"]]
    ax3.scatter(subset_dates, subset["temperature_2m_max"],
                color=colors_map[t], label=labels_map[t], s=80)
ax3.set_title("Max Temperature by Category", fontsize=11)
ax3.set_xlabel("Date")
ax3.set_ylabel("Max Temp (°C)")
ax3.tick_params(axis="x", rotation=45)
ax3.legend(title="Temperature Categories")
ax3.grid(True)
fig3.tight_layout()
st.pyplot(fig3)

# ── Chart 4 – Rainfall + Revenue (dual axis) ──
st.divider()
st.subheader("💰 Daily Rainfall vs Synthetic Revenue")

fig4, ax4a = plt.subplots(figsize=(10, 4))
ax4a.bar(dates_plot, df["rainfall_mm"], color="skyblue", label="Rainfall (mm)", width=0.8)
ax4a.set_xlabel("Date")
ax4a.set_ylabel("Rainfall (mm)", color="steelblue")
ax4a.tick_params(axis="y", labelcolor="steelblue")
ax4a.tick_params(axis="x", rotation=45)

ax4b = ax4a.twinx()
ax4b.plot(dates_plot, df["synthetic_revenue"], color="red", marker="o", markersize=4, label="Revenue")
ax4b.set_ylabel("Revenue (synthetic)", color="red")
ax4b.tick_params(axis="y", labelcolor="red")

fig4.suptitle(f"Daily Rainfall and Revenue – {nearest_place}", fontsize=11)
lines_a, labels_a = ax4a.get_legend_handles_labels()
lines_b, labels_b = ax4b.get_legend_handles_labels()
ax4b.legend(lines_a + lines_b, labels_a + labels_b, loc="upper right")
fig4.tight_layout()
st.pyplot(fig4)

st.divider()
st.caption("Data source: [Open-Meteo Archive API](https://open-meteo.com/) · Geography: [datasets/geo-countries](https://github.com/datasets/geo-countries)")
