import streamlit as st
import requests
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from fpdf import FPDF
import folium
from streamlit_folium import st_folium
import numpy as np

st.set_page_config(page_title="Ekspert PV Pro 2025", layout="wide")

# --- INICJALIZACJA SESJI ---
if 'lat' not in st.session_state: st.session_state.lat = 52.23
if 'lon' not in st.session_state: st.session_state.lon = 21.01
if 'city' not in st.session_state: st.session_state.city = "Warszawa"

# --- BAZA DANYCH ---
PANELS = {"Longi 450W": 0.45, "Jinko 550W": 0.55, "Trina 400W": 0.40}
INVERTERS = {
    "Huawei SUN2000": [0.98, 4500],
    "Fronius Symo": [0.97, 6200],
    "SMA Sunny Tripower": [0.98, 7500],
    "Growatt MOD": [0.96, 3800]
}
BATTERIES = {"Brak": 0, "5 kWh": 5, "10 kWh": 10, "15 kWh": 15}

# --- FUNKCJE ---
def get_coords(city_name):
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={city_name}&format=json&limit=1"
        res = requests.get(url, headers={'User-Agent': 'PV_Pro_V8'}).json()
        if res: return float(res[0]['lat']), float(res[0]['lon']), res[0]['display_name'].split(',')[0]
    except: return None

@st.cache_data
def get_weather_data(lat, lon):
    try:
        url = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date=2025-01-01&end_date=2025-12-31&daily=shortwave_radiation_sum&timezone=auto"
        res = requests.get(url).json()
        rad_list = res['daily']['shortwave_radiation_sum']
        rad_total = sum([r for r in rad_list if r is not None]) / 3.6
        sunny_days = len([r for r in rad_list if r is not None and r > 15])
        return rad_total, sunny_days
    except: return 1050.0, 185

# --- SIDEBAR ---
st.sidebar.header("📍 1. Lokalizacja")
city_in = st.sidebar.text_input("Miasto:", value=st.session_state.city)
if st.sidebar.button("Zaktualizuj dane"):
    res = get_coords(city_in)
    if res:
        st.session_state.lat, st.session_state.lon, st.session_state.city = res
        st.rerun()

st.sidebar.header("🏗️ 2. Sprzęt")
sel_p = st.sidebar.selectbox("Model paneli:", list(PANELS.keys()))
num_p = st.sidebar.slider("Liczba paneli:", 1, 60, 14)
sel_inv = st.sidebar.selectbox("Model inwertera:", list(INVERTERS.keys()))
sel_b = st.sidebar.selectbox("Magazyn energii:", list(BATTERIES.keys()))

st.sidebar.header("💰 3. Finanse")
bill = st.sidebar.number_input("Rachunek (miesięczny):", 50, 2000, 400)
price = st.sidebar.number_input("Cena 1 kWh (zł):", 0.5, 3.0, 1.25)
# POPRAWKA: Zakres od 0 zł
cost_kwp = st.sidebar.number_input("Montaż i osprzęt (zł/kWp):", 0, 10000, 4000)

# --- OBLICZENIA ---
rad_total, sunny_days = get_weather_data(st.session_state.lat, st.session_state.lon)
total_kwp = num_p * PANELS[sel_p]
inv_eff = INVERTERS[sel_inv][0]
inv_price = INVERTERS[sel_inv][1]

prod_year = total_kwp * rad_total * inv_eff * 0.9
inv_cost = (total_kwp * cost_kwp) + inv_price + (BATTERIES[sel_b] * 2000)

autocons_val = 0.3 + (BATTERIES[sel_b] / 25) if BATTERIES[sel_b] > 0 else 0.3
autocons = min(0.75, autocons_val)
savings = (prod_year * autocons * price) + (prod_year * (1 - autocons) * 0.50)
roi = inv_cost / savings if savings > 0 else 0

# --- WIDOK GŁÓWNY ---
st.title(f"☀️ Raport Techniczny PV 2025: {st.session_state.city}")

col_top1, col_top2, col_top3, col_top4 = st.columns(4)
col_top1.metric("Dni Słoneczne (2025)", f"{sunny_days} dni")
col_top2.metric("Moc Układu", f"{round(total_kwp, 2)} kWp")
col_top3.metric("Inwestycja", f"{int(inv_cost)} zł")
col_top4.metric("Zwrot (ROI)", f"{round(roi, 1)} lat")

st.divider()

col_map, col_plots = st.columns([1, 1])

with col_map:
    st.subheader("📍 Analiza Lokalizacji")
    m = folium.Map(location=[st.session_state.lat, st.session_state.lon], zoom_start=12)
    folium.Marker([st.session_state.lat, st.session_state.lon]).add_to(m)
    st_folium(m, height=250, use_container_width=True, key="map_v9")
    st.info(f"Nasłonecznienie w tej lokalizacji: **{int(rad_total)} kWh/m²**.")

with col_plots:
    st.subheader("📈
